"""
Gerenciamento de sessão Supabase Auth para consultórios ativados por chave.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from database.secure_storage import SecureStorage


class SessionExpiredError(Exception):
    """Sessão expirada ou revogada — requer revalidação da chave."""


class SessionManager:
    """Valida chave via Edge Function e mantém sessão autenticada."""

    def __init__(self, supabase_url: str, supabase_anon_key: str) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.supabase_anon_key = supabase_anon_key
        self.storage = SecureStorage()
        self.device_id = self.storage.get_or_create_device_id()
        self._session: dict[str, Any] | None = None
        self._persist_session = False

    @property
    def is_authenticated(self) -> bool:
        return self._session is not None and bool(self._session.get("access_token"))

    @property
    def consultorio_id(self) -> int | None:
        if not self._session:
            return None
        cid = self._session.get("consultorio_id")
        return int(cid) if cid is not None else None

    @property
    def access_token(self) -> str | None:
        return (self._session or {}).get("access_token")

    @property
    def refresh_token(self) -> str | None:
        return (self._session or {}).get("refresh_token")

    @property
    def plano(self) -> str:
        """Plano recebido na ativação; usado apenas para liberar recursos futuros."""
        return str((self._session or {}).get("plano") or "solo")

    @property
    def recursos_extras(self) -> list[str]:
        recursos = (self._session or {}).get("recursos_extras") or []
        return recursos if isinstance(recursos, list) else []

    @property
    def papel(self) -> str:
        return str((self._session or {}).get("papel") or "proprietario")

    def load_persisted_session(self) -> bool:
        data = self.storage.load_session()
        if not data or not data.get("access_token"):
            return False
        if self._is_expired(data):
            refreshed = self._refresh_tokens(data)
            if refreshed:
                self._session = refreshed
                self.storage.save_session(refreshed)
                self._persist_session = True
                return True
            self.storage.clear_session()
            return False
        self._session = data
        self._persist_session = True
        return True

    def activate_with_key(self, chave: str, device_name: str | None = None) -> dict[str, Any]:
        """Valida chave na Edge Function e obtém sessão autenticada."""
        fn_url = os.getenv("SUPABASE_ACTIVATE_URL") or (
            f"{self.supabase_url}/functions/v1/ativar-consultorio"
        )
        headers = {
            "Authorization": f"Bearer {self.supabase_anon_key}",
            "apikey": self.supabase_anon_key,
            "Content-Type": "application/json",
        }
        body = {
            "chave": chave.strip(),
            "device_id": self.device_id,
            "device_name": device_name or os.environ.get("COMPUTERNAME", "desktop"),
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(fn_url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Falha ao contactar servidor de ativação: {exc}") from exc

        if resp.status_code == 401:
            return {}
        if resp.status_code >= 400:
            detail = resp.text[:200] if resp.text else resp.status_code
            raise RuntimeError(f"Erro na ativação ({resp.status_code}): {detail}")

        payload = resp.json()
        if not payload.get("access_token"):
            return {}

        session = {
            "access_token": payload["access_token"],
            "refresh_token": payload.get("refresh_token"),
            "expires_at": payload.get("expires_at"),
            "consultorio_id": payload.get("consultorio_id"),
            "nome_clinica": payload.get("nome_clinica"),
            "auth_user_id": payload.get("auth_user_id"),
            "plano": payload.get("plano") or "solo",
            "status_assinatura": payload.get("status_assinatura") or "ativa",
            "expira_em": payload.get("expira_em"),
            "max_usuarios": payload.get("max_usuarios") or 1,
            "recursos_extras": payload.get("recursos_extras") or [],
            "papel": payload.get("papel") or "proprietario",
        }
        self._session = session
        self._persist_session = bool(self.storage.save_session(session))
        self.storage.mark_legacy_requires_revalidation()
        return session

    def login_with_email(self, email: str, senha: str, device_name: str | None = None, lembrar: bool = True) -> dict[str, Any]:
        return self._chamar_funcao_sessao(
            "entrar-equipe", {"email": email, "senha": senha}, device_name, lembrar=lembrar
        )

    def accept_invite(self, codigo: str, email: str, senha: str, device_name: str | None = None) -> dict[str, Any]:
        return self._chamar_funcao_sessao(
            "aceitar-convite", {"codigo": codigo, "email": email, "senha": senha}, device_name
        )

    def create_owner_login(self, email: str, senha: str, device_name: str | None = None) -> dict[str, Any]:
        return self._chamar_funcao_sessao(
            "criar-acesso-proprietario", {"email": email, "senha": senha}, device_name, usar_sessao_atual=True
        )

    def request_password_reset(self, email: str) -> bool:
        """Solicita o e-mail de recuperação sem expor se existe uma conta."""
        headers = {"Authorization": f"Bearer {self.supabase_anon_key}", "apikey": self.supabase_anon_key, "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.supabase_url}/functions/v1/solicitar-redefinicao-senha", json={"email": email}, headers=headers)
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def gerenciar_equipe(self, acao: str, **dados: Any) -> dict[str, Any]:
        """Chama a Edge Function da equipe usando a sessao autenticada atual."""
        if not self.access_token:
            raise RuntimeError("Sua sessao expirou. Entre novamente para continuar.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "apikey": self.supabase_anon_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resposta = client.post(
                    f"{self.supabase_url}/functions/v1/equipe",
                    json={"acao": acao, **dados},
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise ConnectionError("Nao foi possivel contactar o servico da equipe.") from exc

        if resposta.status_code >= 400:
            try:
                detalhe = str(resposta.json().get("error") or "Operacao nao concluida")
            except ValueError:
                detalhe = "Operacao nao concluida"
            raise RuntimeError(detalhe)
        return resposta.json()

    def _chamar_funcao_sessao(self, nome_funcao: str, dados: dict[str, Any], device_name: str | None, usar_sessao_atual: bool = False, lembrar: bool = True) -> dict[str, Any]:
        token = self.access_token if usar_sessao_atual else self.supabase_anon_key
        if not token:
            raise RuntimeError("Sessao indisponivel")
        headers = {"Authorization": f"Bearer {token}", "apikey": self.supabase_anon_key, "Content-Type": "application/json"}
        body = {**dados, "device_id": self.device_id, "device_name": device_name or os.environ.get("COMPUTERNAME", "desktop")}
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{self.supabase_url}/functions/v1/{nome_funcao}", json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Falha ao contactar o serviço de acesso: {exc}") from exc
        if resp.status_code >= 400:
            try:
                detalhe = str(resp.json().get("error") or "Acesso indisponível")
            except ValueError:
                detalhe = "Acesso indisponível"
            raise RuntimeError(detalhe)
        payload = resp.json()
        if not payload.get("access_token"):
            raise RuntimeError("Acesso indisponível")
        session = {
            "access_token": payload["access_token"], "refresh_token": payload.get("refresh_token"),
            "expires_at": payload.get("expires_at"), "consultorio_id": payload.get("consultorio_id"),
            "nome_clinica": payload.get("nome_clinica"), "auth_user_id": payload.get("user", {}).get("id") or payload.get("auth_user_id"),
            "plano": payload.get("plano") or "solo", "status_assinatura": payload.get("status_assinatura") or "ativa",
            "expira_em": payload.get("expira_em"), "max_usuarios": payload.get("max_usuarios") or 1,
            "recursos_extras": payload.get("recursos_extras") or [], "papel": payload.get("papel") or "proprietario",
        }
        self._session = session
        self._persist_session = False
        if lembrar:
            self._persist_session = bool(self.storage.save_session(session))
            if not self._persist_session:
                print("Aviso: sessão ativa, mas não foi possível salvá-la neste dispositivo.")
        else:
            self.storage.clear_session()
        return session

    def refresh_if_needed(self) -> bool:
        if not self._session:
            return False
        if not self._is_expired(self._session):
            return True
        refreshed = self._refresh_tokens(self._session)
        if not refreshed:
            raise SessionExpiredError("Sessão expirada. Revalide a chave de acesso.")
        self._session = refreshed
        if self._persist_session:
            self.storage.save_session(refreshed)
        return True

    def logout(self) -> None:
        self._session = None
        self._persist_session = False
        self.storage.clear_session()

    def _refresh_tokens(self, session: dict[str, Any]) -> dict[str, Any] | None:
        refresh = session.get("refresh_token")
        if not refresh:
            return None
        url = f"{self.supabase_url}/auth/v1/token?grant_type=refresh_token"
        headers = {
            "apikey": self.supabase_anon_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, json={"refresh_token": refresh}, headers=headers)
            if resp.status_code >= 400:
                return None
            data = resp.json()
        except httpx.HTTPError:
            return None

        updated = dict(session)
        updated["access_token"] = data.get("access_token")
        updated["refresh_token"] = data.get("refresh_token", refresh)
        updated["expires_at"] = self._expires_at_from_response(data)
        return updated

    @staticmethod
    def _expires_at_from_response(data: dict[str, Any]) -> int | None:
        if "expires_at" in data:
            return int(data["expires_at"])
        expires_in = data.get("expires_in")
        if expires_in:
            return int(datetime.now(timezone.utc).timestamp()) + int(expires_in)
        return None

    def _is_expired(self, session: dict[str, Any], skew_seconds: int = 120) -> bool:
        expires_at = session.get("expires_at")
        if expires_at is None:
            return False
        now = int(datetime.now(timezone.utc).timestamp())
        return now >= (int(expires_at) - skew_seconds)
