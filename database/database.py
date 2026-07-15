import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client, Client

from database.secure_storage import SecureStorage
from database.session_manager import SessionExpiredError, SessionManager

# --- BLOCO DINÂMICO DE LOCALIZAÇÃO E PARSER SUPREMO DO .ENV ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CWD_DIR = os.getcwd()

caminhos_possiveis = [
    os.path.join(CWD_DIR, ".env"),
    os.path.join(CWD_DIR, ".env.txt"),
    os.path.join(BASE_DIR, ".env"),
    os.path.join(os.path.dirname(BASE_DIR), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), ".env"),
]

ENV_PATH = None
for caminho in caminhos_possiveis:
    if os.path.exists(caminho):
        ENV_PATH = caminho
        break

env_emergencia = {}

if ENV_PATH:
    try:
        with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
            load_dotenv(stream=f)

        with open(ENV_PATH, "r", encoding="utf-8-sig") as f:
            conteudo_completo = f.read()
            linhas = conteudo_completo.replace("\r", "\n").split("\n")

            for linha in linhas:
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
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
    print("AVISO: Nenhum arquivo .env encontrado nas pastas mapeadas.")

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".prontu_config.json")


def _limpar_credencial(valor_bruto, prefixo: str):
    if not valor_bruto:
        return None
    s = str(valor_bruto)
    if f"{prefixo}=" in s:
        s = s.split(f"{prefixo}=", 1)[1]
    return s.strip().strip("'").strip('"').strip()


class Database:
    """Cliente Supabase centralizado com sessão autenticada por consultório."""

    def __init__(self):
        url_bruta = os.getenv("SUPABASE_URL") or env_emergencia.get("SUPABASE_URL")
        key_bruta = os.getenv("SUPABASE_KEY") or env_emergencia.get("SUPABASE_KEY")

        if not url_bruta:
            for k, v in env_emergencia.items():
                if "SUPABASE_URL" in k:
                    url_bruta = v if v else k.split("=", 1)[1] if "=" in k else None

        if not key_bruta:
            for k, v in env_emergencia.items():
                if "SUPABASE_KEY" in k:
                    key_bruta = v if v else k.split("=", 1)[1] if "=" in k else None

        self.supabase_url = _limpar_credencial(url_bruta, "SUPABASE_URL")
        if self.supabase_url:
            self.supabase_url = self.supabase_url.rstrip("/")
        self.supabase_key = _limpar_credencial(key_bruta, "SUPABASE_KEY")

        self.supabase: Client | None = None
        self.session_manager: SessionManager | None = None
        self.consultorio_id: int | None = None
        self._secure_storage = SecureStorage()

        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                self.session_manager = SessionManager(self.supabase_url, self.supabase_key)
                print("-> Conexão com o Supabase estabelecida com SUCESSO!")
            except Exception as e:
                print(f"Erro ao conectar ao Supabase: {e}")
        else:
            print("AVISO: Conexão não iniciada. Credenciais inválidas!")

        self._restaurar_sessao_local()

    def _restaurar_sessao_local(self) -> None:
        """Restaura sessão segura; consultorio_id legado sozinho não autentica."""
        if not self.session_manager or not self.supabase:
            return

        legacy_hint = self._secure_storage.load_legacy_consultorio_hint()
        if legacy_hint is not None and not self._secure_storage.load_session():
            self._secure_storage.mark_legacy_requires_revalidation()
            print(
                "Aviso: configuração legada detectada — revalidação da chave necessária."
            )
            return

        if self.session_manager.load_persisted_session():
            self._aplicar_sessao_no_cliente()
            self.consultorio_id = self.session_manager.consultorio_id

    def _aplicar_sessao_no_cliente(self) -> None:
        if not self.supabase or not self.session_manager:
            return
        access = self.session_manager.access_token
        refresh = self.session_manager.refresh_token
        if access and refresh:
            try:
                self.supabase.auth.set_session(access, refresh)
            except Exception as exc:
                print(f"Aviso: falha ao aplicar sessão ({exc}).")

    def esta_autenticado(self) -> bool:
        return (
            self.session_manager is not None
            and self.session_manager.is_authenticated
            and self.consultorio_id is not None
        )

    def validar_chave_acesso(self, chave_inserida: str) -> dict | None:
        """Ativa consultório via Edge Function segura (não consulta chaves_acesso diretamente)."""
        if not self.session_manager:
            print("Erro: gerenciador de sessão indisponível.")
            return None
        try:
            resultado = self.session_manager.activate_with_key(chave_inserida)
        except ConnectionError as exc:
            print(exc)
            return None
        except RuntimeError as exc:
            print(exc)
            return None

        if not resultado:
            return None

        self.consultorio_id = self.session_manager.consultorio_id
        self._aplicar_sessao_no_cliente()
        return {
            "consultorio_id": self.consultorio_id,
            "nome_clinica": resultado.get("nome_clinica"),
        }

    def renovar_sessao_se_necessario(self) -> bool:
        if not self.session_manager:
            return False
        try:
            ok = self.session_manager.refresh_if_needed()
            if ok:
                self._aplicar_sessao_no_cliente()
            return ok
        except SessionExpiredError:
            self.desativar_dispositivo()
            return False

    def desativar_dispositivo(self) -> None:
        """Encerra sessão local (desativação do dispositivo)."""
        if self.session_manager:
            self.session_manager.logout()
        self.consultorio_id = None

    def carregar_consultorio_id_local(self):
        """Compatibilidade: retorna consultorio_id apenas se sessão autenticada."""
        if self.esta_autenticado():
            return self.consultorio_id
        return None

    def salvar_consultorio_id_local(self, novo_id):
        """Legado: sessão segura é a fonte de verdade; mantém hint não-autenticador."""
        try:
            hint = int(novo_id) if novo_id is not None else None
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "requires_revalidation": False,
                        "consultorio_id_hint": hint,
                    },
                    f,
                )
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração local: {e}")
            return False

    def registrar_evento_auditoria(
        self,
        acao: str,
        entidade: str,
        registro_id=None,
        contexto: dict | None = None,
    ) -> None:
        """Registra eventos de alto nível (backup/export) via RPC."""
        if not self.supabase or self.consultorio_id is None:
            return
        try:
            self.supabase.rpc(
                "registrar_audit_log",
                {
                    "p_acao": acao,
                    "p_entidade": entidade,
                    "p_registro_id": str(registro_id) if registro_id is not None else None,
                    "p_contexto": contexto or {},
                },
            ).execute()
        except Exception as exc:
            print(f"Aviso: falha ao registrar auditoria ({acao}/{entidade}): {exc}")

    # --- FUNÇÕES DE CONFIGURAÇÃO ---
    def obter_nome_profissional(self):
        if not self.supabase or self.consultorio_id is None:
            return ""
        try:
            resposta = (
                self.supabase.table("configuracoes")
                .select("valor")
                .eq("consultorio_id", self.consultorio_id)
                .eq("chave", "nome_profissional")
                .execute()
            )
            if resposta.data:
                return resposta.data[0]["valor"]
        except Exception as e:
            print(f"Erro ao obter nome profissional: {e}")
        return ""

    def salvar_nome_profissional(self, nome):
        if not self.supabase or self.consultorio_id is None:
            return
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "chave": "nome_profissional",
                "valor": nome.strip(),
            }
            self.supabase.table("configuracoes").upsert(payload).execute()
        except Exception as e:
            print(f"Erro ao salvar nome profissional: {e}")

    def obter_configuracao(self, chave: str, default: str = "") -> str:
        if not self.supabase or self.consultorio_id is None:
            return default
        try:
            resposta = (
                self.supabase.table("configuracoes")
                .select("valor")
                .eq("consultorio_id", self.consultorio_id)
                .eq("chave", chave)
                .execute()
            )
            if resposta.data:
                return resposta.data[0]["valor"]
        except Exception as e:
            print(f"Erro ao obter configuração {chave}: {e}")
        return default

    def obter_configuracoes(self, chaves: list[str]) -> dict[str, str]:
        """Busca várias configurações em uma única chamada ao Supabase."""
        if not self.supabase or self.consultorio_id is None or not chaves:
            return {}
        try:
            resposta = (
                self.supabase.table("configuracoes")
                .select("chave, valor")
                .eq("consultorio_id", self.consultorio_id)
                .in_("chave", chaves)
                .execute()
            )
            return {
                item["chave"]: item.get("valor", "")
                for item in (resposta.data or [])
            }
        except Exception as e:
            print(f"Erro ao obter configurações: {e}")
            return {}

    def salvar_configuracao(self, chave: str, valor: str) -> None:
        if not self.supabase or self.consultorio_id is None:
            return
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "chave": chave,
                "valor": valor,
            }
            self.supabase.table("configuracoes").upsert(payload).execute()
        except Exception as e:
            print(f"Erro ao salvar configuração {chave}: {e}")

    # --- FUNÇÕES PARA PACIENTES ---
    def salvar_paciente(self, dados):
        if not self.supabase or self.consultorio_id is None:
            return
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "nome": dados.get("nome"),
                "telefone": dados.get("telefone"),
                "nascimento": dados.get("nascimento"),
                "convenio": dados.get("convenio"),
                "endereco": dados.get("endereco"),
                "queixa_principal": dados.get("queixa_principal"),
                "pasta": dados.get("pasta", "Geral"),
            }
            self.supabase.table("pacientes").insert(payload).execute()
        except Exception as e:
            print(f"Erro ao salvar paciente: {e}")

    def listar_todos_pacientes(self):
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("pacientes")
                .select(
                    "nome, telefone, convenio, pasta, nascimento, endereco, queixa_principal"
                )
                .eq("consultorio_id", self.consultorio_id)
                .is_("deleted_at", "null")
                .order("nome")
                .execute()
            )
            pacientes = []
            for item in resposta.data:
                pacientes.append(
                    (
                        item["nome"],
                        item["telefone"],
                        item["convenio"],
                        item["pasta"],
                        item["nascimento"],
                        item["endereco"],
                        item["queixa_principal"],
                    )
                )
            return pacientes
        except Exception as e:
            print(f"Erro ao listar pacientes: {e}")
            return []

    def buscar_nomes_pacientes(self):
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("pacientes")
                .select("nome")
                .eq("consultorio_id", self.consultorio_id)
                .is_("deleted_at", "null")
                .order("nome")
                .execute()
            )
            return [row["nome"] for row in resposta.data]
        except Exception as e:
            print(f"Erro ao buscar nomes: {e}")
            return []

    def soft_delete_paciente(self, paciente_id: int) -> bool:
        """Exclusão lógica — preserva dados clínicos."""
        if not self.supabase or self.consultorio_id is None:
            return False

    def soft_delete_ficha(self, ficha_id: int) -> bool:
        """Remove uma ficha da visualização sem apagar seu histórico clínico."""
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            from datetime import datetime, timezone

            self.supabase.table("fichas_preenchidas").update(
                {"deleted_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", ficha_id).eq("consultorio_id", self.consultorio_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao excluir ficha: {e}")
            return False
        try:
            from datetime import datetime, timezone

            agora = datetime.now(timezone.utc).isoformat()
            self.supabase.table("pacientes").update(
                {"deleted_at": agora}
            ).eq("id", paciente_id).eq("consultorio_id", self.consultorio_id).execute()
            self.supabase.table("fichas_preenchidas").update(
                {"deleted_at": agora}
            ).eq("paciente_id", paciente_id).eq(
                "consultorio_id", self.consultorio_id
            ).execute()
            return True
        except Exception as e:
            print(f"Erro ao excluir paciente (soft delete): {e}")
            return False
