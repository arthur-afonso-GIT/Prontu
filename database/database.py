import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# --- BLOCO DINÂMICO DE LOCALIZAÇÃO E PARSER SUPREMO DO .ENV ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CWD_DIR = os.getcwd()

caminhos_possiveis = [
    os.path.join(CWD_DIR, ".env"),
    os.path.join(CWD_DIR, ".env.txt"),
    os.path.join(BASE_DIR, ".env"),
    os.path.join(os.path.dirname(BASE_DIR), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), ".env")
]

ENV_PATH = None
for caminho in caminhos_possiveis:
    if os.path.exists(caminho):
        ENV_PATH = caminho
        break

env_emergencia = {}

if ENV_PATH:
    try:
        # 1. Tentativa padrão com dotenv
        with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
            load_dotenv(stream=f)
        
        # 2. PARSER MANUAL ULTRA-AGRESSIVO (Lê o arquivo bruto)
        with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
            conteudo_completo = f.read()
            
            # Divide por quebras de linha comuns do Windows (\r\n) ou Linux (\n)
            linhas = conteudo_completo.replace("\r", "\n").split("\n")
            
            for linha in linhas:
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
                
                # Se a linha contiver o sinal de igual, nós separamos cirurgicamente
                if "=" in linha:
                    partes = linha.split("=", 1)
                    chave = partes[0].strip().strip("'").strip('"')
                    valor = partes[1].strip().strip("'").strip('"')
                    env_emergencia[chave] = valor
                    
        print(f"Sucesso: Configuração lida do arquivo em: {ENV_PATH}")
    except Exception as e:
        print(f"Erro crítico ao ler fisicamente o arquivo .env: {e}")
else:
    ENV_PATH = os.path.join(CWD_DIR, ".env")
    print("AVISO: Nenhum arquivo .env encontrado nas pastas mapeadas!")
# --------------------------------------------------

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".prontu_config.json")

class Database:
    def __init__(self):
        """Inicializa a conexão segura com o Supabase limpando qualquer resíduo de string."""
        # Captura de todas as fontes possíveis (Dotenv clássico, Sistema ou Parser Manual)
        url_bruta = os.getenv("SUPABASE_URL") or env_emergencia.get("SUPABASE_URL")
        key_bruta = os.getenv("SUPABASE_KEY") or env_emergencia.get("SUPABASE_KEY")
        
        # Se falhou e leu a linha inteira como chave por causa de erros do Windows, extrai pelo dicionário
        if not url_bruta:
            for k, v in env_emergencia.items():
                if "SUPABASE_URL" in k:
                    url_bruta = v if v else k.split("=", 1)[1] if "=" in k else None
                    
        if not key_bruta:
            for k, v in env_emergencia.items():
                if "SUPABASE_KEY" in k:
                    key_bruta = v if v else k.split("=", 1)[1] if "=" in k else None

        self.supabase_url = None
        self.supabase_key = None

        # Limpeza definitiva de aspas e nomes de variáveis grudados por acidente
        if url_bruta:
            s_url = str(url_bruta)
            if "SUPABASE_URL=" in s_url:
                s_url = s_url.split("SUPABASE_URL=", 1)[1]
            self.supabase_url = s_url.strip().strip("'").strip('"').strip().rstrip('/')
            
        if key_bruta:
            s_key = str(key_bruta)
            if "SUPABASE_KEY=" in s_key:
                s_key = s_key.split("SUPABASE_KEY=", 1)[1]
            self.supabase_key = s_key.strip().strip("'").strip('"').strip()
        
        self.supabase = None
        
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
                print("-> Conexão com o Supabase estabelecida com SUCESSO!")
            except Exception as e:
                print(f"Erro ao conectar ao Supabase: {e}")
        else:
            print("AVISO: Conexão não iniciada. Credenciais inválidas!")
            print(f"   -> URL processada final: {repr(self.supabase_url)}")
            print(f"   -> KEY processada final: {repr(self.supabase_key)}")
        
        self.consultorio_id = self.carregar_consultorio_id_local()

    def carregar_consultorio_id_local(self):
        """Busca o ID salvo localmente no computador do utilizador para login automático."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    return dados.get("consultorio_id", None)
            except Exception as e:
                print(f"Erro ao ler configuração local: {e}")
        return None

    def validar_chave_acesso(self, chave_inserida):
        """Verifica na tabela 'chaves_acesso' se a chave introduzida existe."""
        if not self.supabase:
            print("Erro: Conexão com o banco de dados indisponível para validação.")
            return None
        
        try:
            # Limpa espaços em branco e garante que busca a chave correta
            chave_limpa = str(chave_inserida).strip()
            
            resposta = self.supabase.table("chaves_acesso")\
                .select("consultorio_id, nome_clinica")\
                .eq("chave", chave_limpa)\
                .execute()
                
            if resposta.data and len(resposta.data) > 0:
                dados_retornados = resposta.data[0]
                
                # CORREÇÃO CRÍTICA: Garante que o consultorio_id extraído seja tratado com segurança
                if dados_retornados.get("consultorio_id") is not None:
                    try:
                        dados_retornados["consultorio_id"] = int(dados_retornados["consultorio_id"])
                    except (ValueError, TypeError):
                        pass # Mantém o formato original caso não consiga converter
                        
                return dados_retornados
        except Exception as e:
            print(f"Erro crítico ao validar chave de acesso no Supabase: {e}")
            
        return None

    def carregar_consultorio_id_local(self):
        """Busca o ID salvo localmente no computador do utilizador para login automático."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    val = dados.get("consultorio_id", None)
                    return int(val) if val is not None else None
            except Exception as e:
                print(f"Erro ao ler configuração local: {e}")
        return None

    def salvar_consultorio_id_local(self, novo_id):
        """Salva permanentemente o ID na máquina local após validação com sucesso."""
        try:
            self.consultorio_id = int(novo_id) if novo_id is not None else None
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"consultorio_id": self.consultorio_id}, f)
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração local: {e}")
            return False

    # --- FUNÇÕES DE CONFIGURAÇÃO ---
    def obter_nome_profissional(self):
        """Recupera o nome salvo do médico/profissional para esta clínica."""
        if not self.supabase or self.consultorio_id is None:
            return ""
        try:
            resposta = self.supabase.table("configuracoes")\
                .select("valor")\
                .eq("consultorio_id", self.consultorio_id)\
                .eq("chave", "nome_profissional")\
                .execute()
            
            if resposta.data:
                return resposta.data[0]["valor"]
        except Exception as e:
            print(f"Erro ao obter nome profissional: {e}")
        return ""

    def salvar_nome_profissional(self, nome):
        """Salva ou atualiza o nome do médico/profissional na nuvem."""
        if not self.supabase or self.consultorio_id is None:
            return
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "chave": "nome_profissional",
                "valor": nome.strip()
            }
            self.supabase.table("configuracoes").upsert(payload).execute()
        except Exception as e:
            print(f"Erro ao salvar nome profissional: {e}")

    # --- FUNÇÕES PARA PACIENTES ---
    def salvar_paciente(self, dados):
        """Insere ou atualiza um paciente na base de dados do Supabase."""
        if not self.supabase or self.consultorio_id is None:
            return
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "nome": dados.get('nome'),
                "telefone": dados.get('telefone'),
                "nascimento": dados.get('nascimento'),
                "convenio": dados.get('convenio'),
                "endereco": dados.get('endereco'),
                "queixa_principal": dados.get('queixa_principal'),
                "pasta": dados.get('pasta', 'Geral')
            }
            self.supabase.table("pacientes").insert(payload).execute()
        except Exception as e:
            print(f"Erro ao salvar paciente: {e}")

    def listar_todos_pacientes(self):
        """Retorna todos os pacientes cadastrados na nuvem para este consultório."""
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = self.supabase.table("pacientes")\
                .select("nome, telefone, convenio, pasta, nascimento, endereco, queixa_principal")\
                .eq("consultorio_id", self.consultorio_id)\
                .order("nome")\
                .execute()
            
            pacientes = []
            for item in resposta.data:
                pacientes.append((
                    item["nome"],
                    item["telefone"],
                    item["convenio"],
                    item["pasta"],
                    item["nascimento"],
                    item["endereco"],
                    item["queixa_principal"]
                ))
            return pacientes
        except Exception as e:
            print(f"Erro ao listar pacientes: {e}")
            return []

    def buscar_nomes_pacientes(self):
        """Retorna apenas a lista de strings com os nomes (Para a Agenda!)."""
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = self.supabase.table("pacientes")\
                .select("nome")\
                .eq("consultorio_id", self.consultorio_id)\
                .order("nome")\
                .execute()
            return [row["nome"] for row in resposta.data]
        except Exception as e:
            print(f"Erro ao buscar nomes: {e}")
            return []