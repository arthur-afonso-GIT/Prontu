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

    def load_persisted_session(self) -> bool:
        data = self.storage.load_session()
        if not data or not data.get("access_token"):
            return False
        if self._is_expired(data):
            refreshed = self._refresh_tokens(data)
            if refreshed:
                self._session = refreshed
                self.storage.save_session(refreshed)
                return True
            self.storage.clear_session()
            return False
        self._session = data
        return True

    def activate_with_key(self, chave: str, device_name: str | None = None) -> dict[str, Any]:
        """Valida chave na Edge Function e obtém sessão autenticada."""
        fn_url = os.getenv("PRONTU_ACTIVATION_URL", "").rstrip("/")
        if not fn_url:
            raise RuntimeError("Ativacao indisponivel: configure PRONTU_ACTIVATION_URL")
        if not fn_url.endswith("/ativar-consultorio"):
            fn_url = f"{fn_url}/ativar-consultorio"
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
        }
        self._session = session
        self.storage.save_session(session)
        self.storage.mark_legacy_requires_revalidation()
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
        self.storage.save_session(refreshed)
        return True

    def logout(self) -> None:
        self._session = None
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
