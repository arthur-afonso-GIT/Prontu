import os
import sys
import json
import logging
import mimetypes
import time
import uuid
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

EXTENSOES_ANEXO_FICHA = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
TAMANHO_MAXIMO_ANEXO_FICHA = 15 * 1024 * 1024
LOGGER = logging.getLogger("prontu")


class ErroAnexoFicha(RuntimeError):
    """Falha segura e compreensível ao preparar um anexo clínico."""


def _normalizar_anexos_ficha(valor) -> list[dict]:
    """Converte JSON/texto antigo em uma lista segura de metadados."""
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
    if not isinstance(valor, list):
        return []
    anexos = []
    for item in valor:
        if not isinstance(item, dict):
            continue
        caminho = str(item.get("caminho") or "").strip()
        if not caminho:
            continue
        anexo = {
            "nome": str(item.get("nome") or "Anexo"),
            "caminho": caminho,
            "tipo": str(item.get("tipo") or "application/octet-stream"),
        }
        try:
            if item.get("tamanho") is not None:
                anexo["tamanho"] = max(0, int(item.get("tamanho") or 0))
        except (TypeError, ValueError):
            pass
        anexos.append(anexo)
    return anexos


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

    @staticmethod
    def _executar_leitura_com_recuperacao(operacao, tentativas: int = 3):
        """Repete leituras interrompidas antes de o Supabase concluir a resposta.

        A recuperacao fica restrita a falhas de transporte. Erros reais de banco,
        permissao ou validacao continuam sendo entregues imediatamente ao chamador.
        """
        total = max(1, int(tentativas or 1))
        for numero in range(1, total + 1):
            try:
                return operacao()
            except Exception as erro:
                falha_transitoria = isinstance(erro, httpx.TransportError) or (
                    type(erro).__name__ in {
                        "RemoteProtocolError",
                        "ReadError",
                        "ConnectError",
                        "ReadTimeout",
                    }
                )
                if not falha_transitoria or numero >= total:
                    raise
                LOGGER.warning(
                    "Leitura do Supabase interrompida; nova tentativa %s de %s.",
                    numero + 1,
                    total,
                )
                time.sleep(0.15 * numero)

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
        sessao = getattr(self.session_manager, "_session", None) or {}
        resultado = self._chamar_funcao_auth("criar-acesso-proprietario", {
            # `senha` é o contrato atual. `password` mantém compatibilidade
            # com versões anteriores da Edge Function já implantadas.
            "email": email.strip().lower(),
            "senha": senha,
            "password": senha,
            # Algumas versões já implantadas exigem estes campos no corpo,
            # além de conferi-los novamente contra o JWT do dispositivo.
            "consultorio_id": sessao.get("consultorio_id"),
            "auth_user_id": sessao.get("auth_user_id"),
            "device_id": getattr(self.session_manager, "device_id", None),
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
                .select(
                    "id, acao, entidade, registro_id, contexto, "
                    "valor_anterior, valor_novo, criado_em, "
                    "ator_nome, ator_papel"
                )
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
            resposta = self._executar_leitura_com_recuperacao(
                lambda: (
                    self.supabase.table("retornos_pacientes")
                    .select("id, paciente_id, data_prevista, motivo, status")
                    .eq("consultorio_id", self.consultorio_id)
                    .eq("status", "Pendente")
                    .order("data_prevista", nullsfirst=False)
                    .limit(limite)
                    .execute()
                )
            )
            retornos = resposta.data or []
            ids = list({item.get("paciente_id") for item in retornos if item.get("paciente_id") is not None})
            if not ids:
                return retornos
            pacientes = self._executar_leitura_com_recuperacao(
                lambda: (
                    self.supabase.table("pacientes").select("id, nome")
                    .eq("consultorio_id", self.consultorio_id).in_("id", ids)
                    .is_("deleted_at", "null").execute()
                )
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

    def salvar_configuracao(self, chave: str, valor: str) -> bool:
        """Salva uma configuração e confirma que o valor persistiu no banco."""
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            payload = {
                "consultorio_id": self.consultorio_id,
                "chave": chave,
                "valor": valor,
            }
            existente = (
                self.supabase.table("configuracoes")
                .select("chave")
                .eq("consultorio_id", self.consultorio_id)
                .eq("chave", chave)
                .execute()
            )
            if existente.data:
                (
                    self.supabase.table("configuracoes")
                    .update({"valor": valor})
                    .eq("consultorio_id", self.consultorio_id)
                    .eq("chave", chave)
                    .execute()
                )
            else:
                self.supabase.table("configuracoes").insert(payload).execute()

            valor_confirmado = self.obter_configuracao(chave, default="")
            return valor_confirmado == valor
        except Exception as e:
            print(f"Erro ao salvar configuração {chave}: {e}")
            return False

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

    def listar_pacientes_interface(self) -> list[dict]:
        """Lista pacientes para interfaces desacopladas de Qt Widgets."""
        if not self.supabase or self.consultorio_id is None:
            return []
        if self.obter_papel_atual() == "secretaria":
            return self.listar_pacientes_secretaria(None)
        try:
            resposta = (
                self.supabase.table("pacientes")
                .select("id, nome, telefone, convenio, pasta, cpf, rg")
                .eq("consultorio_id", self.consultorio_id)
                .is_("deleted_at", "null")
                .order("nome")
                .execute()
            )
            return resposta.data or []
        except Exception as erro:
            print(f"Erro ao listar pacientes para a interface: {type(erro).__name__}.")
            return []

    def obter_paciente_interface(self, paciente_id: int) -> dict | None:
        """Obtém um paciente respeitando os campos permitidos ao papel atual."""
        if not self.supabase or self.consultorio_id is None or not paciente_id:
            return None
        if self.obter_papel_atual() == "secretaria":
            return self.obter_paciente_secretaria(paciente_id)
        try:
            resposta = (
                self.supabase.table("pacientes")
                .select(
                    "id, nome, telefone, nascimento, convenio, pasta, sexo, "
                    "cpf, rg, estado_civil, profissao, endereco, queixa, "
                    "lembretes_whatsapp_ativos"
                )
                .eq("id", int(paciente_id))
                .eq("consultorio_id", self.consultorio_id)
                .is_("deleted_at", "null")
                .maybe_single()
                .execute()
            )
            return resposta.data or None
        except Exception as erro:
            print(f"Erro ao obter paciente para a interface: {type(erro).__name__}.")
            return None

    def salvar_paciente_interface(
        self, paciente_id: int | None, dados: dict
    ) -> int | None:
        """Cria ou atualiza um paciente usando o escopo da sessão atual."""
        if not self.supabase or self.consultorio_id is None:
            return None
        if self.obter_papel_atual() == "secretaria":
            return self.salvar_paciente_secretaria(paciente_id, dados)

        permitidos = {
            "nome", "telefone", "nascimento", "convenio", "pasta", "sexo",
            "cpf", "rg", "estado_civil", "profissao", "endereco", "queixa",
            "lembretes_whatsapp_ativos",
        }
        payload = {
            chave: valor for chave, valor in dados.items() if chave in permitidos
        }
        payload["consultorio_id"] = self.consultorio_id
        try:
            if paciente_id is None:
                resposta = self.supabase.table("pacientes").insert(payload).execute()
                linhas = resposta.data or []
                return int(linhas[0]["id"]) if linhas else None

            (
                self.supabase.table("pacientes")
                .update(payload)
                .eq("id", int(paciente_id))
                .eq("consultorio_id", self.consultorio_id)
                .execute()
            )
            return int(paciente_id)
        except Exception as erro:
            print(f"Erro ao salvar paciente pela interface: {type(erro).__name__}.")
            return None

    def listar_pastas_interface(self) -> list[str]:
        """Retorna as pastas da clínica, incluindo as usadas por pacientes."""
        if not self.supabase or self.consultorio_id is None:
            return ["Geral"]
        try:
            pastas = self.supabase.table("pastas").select("nome").eq(
                "consultorio_id", self.consultorio_id
            ).order("nome").execute()
            pacientes = self.supabase.table("pacientes").select("pasta").eq(
                "consultorio_id", self.consultorio_id
            ).is_("deleted_at", "null").execute()
            nomes = ["Geral"]
            nomes.extend(str(item.get("nome") or "").strip() for item in (pastas.data or []))
            nomes.extend(str(item.get("pasta") or "").strip() for item in (pacientes.data or []))
            unicos = {}
            for nome in nomes:
                nome = " ".join(nome.split())
                if nome:
                    unicos.setdefault(nome.casefold(), nome)
            return sorted(
                unicos.values(),
                key=lambda nome: (nome.casefold() != "geral", nome.casefold()),
            )
        except Exception as erro:
            print(f"Erro ao listar pastas para a interface: {type(erro).__name__}.")
            return ["Geral"]

    # --- INTERFACE QML DO PAINEL PRINCIPAL ---
    def listar_home_interface(self) -> dict:
        """Carrega o resumo da Home com poucas consultas e escopo da clínica."""
        if not self.supabase or self.consultorio_id is None:
            return {
                "pacientes": [], "pastas": [], "agenda": [], "retornos": []
            }
        from datetime import date

        hoje = date.today().strftime("%d/%m/%Y")
        try:
            pacientes = (
                self.supabase.table("pacientes")
                .select("id,nome,pasta")
                .eq("consultorio_id", self.consultorio_id)
                .is_("deleted_at", "null")
                .order("id", desc=True)
                .execute()
            )
            pastas = (
                self.supabase.table("pastas")
                .select("nome,cor")
                .eq("consultorio_id", self.consultorio_id)
                .order("nome")
                .execute()
            )
            agenda = (
                self.supabase.table("agenda")
                .select("data,horario,paciente,status,tipo_bloco")
                .eq("consultorio_id", self.consultorio_id)
                .eq("data", hoje)
                .eq("tipo_bloco", "principal")
                .order("horario")
                .execute()
            )
            return {
                "data_hoje": hoje,
                "pacientes": pacientes.data or [],
                "pastas": pastas.data or [],
                "agenda": agenda.data or [],
                "retornos": self.listar_retornos_pendentes(),
            }
        except Exception as erro:
            print(f"Erro ao carregar a Home: {type(erro).__name__}.")
            return {
                "data_hoje": hoje,
                "pacientes": [],
                "pastas": [],
                "agenda": [],
                "retornos": [],
                "erro": True,
            }

    def criar_pasta_interface(self, nome: str, cor: str = "#0284c7") -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        nome = " ".join(str(nome or "").strip().split())
        if not nome:
            return False
        try:
            existentes = self.listar_pastas_interface()
            if nome.casefold() in {item.casefold() for item in existentes}:
                return False
            resposta = self.supabase.table("pastas").insert({
                "consultorio_id": self.consultorio_id,
                "nome": nome,
                "cor": str(cor or "#0284c7"),
            }).execute()
            if not resposta.data:
                return False
            self.registrar_evento_auditoria(
                "INSERT", "pastas", resposta.data[0].get("id"), {"nome": nome}
            )
            return True
        except Exception as erro:
            print(f"Erro ao criar pasta: {type(erro).__name__}.")
            return False

    def renomear_pasta_interface(
        self, nome_atual: str, nome_novo: str
    ) -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        atual = " ".join(str(nome_atual or "").strip().split())
        novo = " ".join(str(nome_novo or "").strip().split())
        if (
            not atual or not novo
            or atual.casefold() == "geral"
        ):
            return False
        try:
            existentes = self.listar_pastas_interface()
            if (
                novo.casefold() != atual.casefold()
                and novo.casefold() in {item.casefold() for item in existentes}
            ):
                return False
            (
                self.supabase.table("pacientes")
                .update({"pasta": novo})
                .eq("consultorio_id", self.consultorio_id)
                .ilike("pasta", atual)
                .is_("deleted_at", "null")
                .execute()
            )
            resposta = (
                self.supabase.table("pastas")
                .update({"nome": novo})
                .eq("consultorio_id", self.consultorio_id)
                .ilike("nome", atual)
                .execute()
            )
            if not resposta.data:
                self.supabase.table("pastas").insert({
                    "consultorio_id": self.consultorio_id,
                    "nome": novo,
                    "cor": "#0284c7",
                }).execute()
            self.registrar_evento_auditoria(
                "UPDATE", "pastas", None,
                {"nome_anterior": atual, "nome_novo": novo},
            )
            return True
        except Exception as erro:
            print(f"Erro ao renomear pasta: {type(erro).__name__}.")
            return False

    def excluir_pasta_interface(self, nome: str) -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        nome = " ".join(str(nome or "").strip().split())
        if not nome or nome.casefold() == "geral":
            return False
        try:
            (
                self.supabase.table("pacientes")
                .update({"pasta": "Geral"})
                .eq("consultorio_id", self.consultorio_id)
                .ilike("pasta", nome)
                .is_("deleted_at", "null")
                .execute()
            )
            (
                self.supabase.table("pastas")
                .delete()
                .eq("consultorio_id", self.consultorio_id)
                .ilike("nome", nome)
                .execute()
            )
            self.registrar_evento_auditoria(
                "DELETE", "pastas", None, {"nome": nome}
            )
            return True
        except Exception as erro:
            print(f"Erro ao excluir pasta: {type(erro).__name__}.")
            return False

    def atualizar_cor_pasta_interface(self, nome: str, cor: str) -> bool:
        if not self.supabase or self.consultorio_id is None:
            return False
        nome = " ".join(str(nome or "").strip().split())
        cor = str(cor or "").strip()
        if not nome or not cor.startswith("#") or len(cor) != 7:
            return False
        try:
            resposta = (
                self.supabase.table("pastas")
                .update({"cor": cor})
                .eq("consultorio_id", self.consultorio_id)
                .ilike("nome", nome)
                .execute()
            )
            if not resposta.data:
                inserida = self.supabase.table("pastas").insert({
                    "consultorio_id": self.consultorio_id,
                    "nome": nome,
                    "cor": cor,
                }).execute()
                if not inserida.data:
                    return False
            return True
        except Exception as erro:
            print(f"Erro ao atualizar cor da pasta: {type(erro).__name__}.")
            return False

    def mover_paciente_pasta_interface(
        self, paciente_id: int, pasta: str
    ) -> bool:
        if not self.supabase or self.consultorio_id is None or not paciente_id:
            return False
        pasta = " ".join(str(pasta or "").strip().split()) or "Geral"
        papel = self.obter_papel_atual().strip().casefold()
        try:
            # Mantém a grafia original da pasta exibida na interface. Isso
            # evita criar variações apenas por diferença de maiúsculas.
            pasta = next(
                (
                    item for item in self.listar_pastas_interface()
                    if item.casefold() == pasta.casefold()
                ),
                pasta,
            )

            if papel in {"secretaria", "secretária"}:
                # A secretária grava pelos RPCs restritos. Uma atualização
                # direta pode ser rejeitada pela RLS sem devolver uma linha.
                paciente = self.obter_paciente_secretaria(int(paciente_id))
                if not paciente:
                    LOGGER.warning(
                        "Paciente não encontrado ao mover pasta | id=%s | papel=%s",
                        int(paciente_id),
                        papel,
                    )
                    return False
                dados_atualizados = dict(paciente)
                dados_atualizados["pasta"] = pasta
                salvo_id = self.salvar_paciente_secretaria(
                    int(paciente_id), dados_atualizados
                )
                if salvo_id != int(paciente_id):
                    LOGGER.warning(
                        "RPC não confirmou movimento de paciente | id=%s | pasta=%s",
                        int(paciente_id),
                        pasta,
                    )
                    return False
                paciente_confirmado = self.obter_paciente_secretaria(
                    int(paciente_id)
                )
                linhas = [paciente_confirmado] if paciente_confirmado else []
            else:
                (
                    self.supabase.table("pacientes")
                    .update({"pasta": pasta})
                    .eq("id", int(paciente_id))
                    .eq("consultorio_id", self.consultorio_id)
                    .is_("deleted_at", "null")
                    .execute()
                )

                # Algumas configurações do PostgREST não devolvem as
                # linhas alteradas. Uma leitura curta confirma o resultado real.
                confirmacao = (
                    self.supabase.table("pacientes")
                    .select("id,pasta")
                    .eq("id", int(paciente_id))
                    .eq("consultorio_id", self.consultorio_id)
                    .is_("deleted_at", "null")
                    .limit(1)
                    .execute()
                )
                linhas = confirmacao.data or []
            if not linhas:
                LOGGER.warning(
                    "Movimento de paciente não localizado após gravação | id=%s | pasta=%s",
                    int(paciente_id),
                    pasta,
                )
                return False
            pasta_salva = " ".join(
                str(linhas[0].get("pasta") or "").strip().split()
            )
            if pasta_salva.casefold() != pasta.casefold():
                LOGGER.warning(
                    "Movimento de paciente divergente | id=%s | esperada=%s | salva=%s",
                    int(paciente_id),
                    pasta,
                    pasta_salva,
                )
                return False
            self.registrar_evento_auditoria(
                "UPDATE", "pacientes", int(paciente_id), {"pasta": pasta}
            )
            return True
        except Exception as erro:
            print(f"Erro ao mover paciente: {type(erro).__name__}.")
            LOGGER.exception(
                "Falha ao mover paciente entre pastas | id=%s | pasta=%s | papel=%s",
                int(paciente_id),
                pasta,
                papel,
            )
            return False

    # --- INTERFACE QML DA AGENDA ---
    def listar_agenda_interface(self, data_consulta: str) -> list[dict]:
        """Lista os blocos de um dia, sempre limitados à clínica autenticada."""
        if not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("agenda")
                .select(
                    "data, horario, paciente, status, procedimento, duracao_txt, "
                    "observacao, tipo_bloco, slots_vinculados, retorno_id"
                )
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("data", str(data_consulta))
                .order("horario")
                .execute()
            )
            linhas = []
            for item in resposta.data or []:
                linha = dict(item)
                slots = linha.get("slots_vinculados")
                if isinstance(slots, str):
                    try:
                        linha["slots_vinculados"] = json.loads(slots)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        linha["slots_vinculados"] = []
                linhas.append(linha)
            return linhas
        except Exception as erro:
            print(f"Erro ao listar agenda para a interface: {type(erro).__name__}.")
            return []

    def listar_agenda_periodo_interface(
        self, datas_consulta: list[str]
    ) -> list[dict]:
        """Lista vários dias em uma única consulta para as visões ampla da agenda."""
        datas = sorted({
            str(data_consulta).strip()
            for data_consulta in datas_consulta
            if str(data_consulta).strip()
        })
        if not datas or not self.supabase or self.consultorio_id is None:
            return []
        try:
            resposta = (
                self.supabase.table("agenda")
                .select(
                    "data, horario, paciente, status, procedimento, duracao_txt, "
                    "observacao, tipo_bloco, slots_vinculados, retorno_id"
                )
                .eq("consultorio_id", int(self.consultorio_id))
                .in_("data", datas)
                .order("data")
                .order("horario")
                .execute()
            )
            linhas = []
            for item in resposta.data or []:
                linha = dict(item)
                slots = linha.get("slots_vinculados")
                if isinstance(slots, str):
                    try:
                        linha["slots_vinculados"] = json.loads(slots)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        linha["slots_vinculados"] = []
                linhas.append(linha)
            return linhas
        except Exception as erro:
            print(f"Erro ao listar período da agenda: {type(erro).__name__}.")
            return []

    def listar_tipos_consulta_personalizados_interface(self) -> list[str]:
        """Retorna somente os procedimentos criados pela clínica."""
        try:
            salvos = json.loads(
                self.obter_configuracao(
                    "agenda_tipos_consulta_personalizados", "[]"
                ) or "[]"
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            salvos = []
        tipos = []
        chaves = set()
        for tipo in salvos if isinstance(salvos, list) else []:
            nome = " ".join(str(tipo or "").split())
            if nome and nome.casefold() not in chaves:
                tipos.append(nome)
                chaves.add(nome.casefold())
        return tipos

    def _salvar_tipos_consulta_personalizados(
        self, tipos: list[str]
    ) -> bool:
        return self.salvar_configuracao(
            "agenda_tipos_consulta_personalizados",
            json.dumps(tipos, ensure_ascii=False),
        )

    def listar_tipos_consulta_interface(self) -> list[str]:
        """Combina os tipos padrão com os tipos personalizados da clínica."""
        from services.agenda_service import TIPOS_CONSULTA_PADRAO

        tipos = list(TIPOS_CONSULTA_PADRAO)
        chaves = {tipo.casefold() for tipo in tipos}
        for nome in self.listar_tipos_consulta_personalizados_interface():
            if nome.casefold() not in chaves:
                tipos.append(nome)
                chaves.add(nome.casefold())
        return tipos

    def adicionar_tipo_consulta_interface(self, nome: str) -> bool:
        """Adiciona um procedimento sem criar nomes duplicados."""
        nome = " ".join(str(nome or "").split())
        if not nome or len(nome) > 80:
            return False
        existentes = self.listar_tipos_consulta_interface()
        if nome.casefold() in {item.casefold() for item in existentes}:
            return False
        personalizados = self.listar_tipos_consulta_personalizados_interface()
        personalizados.append(nome)
        return self._salvar_tipos_consulta_personalizados(personalizados)

    def editar_tipo_consulta_interface(
        self, nome_atual: str, nome_novo: str
    ) -> bool:
        """Renomeia somente um procedimento personalizado."""
        nome_atual = " ".join(str(nome_atual or "").split())
        nome_novo = " ".join(str(nome_novo or "").split())
        if not nome_atual or not nome_novo or len(nome_novo) > 80:
            return False
        personalizados = self.listar_tipos_consulta_personalizados_interface()
        indice = next(
            (
                indice
                for indice, item in enumerate(personalizados)
                if item.casefold() == nome_atual.casefold()
            ),
            None,
        )
        if indice is None:
            return False
        outros = {
            item.casefold()
            for item in self.listar_tipos_consulta_interface()
            if item.casefold() != nome_atual.casefold()
        }
        if nome_novo.casefold() in outros:
            return False
        personalizados[indice] = nome_novo
        return self._salvar_tipos_consulta_personalizados(personalizados)

    def excluir_tipo_consulta_interface(self, nome: str) -> bool:
        """Exclui somente um procedimento personalizado."""
        nome = " ".join(str(nome or "").split())
        personalizados = self.listar_tipos_consulta_personalizados_interface()
        restantes = [
            item for item in personalizados
            if item.casefold() != nome.casefold()
        ]
        if len(restantes) == len(personalizados):
            return False
        return self._salvar_tipos_consulta_personalizados(restantes)

    def salvar_agendamento_interface(
        self, data_consulta: str, horario: str, dados: dict
    ) -> dict:
        """Cria uma consulta e informa claramente quando o horário está ocupado."""
        if not self.supabase or self.consultorio_id is None:
            return {"sucesso": False, "motivo": "erro"}

        from services.agenda_service import slots_da_consulta

        data_consulta = str(data_consulta)
        horario = str(horario)
        duracao = str(dados.get("duracao_txt") or "30 minutos")
        slots = slots_da_consulta(horario, duracao)

        def horarios_ocupados() -> list[str]:
            resposta = (
                self.supabase.table("agenda")
                .select("horario")
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("data", data_consulta)
                .in_("horario", slots)
                .execute()
            )
            return sorted({
                str(item.get("horario") or "").strip()
                for item in resposta.data or []
                if str(item.get("horario") or "").strip()
            })

        try:
            conflitos = horarios_ocupados()
            if conflitos:
                return {
                    "sucesso": False,
                    "motivo": "conflito",
                    "data": data_consulta,
                    "horarios": conflitos,
                }

            paciente = str(dados.get("paciente") or "").strip().upper()
            payloads = []
            for indice, slot in enumerate(slots):
                principal = indice == 0
                payloads.append({
                    "consultorio_id": int(self.consultorio_id),
                    "data": data_consulta,
                    "horario": slot,
                    "paciente": paciente,
                    "status": str(dados.get("status") or "") if principal else "",
                    "procedimento": (
                        str(dados.get("procedimento") or "") if principal else ""
                    ),
                    "duracao_txt": duracao if principal else "",
                    "observacao": (
                        str(dados.get("observacao") or "") if principal else ""
                    ),
                    "tipo_bloco": "principal" if principal else "continua",
                    "retorno_id": dados.get("retorno_id") if principal else None,
                    "slots_vinculados": json.dumps(slots if principal else []),
                })
            self.supabase.table("agenda").insert(payloads).execute()

            retorno_id = dados.get("retorno_id")
            if retorno_id:
                self.atualizar_status_retorno(int(retorno_id), "Agendado")
            return {"sucesso": True}
        except Exception as erro:
            codigo = str(getattr(erro, "code", "") or "")
            mensagem = str(erro)
            if (
                codigo == "23505"
                or "agenda_horario_unico_por_consultorio" in mensagem
                or "duplicate key" in mensagem.casefold()
            ):
                try:
                    conflitos = horarios_ocupados() or slots
                except Exception:
                    conflitos = slots
                return {
                    "sucesso": False,
                    "motivo": "conflito",
                    "data": data_consulta,
                    "horarios": conflitos,
                }
            print(f"Erro ao salvar agenda pela interface: {type(erro).__name__}.")
            return {"sucesso": False, "motivo": "erro"}

    def atualizar_status_agenda_interface(
        self, data_consulta: str, horario: str, novo_status: str
    ) -> bool:
        """Atualiza uma consulta e mantém a decisão de retorno coerente."""
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            consulta = (
                self.supabase.table("agenda")
                .select("paciente, procedimento, retorno_id")
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("data", str(data_consulta))
                .eq("horario", str(horario))
                .eq("tipo_bloco", "principal")
                .maybe_single()
                .execute()
            )
            dados = consulta.data or {}
            if not dados:
                return False

            (
                self.supabase.table("agenda")
                .update({"status": str(novo_status)})
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("data", str(data_consulta))
                .eq("horario", str(horario))
                .eq("tipo_bloco", "principal")
                .execute()
            )

            retorno_id = dados.get("retorno_id")
            if retorno_id:
                if "Realizada" in novo_status:
                    status_retorno = "Concluído"
                elif "Cancelada" in novo_status or "Faltou" in novo_status:
                    status_retorno = "Pendente"
                else:
                    status_retorno = "Agendado"
                self.atualizar_status_retorno(int(retorno_id), status_retorno)
            elif (
                "Realizada" in novo_status
                and str(dados.get("procedimento") or "").strip().casefold()
                != "retorno"
            ):
                self.criar_retorno_pendente_da_consulta(
                    str(dados.get("paciente") or ""),
                    str(data_consulta),
                    str(horario),
                )
            return True
        except Exception as erro:
            print(f"Erro ao atualizar agenda pela interface: {type(erro).__name__}.")
            return False

    # --- INTERFACE QML DAS FICHAS CLÍNICAS ---
    def iniciar_consultas_no_horario_interface(
        self, data_consulta: str, horario_atual: str
    ) -> int:
        """Coloca em atendimento consultas cujo horário acabou de começar."""
        if not self.supabase or self.consultorio_id is None:
            return 0

        from services.agenda_service import (
            consulta_deve_entrar_em_atendimento,
            data_hora_da_consulta,
        )

        try:
            momento_atual = data_hora_da_consulta(
                str(data_consulta), str(horario_atual)
            )
            resposta = (
                self.supabase.table("agenda")
                .select("horario, status, duracao_txt")
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("data", str(data_consulta))
                .eq("tipo_bloco", "principal")
                .execute()
            )
            atualizadas = 0
            for item in resposta.data or []:
                if not consulta_deve_entrar_em_atendimento(
                    str(data_consulta),
                    str(item.get("horario") or ""),
                    str(item.get("duracao_txt") or "30 minutos"),
                    str(item.get("status") or ""),
                    momento_atual,
                ):
                    continue
                if self.atualizar_status_agenda_interface(
                    str(data_consulta),
                    str(item.get("horario") or ""),
                    "🏥 Em Atendimento",
                ):
                    atualizadas += 1
            return atualizadas
        except Exception as erro:
            print(
                "Erro ao sincronizar consultas em atendimento: "
                f"{type(erro).__name__}."
            )
            return 0

    def listar_pacientes_fichas_interface(self) -> list[dict]:
        """Lista somente a identificação necessária para iniciar uma ficha."""
        if (
            not self.supabase
            or self.consultorio_id is None
            or self.obter_papel_atual() == "secretaria"
        ):
            return []
        try:
            resposta = (
                self.supabase.table("pacientes")
                .select("id, nome")
                .eq("consultorio_id", int(self.consultorio_id))
                .is_("deleted_at", "null")
                .order("nome")
                .execute()
            )
            return resposta.data or []
        except Exception as erro:
            print(f"Erro ao listar pacientes das fichas: {type(erro).__name__}.")
            return []

    def listar_modelos_fichas_interface(self) -> list[dict]:
        """Retorna o modelo padrão e os modelos personalizados da clínica."""
        from services.fichas_service import (
            MODELO_PADRAO,
            NOME_MODELO_PADRAO,
            normalizar_estrutura,
        )

        modelos = [{
            "nome": NOME_MODELO_PADRAO,
            "estrutura": normalizar_estrutura(MODELO_PADRAO),
        }]
        if (
            not self.supabase
            or self.consultorio_id is None
            or self.obter_papel_atual() == "secretaria"
        ):
            return modelos
        try:
            resposta = (
                self.supabase.table("modelos_fichas")
                .select("nome_modelo, estrutura_json")
                .eq("consultorio_id", int(self.consultorio_id))
                .order("id", desc=True)
                .execute()
            )
            nomes = {NOME_MODELO_PADRAO.casefold()}
            for item in resposta.data or []:
                nome = str(item.get("nome_modelo") or "").strip()
                if not nome or nome.casefold() in nomes:
                    continue
                estrutura = item.get("estrutura_json")
                if isinstance(estrutura, str):
                    try:
                        estrutura = json.loads(estrutura)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        estrutura = []
                modelos.append({
                    "nome": nome,
                    "estrutura": normalizar_estrutura(estrutura),
                })
                nomes.add(nome.casefold())
            return modelos
        except Exception as erro:
            print(f"Erro ao listar modelos de ficha: {type(erro).__name__}.")
            return modelos

    def listar_historico_fichas_interface(
        self, paciente_id: int
    ) -> list[dict]:
        """Lista fichas anteriores sem trazer todo o conteúdo clínico."""
        if (
            not self.supabase
            or self.consultorio_id is None
            or not paciente_id
            or self.obter_papel_atual() == "secretaria"
        ):
            return []
        try:
            resposta = (
                self.supabase.table("fichas_preenchidas")
                .select("id, modelo_nome, data_atendimento, anexos")
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("paciente_id", int(paciente_id))
                .is_("deleted_at", "null")
                .order("id", desc=True)
                .execute()
            )
            historico = []
            for item in resposta.data or []:
                anexos = item.get("anexos") or []
                if isinstance(anexos, str):
                    try:
                        anexos = json.loads(anexos)
                    except (TypeError, ValueError, json.JSONDecodeError):
                        anexos = []
                historico.append({
                    "id": item.get("id"),
                    "modelo_nome": item.get("modelo_nome") or "Ficha Clínica",
                    "data_atendimento": item.get("data_atendimento") or "",
                    "total_anexos": len(anexos) if isinstance(anexos, list) else 0,
                })
            return historico
        except Exception as erro:
            print(f"Erro ao listar histórico de fichas: {type(erro).__name__}.")
            return []

    def obter_ficha_interface(self, ficha_id: int) -> dict | None:
        """Abre uma ficha existente e recupera a estrutura usada na interface."""
        from services.fichas_service import normalizar_estrutura

        if (
            not self.supabase
            or self.consultorio_id is None
            or not ficha_id
            or self.obter_papel_atual() == "secretaria"
        ):
            return None
        try:
            resposta = (
                self.supabase.table("fichas_preenchidas")
                .select(
                    "id, paciente_id, modelo_nome, dados_respostas, "
                    "data_atendimento, anexos"
                )
                .eq("id", int(ficha_id))
                .eq("consultorio_id", int(self.consultorio_id))
                .is_("deleted_at", "null")
                .maybe_single()
                .execute()
            )
            ficha = dict(resposta.data or {})
            if not ficha:
                return None
            respostas = ficha.get("dados_respostas") or {}
            if isinstance(respostas, str):
                try:
                    respostas = json.loads(respostas)
                except (TypeError, ValueError, json.JSONDecodeError):
                    respostas = {}
            ficha["dados_respostas"] = respostas
            ficha["anexos"] = _normalizar_anexos_ficha(
                ficha.get("anexos")
            )

            nome_modelo = str(ficha.get("modelo_nome") or "")
            modelos = self.listar_modelos_fichas_interface()
            estrutura = next(
                (
                    modelo["estrutura"]
                    for modelo in modelos
                    if modelo["nome"] == nome_modelo
                ),
                None,
            )
            if estrutura is None:
                estrutura = [
                    {
                        "tipo": (
                            "checkbox" if isinstance(valor, bool) else "texto_longo"
                        ),
                        "id": campo_id,
                        "label": str(campo_id).replace("_", " ").capitalize(),
                    }
                    for campo_id, valor in respostas.items()
                ]
            ficha["estrutura"] = normalizar_estrutura(estrutura)
            return ficha
        except Exception as erro:
            print(f"Erro ao abrir ficha pela interface: {type(erro).__name__}.")
            return None

    def salvar_ficha_interface(
        self,
        ficha_id: int | None,
        paciente_id: int,
        modelo_nome: str,
        respostas: dict,
        caminhos_anexos: list[str] | None = None,
        anexos_existentes: list[dict] | None = None,
    ) -> int | None:
        """Cria ou atualiza uma ficha no atendimento original."""
        if (
            not self.supabase
            or self.consultorio_id is None
            or not paciente_id
            or self.obter_papel_atual() == "secretaria"
        ):
            return None
        caminhos_enviados: list[str] = []
        try:
            anexos_finais = _normalizar_anexos_ficha(
                anexos_existentes or []
            )
            anexos_anteriores: list[dict] = []
            if ficha_id:
                anterior = (
                    self.supabase.table("fichas_preenchidas")
                    .select("anexos")
                    .eq("id", int(ficha_id))
                    .eq("consultorio_id", int(self.consultorio_id))
                    .eq("paciente_id", int(paciente_id))
                    .maybe_single()
                    .execute()
                )
                anexos_anteriores = _normalizar_anexos_ficha(
                    (anterior.data or {}).get("anexos")
                )

            for caminho_local in caminhos_anexos or []:
                if not os.path.isfile(caminho_local):
                    raise ErroAnexoFicha(
                        "Um dos arquivos selecionados não existe mais no computador."
                    )
                nome_original = os.path.basename(caminho_local)
                extensao = os.path.splitext(nome_original)[1].lower()
                if extensao not in EXTENSOES_ANEXO_FICHA:
                    raise ErroAnexoFicha(
                        f'O arquivo "{nome_original}" não é uma foto ou PDF suportado.'
                    )
                tamanho = os.path.getsize(caminho_local)
                if tamanho <= 0:
                    raise ErroAnexoFicha(
                        f'O arquivo "{nome_original}" está vazio.'
                    )
                if tamanho > TAMANHO_MAXIMO_ANEXO_FICHA:
                    raise ErroAnexoFicha(
                        f'O arquivo "{nome_original}" ultrapassa o limite de 15 MB.'
                    )
                caminho_bucket = (
                    f"{int(self.consultorio_id)}/{int(paciente_id)}/"
                    f"{uuid.uuid4().hex}{extensao}"
                )
                tipo = mimetypes.guess_type(nome_original)[0] or "application/octet-stream"
                with open(caminho_local, "rb") as arquivo:
                    self.supabase.storage.from_("fichas-anexos").upload(
                        caminho_bucket,
                        arquivo.read(),
                        {"content-type": tipo},
                    )
                caminhos_enviados.append(caminho_bucket)
                anexos_finais.append({
                    "nome": nome_original,
                    "caminho": caminho_bucket,
                    "tipo": tipo,
                    "tamanho": tamanho,
                })

            if ficha_id:
                atualizacao = {
                    "dados_respostas": dict(respostas or {}),
                    "anexos": anexos_finais,
                }
                (
                    self.supabase.table("fichas_preenchidas")
                    .update(atualizacao)
                    .eq("id", int(ficha_id))
                    .eq("consultorio_id", int(self.consultorio_id))
                    .eq("paciente_id", int(paciente_id))
                    .execute()
                )
                mantidos = {
                    item["caminho"]
                    for item in anexos_finais
                    if item.get("caminho")
                }
                removidos = [
                    item["caminho"]
                    for item in anexos_anteriores
                    if item.get("caminho") not in mantidos
                ]
                if removidos:
                    try:
                        self.supabase.storage.from_("fichas-anexos").remove(
                            removidos
                        )
                    except Exception as erro_limpeza:
                        print(
                            "Aviso ao remover anexo antigo: "
                            f"{type(erro_limpeza).__name__}."
                        )
                return int(ficha_id)

            from datetime import datetime

            payload = {
                "consultorio_id": int(self.consultorio_id),
                "paciente_id": int(paciente_id),
                "modelo_nome": str(modelo_nome or "Ficha Clínica"),
                "dados_respostas": dict(respostas or {}),
                "data_atendimento": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "anexos": anexos_finais,
            }
            resposta = (
                self.supabase.table("fichas_preenchidas")
                .insert(payload)
                .execute()
            )
            linhas = resposta.data or []
            return int(linhas[0]["id"]) if linhas else None
        except ErroAnexoFicha:
            if caminhos_enviados:
                try:
                    self.supabase.storage.from_("fichas-anexos").remove(
                        caminhos_enviados
                    )
                except Exception:
                    pass
            raise
        except Exception as erro:
            if caminhos_enviados:
                try:
                    self.supabase.storage.from_("fichas-anexos").remove(
                        caminhos_enviados
                    )
                except Exception:
                    pass
            print(
                "Erro ao salvar ficha pela interface: "
                f"{type(erro).__name__}: {erro}"
            )
            return None

    def salvar_modelo_ficha_interface(
        self, nome_modelo: str, estrutura: list[dict]
    ) -> bool:
        """Cria ou atualiza um modelo sem duplicar nomes na mesma clínica."""
        if (
            not self.supabase
            or self.consultorio_id is None
            or self.obter_papel_atual() == "secretaria"
        ):
            return False
        nome = str(nome_modelo or "").strip()
        if not nome or "padrão" in nome.casefold():
            return False
        try:
            consultorio_id = int(self.consultorio_id)
            existente = (
                self.supabase.table("modelos_fichas")
                .select("id")
                .eq("consultorio_id", consultorio_id)
                .eq("nome_modelo", nome)
                .limit(1)
                .execute()
            )
            primeiro = (existente.data or [None])[0]
            if primeiro:
                (
                    self.supabase.table("modelos_fichas")
                    .update({"estrutura_json": list(estrutura or [])})
                    .eq("id", primeiro["id"])
                    .eq("consultorio_id", consultorio_id)
                    .execute()
                )
            else:
                (
                    self.supabase.table("modelos_fichas")
                    .insert({
                        "consultorio_id": consultorio_id,
                        "nome_modelo": nome,
                        "estrutura_json": list(estrutura or []),
                    })
                    .execute()
                )
            return True
        except Exception as erro:
            print(f"Erro ao salvar modelo pela interface: {type(erro).__name__}.")
            return False

    def excluir_modelo_ficha_interface(self, nome_modelo: str) -> bool:
        """Exclui somente o modelo; fichas preenchidas permanecem preservadas."""
        nome = str(nome_modelo or "").strip()
        if (
            not self.supabase
            or self.consultorio_id is None
            or not nome
            or "padrão" in nome.casefold()
            or self.obter_papel_atual() == "secretaria"
        ):
            return False
        try:
            (
                self.supabase.table("modelos_fichas")
                .delete()
                .eq("consultorio_id", int(self.consultorio_id))
                .eq("nome_modelo", nome)
                .execute()
            )
            return True
        except Exception as erro:
            print(f"Erro ao excluir modelo pela interface: {type(erro).__name__}.")
            return False

    def criar_link_anexo_interface(self, caminho: str) -> str:
        """Gera um endereço temporário para consultar um anexo protegido."""
        if not self.supabase or not caminho:
            return ""
        try:
            prefixo = f"{int(self.consultorio_id)}/"
            if not str(caminho).startswith(prefixo):
                return ""
            resposta = (
                self.supabase.storage.from_("fichas-anexos")
                .create_signed_url(str(caminho), 120)
            )
            if isinstance(resposta, dict):
                url = str(
                    resposta.get("signedURL")
                    or resposta.get("signedUrl")
                    or resposta.get("signed_url")
                    or ""
                )
            else:
                url = str(
                    getattr(resposta, "signed_url", "")
                    or getattr(resposta, "signedURL", "")
                    or resposta
                    or ""
                )
            if url.startswith("/") and self.supabase_url:
                return f"{self.supabase_url}{url}"
            return url
        except Exception as erro:
            print(f"Erro ao abrir anexo pela interface: {type(erro).__name__}.")
            return ""

    # --- INTERFACE QML DO FINANCEIRO ---
    def listar_financeiro_interface(self) -> dict:
        """Carrega agenda e pagamentos da clínica para composição no serviço."""
        if not self.supabase or self.consultorio_id is None:
            return {"agenda": [], "pagamentos": []}
        try:
            consultorio_id = int(self.consultorio_id)
            agenda = self._executar_leitura_com_recuperacao(
                lambda: (
                    self.supabase.table("agenda")
                    .select("data, horario, paciente, procedimento, status")
                    .eq("consultorio_id", consultorio_id)
                    .eq("tipo_bloco", "principal")
                    .execute()
                )
            )
            pagamentos = self._executar_leitura_com_recuperacao(
                lambda: (
                    self.supabase.table("pagamentos_consultas")
                    .select("*")
                    .eq("consultorio_id", consultorio_id)
                    .execute()
                )
            )
            return {
                "agenda": agenda.data or [],
                "pagamentos": pagamentos.data or [],
            }
        except Exception as erro:
            print(f"Erro ao carregar financeiro pela interface: {type(erro).__name__}.")
            return {"agenda": [], "pagamentos": [], "erro": True}

    def salvar_pagamento_interface(self, payload: dict) -> bool:
        """Cria ou atualiza o pagamento vinculado ao horário da agenda."""
        if not self.supabase or self.consultorio_id is None:
            return False
        try:
            consultorio_id = int(self.consultorio_id)
            dados = dict(payload or {})
            dados["consultorio_id"] = consultorio_id
            agenda_data = str(dados.get("agenda_data") or "")
            agenda_horario = str(dados.get("agenda_horario") or "")
            if not agenda_data or not agenda_horario:
                return False
            tabela = self.supabase.table("pagamentos_consultas")
            existente = (
                tabela.select("id")
                .eq("consultorio_id", consultorio_id)
                .eq("agenda_data", agenda_data)
                .eq("agenda_horario", agenda_horario)
                .limit(1)
                .execute()
            )
            primeiro = (existente.data or [None])[0]
            if primeiro:
                tabela.update(dados).eq("id", primeiro["id"]).execute()
                acao = "UPDATE"
            else:
                tabela.insert(dados).execute()
                acao = "INSERT"
            if hasattr(self, "registrar_evento_auditoria"):
                self.registrar_evento_auditoria(
                    acao,
                    "pagamentos_consultas",
                    f"{agenda_data}:{agenda_horario}",
                    {"status_pagamento": dados.get("status")},
                )
            return True
        except Exception as erro:
            print(f"Erro ao salvar pagamento pela interface: {type(erro).__name__}.")
            return False

    def listar_lembretes_whatsapp_interface(self) -> dict:
        """Retorna acompanhamento e franquia sem expor credenciais da Meta."""
        if not self.supabase or self.consultorio_id is None:
            return {"lembretes": [], "resumo": "", "franquia": ""}
        nomes_status = {
            "pendente": "Aguardando envio",
            "processando": "Em processamento",
            "enviado": "Aguardando confirmação",
            "falhou": "Falha no envio",
            "cancelado": "Cancelado",
            "ignorado": "Não enviado",
        }
        nomes_meta = {
            "accepted": "Aceito pela Meta",
            "sent": "Enviado ao WhatsApp",
            "delivered": "Entregue",
            "read": "Lido",
            "failed": "Não entregue",
        }
        try:
            resposta_franquia = self.supabase.rpc(
                "resumo_franquia_lembretes_whatsapp",
                {"p_consultorio_id": self.consultorio_id},
            ).execute()
            resumo = (resposta_franquia.data or [{}])[0]
            limite = int(resumo.get("limite") or 0)
            entregues = int(resumo.get("entregues") or 0)
            reservados = int(resumo.get("reservados") or 0)
            disponiveis = int(resumo.get("disponiveis") or 0)
            franquia = (
                f"{entregues} de {limite} entregues · "
                f"{reservados} aguardando confirmação · "
                f"{disponiveis} disponíveis"
            )
            resposta = (
                self.supabase.table("lembretes_whatsapp")
                .select(
                    "agenda_data,agenda_horario,paciente_nome,procedimento,"
                    "status,meta_status,ultimo_erro,criado_em"
                )
                .eq("consultorio_id", self.consultorio_id)
                .order("criado_em", desc=True)
                .limit(100)
                .execute()
            )
            lembretes = []
            totais = {
                "pendente": 0, "processando": 0,
                "enviado": 0, "falhou": 0,
            }
            for item in resposta.data or []:
                status = str(item.get("status") or "pendente").lower()
                meta_status = str(item.get("meta_status") or "").lower()
                if status in totais:
                    totais[status] += 1
                lembretes.append({
                    "consulta": (
                        f"{item.get('agenda_data') or ''} às "
                        f"{item.get('agenda_horario') or ''}"
                    ),
                    "paciente": str(item.get("paciente_nome") or "Paciente"),
                    "procedimento": str(item.get("procedimento") or "Consulta"),
                    "situacao": nomes_meta.get(
                        meta_status, nomes_status.get(status, status.title())
                    ),
                    "detalhe": str(item.get("ultimo_erro") or "—"),
                    "falhou": status == "falhou" or meta_status == "failed",
                    "entregue": meta_status in {"delivered", "read"},
                })
            texto_resumo = (
                f"{len(lembretes)} lembrete(s): "
                f"{totais['pendente']} aguardando, "
                f"{totais['enviado']} enviado(s) e "
                f"{totais['falhou']} com falha."
            )
            return {
                "lembretes": lembretes,
                "resumo": texto_resumo,
                "franquia": franquia,
            }
        except Exception as erro:
            print(
                "Erro ao listar lembretes para a interface "
                f"({type(erro).__name__})."
            )
            return {"lembretes": [], "resumo": "", "franquia": ""}
