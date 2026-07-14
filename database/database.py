import sys
from supabase import create_client, Client
from config_app import SUPABASE_URL, SUPABASE_KEY, CONSULTORIO_ID

class Database:
    def __init__(self):
        """Inicializa a conexão segura com o Supabase na Nuvem."""
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"Erro ao conectar ao Supabase: {e}")
            self.supabase = None
        
        # Define explicitamente o consultorio_id logo na inicialização
        self.consultorio_id = CONSULTORIO_ID

    # --- FUNÇÕES DE CONFIGURAÇÃO ---
    def obter_nome_profissional(self):
        """Recupera o nome salvo do médico/profissional para esta clínica."""
        if not self.supabase:
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
        if not self.supabase:
            return
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "chave": "nome_profissional",
                "valor": nome.strip()
            }
            # Tenta atualizar ou inserir dependendo da existência prévia
            self.supabase.table("configuracoes").upsert(payload).execute()
        except Exception as e:
            print(f"Erro ao salvar nome profissional: {e}")

    # --- FUNÇÕES PARA PACIENTES ---
    def salvar_paciente(self, dados):
        """Insere ou atualiza um paciente na base de dados do Supabase."""
        if not self.supabase:
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
        """Retorna todos os pacientes cadastrados na nuvem."""
        if not self.supabase:
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
        if not self.supabase:
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