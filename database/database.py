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

    def obter_plano_atual(self) -> str:
        """Retorna o plano da ativação atual. Por enquanto, todos usam Solo."""
        if not self.session_manager:
            return "solo"
        return self.session_manager.plano

    def possui_recurso(self, recurso: str) -> bool:
        """Ponto único para liberar recursos futuros sem espalhar regras pela interface."""
        plano = self.obter_plano_atual()
        recursos = self.session_manager.recursos_extras if self.session_manager else []
        if recurso in recursos:
            return True
        recursos_por_plano = {
            "solo": set(),
            "equipe": {"equipe", "controle_acesso", "base_compartilhada"},
            "personalizado": {"equipe", "controle_acesso", "base_compartilhada", "personalizacoes"},
        }
        return recurso in recursos_por_plano.get(plano, set())

    def obter_resumo_assinatura(self) -> dict:
        """Dados seguros para exibição em Configurações; nunca expõe a chave."""
        sessao = getattr(self.session_manager, "_session", None) or {}
        return {
            "plano": self.obter_plano_atual(),
            "status": sessao.get("status_assinatura") or "ativa",
            "expira_em": sessao.get("expira_em"),
            "max_usuarios": sessao.get("max_usuarios") or 1,
        }

    def obter_papel_atual(self) -> str:
        """Papel da pessoa autenticada; por compatibilidade sessões antigas são Proprietário."""
        if not self.session_manager:
            return "proprietario"
        return self.session_manager.papel

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
            "plano": resultado.get("plano") or "solo",
        }

    def entrar_com_email(self, email: str, senha: str, lembrar: bool = True) -> dict | None:
        if not self.session_manager:
            return None
        try:
            resultado = self.session_manager.login_with_email(email, senha, lembrar=lembrar)
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: login não concluído ({exc}).")
            return None
        self.consultorio_id = self.session_manager.consultorio_id
        self._aplicar_sessao_no_cliente()
        return resultado

    def aceitar_convite_equipe(self, codigo: str, email: str, senha: str) -> dict | None:
        if not self.session_manager:
            return None
        try:
            resultado = self.session_manager.accept_invite(codigo, email, senha)
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: convite não aceito ({exc}).")
            return None
        self.consultorio_id = self.session_manager.consultorio_id
        self._aplicar_sessao_no_cliente()
        return resultado

    def criar_login_proprietario(self, email: str, senha: str) -> dict | None:
        if not self.session_manager:
            return None
        try:
            resultado = self.session_manager.create_owner_login(email, senha)
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: login do proprietario nao criado ({exc}).")
            return None
        self.consultorio_id = self.session_manager.consultorio_id
        self._aplicar_sessao_no_cliente()
        return resultado

    def solicitar_redefinicao_senha(self, email: str) -> bool:
        if not self.session_manager:
            return False
        return self.session_manager.request_password_reset(email)

    def listar_equipe(self) -> dict | None:
        if not self.session_manager:
            return None
        try:
            return self.session_manager.gerenciar_equipe("listar")
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: equipe indisponivel ({exc}).")
            return None

    def criar_convite_equipe(self, nome: str, email: str, papel: str) -> dict | None:
        if not self.session_manager:
            return None
        try:
            return self.session_manager.gerenciar_equipe(
                "convidar", nome=nome, email=email, papel=papel
            )
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: convite nao criado ({exc}).")
            return None

    def revogar_acesso_equipe(self, tipo: str, identificador: str) -> bool:
        if not self.session_manager:
            return False
        try:
            campo = "convite_id" if tipo == "convite" else "membro_id"
            self.session_manager.gerenciar_equipe("revogar", **{campo: identificador})
            return True
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: acesso nao revogado ({exc}).")
            return False

    def alterar_papel_equipe(self, membro_id: str, papel: str) -> bool:
        if not self.session_manager:
            return False
        try:
            self.session_manager.gerenciar_equipe("alterar_papel", membro_id=membro_id, papel=papel)
            return True
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: papel nao alterado ({exc}).")
            return False

    def renovar_convite_equipe(self, convite_id: str) -> dict | None:
        if not self.session_manager:
            return None
        try:
            return self.session_manager.gerenciar_equipe("renovar_convite", convite_id=convite_id)
        except (ConnectionError, RuntimeError) as exc:
            print(f"Aviso: convite nao renovado ({exc}).")
            return None

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

    def listar_eventos_auditoria(self, limite: int = 300) -> list[dict]:
        """Retorna metadados de auditoria do consultório, sem valores clínicos."""
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("audit_logs")
                .select(
                    "id, acao, entidade, registro_id, contexto, "
                    "valor_anterior, valor_novo, criado_em"
                )
                .eq("consultorio_id", self.consultorio_id)
                .order("criado_em", desc=True)
                .limit(limite)
                .execute()
            )
            return resposta.data or []
        except Exception as exc:
            print(f"Aviso: falha ao listar auditoria ({type(exc).__name__}).")
            return []

    def criar_retorno(self, paciente_id: int, data_prevista: str | None = None, motivo: str = "") -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            self.supabase.table("retornos_pacientes").insert({
                "consultorio_id": self.consultorio_id,
                "paciente_id": paciente_id,
                "data_prevista": data_prevista,
                "motivo": motivo.strip(),
                "status": "Pendente",
            }).execute()
            self.registrar_evento_auditoria(
                "INSERT", "retornos_pacientes", paciente_id,
                {"data_prevista": data_prevista},
            )
            return True
        except Exception as exc:
            print(f"Aviso: falha ao criar retorno ({type(exc).__name__}).")
            return False

    def criar_retorno_pendente_da_consulta(self, paciente_nome: str) -> bool:
        """Cria um único retorno pendente após uma consulta comum ser realizada."""
        if not self.supabase or self.consultorio_id is None or not paciente_nome.strip():
            return False
        try:
            paciente_resp = (
                self.supabase.table("pacientes")
                .select("id")
                .eq("consultorio_id", self.consultorio_id)
                .ilike("nome", paciente_nome.strip())
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            if not paciente_resp.data:
                return False
            paciente_id = paciente_resp.data[0]["id"]
            existente = (
                self.supabase.table("retornos_pacientes")
                .select("id")
                .eq("consultorio_id", self.consultorio_id)
                .eq("paciente_id", paciente_id)
                .in_("status", ["Pendente", "Agendado"])
                .limit(1)
                .execute()
            )
            if existente.data:
                return True
            return self.criar_retorno(
                paciente_id,
                None,
                "",
            )
        except Exception as exc:
            print(f"Aviso: falha ao criar retorno automático ({type(exc).__name__}).")
            return False

    def definir_data_retorno(self, retorno_id: int, data_prevista: str) -> bool:
        if not self.supabase or self.consultorio_id is None or not retorno_id or not data_prevista:
            return False
        try:
            self.supabase.table("retornos_pacientes").update({
                "data_prevista": data_prevista,
                "status": "Pendente",
            }).eq("id", retorno_id).eq("consultorio_id", self.consultorio_id).execute()
            self.registrar_evento_auditoria(
                "UPDATE", "retornos_pacientes", retorno_id,
                {"data_prevista": data_prevista},
            )
            return True
        except Exception as exc:
            print(f"Aviso: falha ao definir data do retorno ({type(exc).__name__}).")
            return False

    def listar_retornos_pendentes(self, limite: int = 100) -> list[dict]:
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("retornos_pacientes")
                .select("id, paciente_id, data_prevista, motivo, status")
                .eq("consultorio_id", self.consultorio_id)
                .eq("status", "Pendente")
                .order("data_prevista")
                .limit(limite)
                .execute()
            )
            retornos = resposta.data or []
            ids = list({item.get("paciente_id") for item in retornos if item.get("paciente_id") is not None})
            if not ids:
                return retornos
            pacientes = (
                self.supabase.table("pacientes")
                .select("id, nome")
                .eq("consultorio_id", self.consultorio_id)
                .in_("id", ids)
                .is_("deleted_at", "null")
                .execute()
            )
            nomes = {item["id"]: item.get("nome", "Paciente") for item in (pacientes.data or [])}
            for retorno in retornos:
                retorno["paciente_nome"] = nomes.get(retorno.get("paciente_id"), "Paciente indisponível")
            return retornos
        except Exception as exc:
            print(f"Aviso: falha ao listar retornos ({type(exc).__name__}).")
            return []

    def listar_retornos_paciente(self, paciente_id: int) -> list[dict]:
        """Retorna o histórico de retornos de um paciente do consultório atual."""
        if not self.supabase or self.consultorio_id is None or not paciente_id:
            return []
        try:
            resposta = (
                self.supabase.table("retornos_pacientes")
                .select("id, data_prevista, motivo, status, criado_em")
                .eq("consultorio_id", self.consultorio_id)
                .eq("paciente_id", paciente_id)
                .order("data_prevista", desc=True)
                .execute()
            )
            return resposta.data or []
        except Exception as exc:
            print(f"Aviso: falha ao listar retornos do paciente ({type(exc).__name__}).")
            return []

    def atualizar_status_retorno(self, retorno_id: int, status: str) -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        if status not in {"Pendente", "Agendado", "Concluído", "Não retornou", "Cancelado"}:
            return False
        try:
            self.supabase.table("retornos_pacientes").update({"status": status}).eq(
                "id", retorno_id
            ).eq("consultorio_id", self.consultorio_id).execute()
            self.registrar_evento_auditoria("UPDATE", "retornos_pacientes", retorno_id, {"status": status})
            return True
        except Exception as exc:
            print(f"Aviso: falha ao atualizar retorno ({type(exc).__name__}).")
            return False

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
            if self.obter_papel_atual() == "secretaria":
                resposta = self.supabase.rpc("listar_pacientes_secretaria", {"p_busca": None}).execute()
                return [str(row.get("nome") or "") for row in (resposta.data or [])]
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

    def listar_pacientes_secretaria(self, busca: str | None = None) -> list[dict]:
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = self.supabase.rpc("listar_pacientes_secretaria", {"p_busca": busca}).execute()
            return resposta.data or []
        except Exception as exc:
            print(f"Erro ao listar pacientes básicos: {type(exc).__name__}.")
            return []

    def obter_paciente_secretaria(self, paciente_id: int) -> dict | None:
        if not self.supabase:
            return None
        try:
            resposta = self.supabase.rpc("obter_paciente_secretaria", {"p_paciente_id": int(paciente_id)}).execute()
            return (resposta.data or [None])[0]
        except Exception as exc:
            print(f"Erro ao obter paciente básico: {type(exc).__name__}.")
            return None

    def salvar_paciente_secretaria(self, paciente_id: int | None, dados: dict) -> int | None:
        if not self.supabase:
            return None
        try:
            resposta = self.supabase.rpc("salvar_paciente_secretaria", {
                "p_paciente_id": paciente_id,
                "p_nome": dados.get("nome"), "p_telefone": dados.get("telefone"),
                "p_nascimento": dados.get("nascimento"), "p_convenio": dados.get("convenio"),
                "p_pasta": dados.get("pasta"), "p_sexo": dados.get("sexo"),
            }).execute()
            return int(resposta.data) if resposta.data is not None else None
        except Exception as exc:
            print(f"Erro ao salvar paciente básico: {type(exc).__name__}.")
            return None

    def soft_delete_paciente(self, paciente_id: int) -> bool:
        """Exclusão lógica — preserva dados clínicos."""
        if not self.supabase or self.consultorio_id is None:
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

    def atualizar_respostas_ficha(self, ficha_id: int, dados_respostas: dict) -> bool:
        """Atualiza apenas as respostas de uma ficha do consultório ativo."""
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            self.supabase.table("fichas_preenchidas").update(
                {"dados_respostas": dados_respostas}
            ).eq("id", ficha_id).eq("consultorio_id", self.consultorio_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao atualizar ficha: {e}")
            return False
