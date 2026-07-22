import os
import sys
import json
import httpx
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
        self.ultimo_erro_funcao: str | None = None
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
            self._atualizar_contexto_assinatura()

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

    def _atualizar_contexto_assinatura(self) -> None:
        """Atualiza papel e plano ao reabrir o app, sem depender de sessão antiga."""
        if not self.supabase or not self.session_manager or self.consultorio_id is None:
            return
        try:
            sessao = self.session_manager._session or {}
            auth_user_id = sessao.get("auth_user_id")
            if not auth_user_id:
                usuario = self.supabase.auth.get_user()
                auth_user_id = getattr(getattr(usuario, "user", None), "id", None)
            if not auth_user_id:
                return

            vinculo = self.supabase.table("usuarios_consultorios").select("papel").eq(
                "consultorio_id", self.consultorio_id
            ).eq("auth_user_id", auth_user_id).is_("revogado_em", "null").maybe_single().execute()
            assinatura = self.supabase.table("assinaturas_consultorios").select(
                "plano, status, max_usuarios, expira_em, recursos_extras"
            ).eq("consultorio_id", self.consultorio_id).maybe_single().execute()
            dados_assinatura = assinatura.data or {}
            sessao.update({
                "auth_user_id": auth_user_id,
                "papel": (vinculo.data or {}).get("papel") or sessao.get("papel") or "proprietario",
                "plano": dados_assinatura.get("plano") or "solo",
                "status_assinatura": dados_assinatura.get("status") or "ativa",
                "max_usuarios": dados_assinatura.get("max_usuarios") or 1,
                "expira_em": dados_assinatura.get("expira_em"),
                "recursos_extras": dados_assinatura.get("recursos_extras") or [],
            })
            self.session_manager._session = sessao
            if self.session_manager._persist_session:
                self.session_manager.storage.save_session(sessao)
        except Exception as erro:
            print(f"Aviso: nao foi possivel atualizar o plano da sessao ({type(erro).__name__}).")

    def esta_autenticado(self) -> bool:
        return (
            self.session_manager is not None
            and self.session_manager.is_authenticated
            and self.consultorio_id is not None
        )

    def _adotar_sessao_de_login(self, dados: dict, lembrar: bool = True) -> dict | None:
        """Centraliza a persistência da sessão retornada pelo Auth/Edge Function."""
        if not self.session_manager:
            return None
        access = dados.get("access_token")
        consultorio_id = dados.get("consultorio_id")
        if not access or consultorio_id is None:
            return None
        sessao = {
            "access_token": access,
            "refresh_token": dados.get("refresh_token"),
            "expires_at": dados.get("expires_at"),
            "consultorio_id": int(consultorio_id),
            "nome_clinica": dados.get("nome_clinica"),
            "auth_user_id": dados.get("auth_user_id"),
            "papel": dados.get("papel") or "proprietario",
            "plano": dados.get("plano") or "solo",
            "status_assinatura": dados.get("status_assinatura") or "ativa",
            "max_usuarios": dados.get("max_usuarios") or 1,
            "expira_em": dados.get("expira_em"),
            "recursos_extras": dados.get("recursos_extras") or [],
        }
        self.session_manager._session = sessao
        self.session_manager._persist_session = lembrar
        if lembrar:
            self.session_manager.storage.save_session(sessao)
        else:
            self.session_manager.storage.clear_session()
        self.consultorio_id = sessao["consultorio_id"]
        self._aplicar_sessao_no_cliente()
        return sessao

    def entrar_com_email(self, email: str, senha: str, lembrar: bool = True) -> dict | None:
        """Login real pelo Supabase Auth, seguido da identificação do consultório da pessoa."""
        if not self.supabase or not self.session_manager or not email or not senha:
            return None
        try:
            resultado = self.supabase.auth.sign_in_with_password({"email": email, "password": senha})
            sessao_auth = resultado.session
            usuario = resultado.user
            if not sessao_auth or not usuario:
                return None

            vinculo = self.supabase.table("usuarios_consultorios")\
                .select("consultorio_id, papel")\
                .eq("auth_user_id", usuario.id)\
                .is_("revogado_em", "null")\
                .limit(1)\
                .execute()
            if not vinculo.data:
                self.supabase.auth.sign_out()
                return None

            membro = vinculo.data[0]
            consultorio_id = int(membro["consultorio_id"])
            assinatura = self.supabase.table("assinaturas_consultorios")\
                .select("plano, status, max_usuarios, expira_em, recursos_extras")\
                .eq("consultorio_id", consultorio_id)\
                .maybe_single()\
                .execute()
            plano = assinatura.data or {}
            return self._adotar_sessao_de_login({
                "access_token": sessao_auth.access_token,
                "refresh_token": sessao_auth.refresh_token,
                "expires_at": sessao_auth.expires_at,
                "consultorio_id": consultorio_id,
                "auth_user_id": usuario.id,
                "papel": membro.get("papel") or "proprietario",
                "plano": plano.get("plano") or "solo",
                "status_assinatura": plano.get("status") or "ativa",
                "max_usuarios": plano.get("max_usuarios") or 1,
                "expira_em": plano.get("expira_em"),
                "recursos_extras": plano.get("recursos_extras") or [],
            }, lembrar)
        except Exception as erro:
            print(f"Erro ao entrar com e-mail ({type(erro).__name__}).")
            return None

    def obter_papel_atual(self) -> str:
        sessao = getattr(self.session_manager, "_session", None) or {}
        return str(sessao.get("papel") or "proprietario")

    def obter_plano_atual(self) -> str:
        sessao = getattr(self.session_manager, "_session", None) or {}
        return str(sessao.get("plano") or "solo")

    def possui_recurso(self, recurso: str) -> bool:
        sessao = getattr(self.session_manager, "_session", None) or {}
        if recurso in (sessao.get("recursos_extras") or []):
            return True
        por_plano = {
            "solo": set(),
            "equipe": {"equipe", "controle_acesso", "base_compartilhada"},
            "personalizado": {"equipe", "controle_acesso", "base_compartilhada", "personalizacoes"},
        }
        return recurso in por_plano.get(self.obter_plano_atual(), set())

    def obter_resumo_assinatura(self) -> dict:
        sessao = getattr(self.session_manager, "_session", None) or {}
        return {
            "plano": self.obter_plano_atual(),
            "status": sessao.get("status_assinatura") or "ativa",
            "expira_em": sessao.get("expira_em"),
            "max_usuarios": sessao.get("max_usuarios") or 1,
        }

    def _chamar_funcao_auth(self, nome: str, corpo: dict, usar_sessao: bool = False) -> dict | None:
        self.ultimo_erro_funcao = None
        if not self.supabase_url or not self.supabase_key:
            self.ultimo_erro_funcao = "O Prontu não está conectado ao Supabase."
            return None
        token = self.supabase_key
        if usar_sessao and self.session_manager and self.session_manager.access_token:
            token = self.session_manager.access_token
        try:
            resposta = httpx.post(
                f"{self.supabase_url}/functions/v1/{nome}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": self.supabase_key,
                    "Content-Type": "application/json",
                },
                json=corpo,
                timeout=30.0,
            )
            if resposta.status_code >= 400:
                try:
                    conteudo = resposta.json()
                    detalhe = (
                        conteudo.get("error") or conteudo.get("message")
                        if isinstance(conteudo, dict)
                        else None
                    )
                except ValueError:
                    detalhe = None
                self.ultimo_erro_funcao = str(
                    detalhe or "O servidor não conseguiu concluir a solicitação."
                )
                print(
                    f"Função {nome} recusou a solicitação "
                    f"(HTTP {resposta.status_code}): {self.ultimo_erro_funcao}"
                )
                return None
            dados = resposta.json()
            return dados if isinstance(dados, dict) else None
        except (httpx.HTTPError, ValueError) as erro:
            self.ultimo_erro_funcao = "Não foi possível comunicar com o Supabase."
            print(f"Erro na função {nome} ({type(erro).__name__}): {erro}")
            return None

    def obter_ultimo_erro_funcao(self) -> str:
        return self.ultimo_erro_funcao or "Não foi possível concluir a solicitação."

    def aceitar_convite_equipe(self, codigo: str, email: str, senha: str) -> dict | None:
        resultado = self._chamar_funcao_auth("aceitar-convite", {
            "codigo": codigo.strip().upper(),
            "email": email.strip().lower(),
            "senha": senha,
        })
        return self._adotar_sessao_de_login(resultado or {}, lembrar=True)

    def criar_login_proprietario(self, email: str, senha: str) -> bool:
        resultado = self._chamar_funcao_auth("criar-acesso-proprietario", {
            "email": email.strip(), "senha": senha,
        }, usar_sessao=True)
        if resultado and resultado.get("access_token"):
            self._adotar_sessao_de_login(resultado, lembrar=True)
        return bool(resultado and not resultado.get("error"))

    def solicitar_redefinicao_senha(self, email: str) -> bool:
        resultado = self._chamar_funcao_auth("solicitar-redefinicao-senha", {
            "email": email.strip(),
        })
        return bool(resultado and not resultado.get("error"))

    # --- EQUIPE E PERMISSÕES ---
    # As operações abaixo passam pela Edge Function. Assim, a interface nunca
    # recebe credenciais administrativas nem decide limites do plano sozinha.
    def listar_equipe(self) -> dict | None:
        return self._chamar_funcao_auth("equipe", {"acao": "listar"}, usar_sessao=True)

    def criar_convite_equipe(self, nome: str, email: str, papel: str) -> dict | None:
        return self._chamar_funcao_auth(
            "equipe",
            {"acao": "convidar", "nome": nome.strip(), "email": email.strip(), "papel": papel},
            usar_sessao=True,
        )

    def revogar_acesso_equipe(self, tipo: str, identificador: str) -> bool:
        campo = "convite_id" if tipo == "convite" else "membro_id"
        resultado = self._chamar_funcao_auth(
            "equipe", {"acao": "revogar", campo: str(identificador)}, usar_sessao=True
        )
        return bool(resultado and not resultado.get("error"))

    def alterar_papel_equipe(self, membro_id: str, papel: str) -> bool:
        resultado = self._chamar_funcao_auth(
            "equipe", {"acao": "alterar_papel", "membro_id": str(membro_id), "papel": papel}, usar_sessao=True
        )
        return bool(resultado and not resultado.get("error"))

    def renovar_convite_equipe(self, convite_id: str) -> dict | None:
        return self._chamar_funcao_auth(
            "equipe", {"acao": "renovar_convite", "convite_id": str(convite_id)}, usar_sessao=True
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
            "plano": resultado.get("plano") or "solo",
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

    def listar_eventos_auditoria(self, limite: int = 300) -> list[dict]:
        """Retorna somente metadados de auditoria do consultório ativo."""
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("audit_logs")
                .select("id, acao, entidade, registro_id, contexto, valor_anterior, valor_novo, criado_em")
                .eq("consultorio_id", self.consultorio_id)
                .order("criado_em", desc=True)
                .limit(limite)
                .execute()
            )
            return resposta.data or []
        except Exception as erro:
            print(f"Aviso: falha ao listar auditoria ({type(erro).__name__}).")
            return []

    # --- RETORNOS CLÍNICOS ---
    def criar_retorno(self, paciente_id: int, data_prevista: str | None = None, motivo: str = "") -> bool:
        if not self.supabase or self.consultorio_id is None or not paciente_id:
            return False
        try:
            self.supabase.table("retornos_pacientes").insert({
                "consultorio_id": self.consultorio_id,
                "paciente_id": int(paciente_id),
                "data_prevista": data_prevista or None,
                "motivo": (motivo or "").strip(),
                "status": "Pendente",
            }).execute()
            self.registrar_evento_auditoria("INSERT", "retornos_pacientes", paciente_id, {"data_prevista": data_prevista})
            return True
        except Exception as erro:
            print(f"Aviso: falha ao criar retorno ({type(erro).__name__}).")
            return False

    def criar_retorno_pendente_da_consulta(
        self, paciente_nome: str, consulta_data: str = "", consulta_hora: str = ""
    ) -> dict | None:
        """Cria, ou reutiliza, a decisão de retorno aberta após uma consulta concluída."""
        paciente_nome = str(paciente_nome or "").strip()
        if not self.supabase or self.consultorio_id is None or not paciente_nome:
            return None
        try:
            paciente = (
                self.supabase.table("pacientes")
                .select("id, nome")
                .eq("consultorio_id", self.consultorio_id)
                .ilike("nome", paciente_nome)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            if not paciente.data:
                return None

            paciente_id = int(paciente.data[0]["id"])
            nome_cadastrado = str(paciente.data[0].get("nome") or paciente_nome)
            origem = "Retorno criado após consulta realizada"
            if consulta_data or consulta_hora:
                origem += f" | {consulta_data} {consulta_hora}".rstrip()

            existente = (
                self.supabase.table("retornos_pacientes")
                .select("id, paciente_id, data_prevista, motivo, status, criado_em")
                .eq("consultorio_id", self.consultorio_id)
                .eq("paciente_id", paciente_id)
                .eq("motivo", origem)
                .order("criado_em", desc=True)
                .limit(1)
                .execute()
            )
            if existente.data:
                retorno = dict(existente.data[0])
                retorno["paciente_nome"] = nome_cadastrado
                return retorno

            # Compatibilidade com pendências criadas antes de a consulta de origem
            # passar a ser registrada no motivo.
            pendente_anterior = (
                self.supabase.table("retornos_pacientes")
                .select("id, paciente_id, data_prevista, motivo, status, criado_em")
                .eq("consultorio_id", self.consultorio_id)
                .eq("paciente_id", paciente_id)
                .eq("status", "Pendente")
                .order("criado_em", desc=True)
                .limit(1)
                .execute()
            )
            if pendente_anterior.data:
                retorno = dict(pendente_anterior.data[0])
                retorno["paciente_nome"] = nome_cadastrado
                return retorno

            resposta = self.supabase.table("retornos_pacientes").insert({
                "consultorio_id": self.consultorio_id,
                "paciente_id": paciente_id,
                "data_prevista": None,
                "motivo": origem,
                "status": "Pendente",
            }).execute()
            if not resposta.data:
                return None
            retorno = dict(resposta.data[0])
            retorno["paciente_nome"] = nome_cadastrado
            self.registrar_evento_auditoria(
                "INSERT", "retornos_pacientes", retorno.get("id") or paciente_id,
                {"origem": "consulta_realizada", "paciente_id": paciente_id},
            )
            return retorno
        except Exception as erro:
            print(f"Aviso: falha ao criar retorno da consulta ({type(erro).__name__}).")
            return None

    def listar_retornos_pendentes(self, limite: int = 100) -> list[dict]:
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("retornos_pacientes")
                .select("id, paciente_id, data_prevista, motivo, status")
                .eq("consultorio_id", self.consultorio_id)
                .eq("status", "Pendente")
                .order("data_prevista", nullsfirst=False)
                .limit(limite)
                .execute()
            )
            retornos = resposta.data or []
            ids = list({item.get("paciente_id") for item in retornos if item.get("paciente_id") is not None})
            if not ids:
                return retornos
            pacientes = (
                self.supabase.table("pacientes").select("id, nome")
                .eq("consultorio_id", self.consultorio_id).in_("id", ids)
                .is_("deleted_at", "null").execute()
            )
            nomes = {item["id"]: item.get("nome", "Paciente") for item in (pacientes.data or [])}
            for retorno in retornos:
                retorno["paciente_nome"] = nomes.get(retorno.get("paciente_id"), "Paciente indisponível")
            return retornos
        except Exception as erro:
            print(f"Aviso: falha ao listar retornos ({type(erro).__name__}).")
            return []

    def listar_retornos_paciente(self, paciente_id: int) -> list[dict]:
        if not self.supabase or self.consultorio_id is None or not paciente_id:
            return []
        try:
            resposta = (
                self.supabase.table("retornos_pacientes")
                .select("id, data_prevista, motivo, status, criado_em")
                .eq("consultorio_id", self.consultorio_id).eq("paciente_id", int(paciente_id))
                .order("criado_em", desc=True).execute()
            )
            return resposta.data or []
        except Exception as erro:
            print(f"Aviso: falha ao listar retornos do paciente ({type(erro).__name__}).")
            return []

    def atualizar_status_retorno(self, retorno_id: int, status: str) -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        permitidos = {"Pendente", "Agendado", "Concluído", "Não retornou", "Cancelado"}
        if status not in permitidos:
            return False
        try:
            self.supabase.table("retornos_pacientes").update({"status": status}).eq(
                "id", int(retorno_id)
            ).eq("consultorio_id", self.consultorio_id).execute()
            self.registrar_evento_auditoria("UPDATE", "retornos_pacientes", retorno_id, {"status": status})
            return True
        except Exception as erro:
            print(f"Aviso: falha ao atualizar retorno ({type(erro).__name__}).")
            return False

    def definir_data_retorno(self, retorno_id: int, data_prevista: str) -> bool:
        if not self.supabase or self.consultorio_id is None or not retorno_id or not data_prevista:
            return False
        try:
            self.supabase.table("retornos_pacientes").update({"data_prevista": data_prevista}).eq(
                "id", int(retorno_id)
            ).eq("consultorio_id", self.consultorio_id).execute()
            return True
        except Exception as erro:
            print(f"Aviso: falha ao definir data do retorno ({type(erro).__name__}).")
            return False

    # --- FUNÇÕES DE CONFIGURAÇÃO ---
    def obter_auth_user_id_atual(self):
        sessao = getattr(self.session_manager, "_session", None) or {}
        auth_user_id = sessao.get("auth_user_id")
        if auth_user_id:
            return str(auth_user_id)
        if not self.supabase:
            return None
        try:
            resposta = self.supabase.auth.get_user()
            usuario = getattr(resposta, "user", None)
            return str(usuario.id) if usuario and usuario.id else None
        except Exception:
            return None

    def _nome_do_metadata_auth(self):
        if not self.supabase:
            return ""
        try:
            resposta = self.supabase.auth.get_user()
            usuario = getattr(resposta, "user", None)
            metadata = getattr(usuario, "user_metadata", None) or {}
            for chave in ("nome", "full_name", "name"):
                nome = str(metadata.get(chave) or "").strip()
                if nome:
                    return nome
        except Exception:
            pass
        return ""

    def obter_nome_profissional(self):
        """Retorna o nome individual do usuário conectado, com compatibilidade legada."""
        if not self.supabase or self.consultorio_id is None:
            return ""
        try:
            auth_user_id = self.obter_auth_user_id_atual()
            if auth_user_id:
                perfil = (
                    self.supabase.table("usuarios_consultorios")
                    .select("nome_exibicao")
                    .eq("consultorio_id", self.consultorio_id)
                    .eq("auth_user_id", auth_user_id)
                    .is_("revogado_em", "null")
                    .maybe_single()
                    .execute()
                )
                nome_individual = str((perfil.data or {}).get("nome_exibicao") or "").strip()
                if nome_individual:
                    return nome_individual

            nome_metadata = self._nome_do_metadata_auth()
            if nome_metadata:
                return nome_metadata

            # Compatibilidade para o proprietário que já usava a configuração antiga.
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
            return False
        try:
            auth_user_id = self.obter_auth_user_id_atual()
            if not auth_user_id:
                return False
            resposta = (
                self.supabase.table("usuarios_consultorios")
                .update({"nome_exibicao": nome.strip() or None})
                .eq("consultorio_id", self.consultorio_id)
                .eq("auth_user_id", auth_user_id)
                .is_("revogado_em", "null")
                .execute()
            )
            return bool(resposta.data)
        except Exception as e:
            print(f"Erro ao salvar nome profissional: {e}")
            return False

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

    def obter_telefone_paciente_por_nome(self, nome: str) -> str:
        """Retorna o telefone do paciente da clínica para ações manuais do WhatsApp."""
        nome = str(nome or "").strip()
        if not self.supabase or self.consultorio_id is None or not nome:
            return ""
        try:
            resposta = (
                self.supabase.table("pacientes")
                .select("telefone")
                .eq("consultorio_id", self.consultorio_id)
                .ilike("nome", nome)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            if resposta.data:
                return str(resposta.data[0].get("telefone") or "").strip()
        except Exception as e:
            print(f"Erro ao buscar telefone do paciente: {type(e).__name__}.")
        return ""

    def soft_delete_paciente(self, paciente_id: int) -> bool:
        """Exclusão lógica — preserva dados clínicos."""
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            from datetime import datetime, timezone
            agora = datetime.now(timezone.utc).isoformat()
            self.supabase.table("pacientes").update({"deleted_at": agora}).eq(
                "id", int(paciente_id)
            ).eq("consultorio_id", self.consultorio_id).execute()
            self.supabase.table("fichas_preenchidas").update({"deleted_at": agora}).eq(
                "paciente_id", int(paciente_id)
            ).eq("consultorio_id", self.consultorio_id).execute()
            return True
        except Exception as erro:
            print(f"Erro ao excluir paciente: {erro}")
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
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            self.supabase.table("fichas_preenchidas").update({
                "dados_respostas": dados_respostas
            }).eq("id", int(ficha_id)).eq("consultorio_id", self.consultorio_id).execute()
            return True
        except Exception as erro:
            print(f"Erro ao atualizar ficha: {erro}")
            return False

    def listar_pacientes_secretaria(self, busca: str | None = None) -> list[dict]:
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = self.supabase.rpc("listar_pacientes_secretaria", {"p_busca": busca}).execute()
            return resposta.data or []
        except Exception as erro:
            print(f"Erro ao listar pacientes básicos: {type(erro).__name__}.")
            return []

    def obter_paciente_secretaria(self, paciente_id: int) -> dict | None:
        if not self.supabase or not paciente_id:
            return None
        try:
            resposta = self.supabase.rpc("obter_paciente_secretaria", {"p_paciente_id": int(paciente_id)}).execute()
            dados = resposta.data or []
            return dados[0] if isinstance(dados, list) and dados else None
        except Exception as erro:
            print(f"Erro ao obter paciente básico: {type(erro).__name__}.")
            return None

    def salvar_paciente_secretaria(self, paciente_id: int | None, dados: dict) -> int | None:
        if not self.supabase:
            return None
        try:
            resposta = self.supabase.rpc("salvar_paciente_secretaria", {
                "p_paciente_id": paciente_id,
                "p_nome": dados.get("nome"),
                "p_telefone": dados.get("telefone"),
                "p_nascimento": dados.get("nascimento"),
                "p_convenio": dados.get("convenio"),
                "p_pasta": dados.get("pasta"),
                "p_sexo": dados.get("sexo"),
            }).execute()
            return int(resposta.data) if resposta.data is not None else None
        except Exception as erro:
            print(f"Erro ao salvar paciente básico: {type(erro).__name__}.")
            return None
