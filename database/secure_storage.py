"""
Armazenamento seguro de tokens de sessão no Windows (Credential Manager via keyring).

Fallback: DPAPI no Windows (cryptography) ou arquivo restrito com aviso documentado.
Nunca grava access_token em JSON simples sem proteção.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

SERVICE_NAME = "Prontu-SaaS"
ACCOUNT_PREFIX = "session_"


def _device_account() -> str:
    return f"{ACCOUNT_PREFIX}device"


def _legacy_config_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".prontu_config.json")


class SecureStorage:
    """Adaptador unificado para persistir sessão autenticada localmente."""

    def __init__(self) -> None:
        self._keyring = None
        try:
            import keyring  # type: ignore

            self._keyring = keyring
        except ImportError:
            self._keyring = None
        self._dpapi_available = sys.platform == "win32"
        self._fallback_path = os.path.join(
            os.path.expanduser("~"), ".prontu_session.enc"
        )

    @property
    def backend(self) -> str:
        if self._keyring is not None:
            return "keyring"
        if self._dpapi_available:
            return "dpapi_file"
        return "restricted_file"

    def save_session(self, payload: dict[str, Any]) -> bool:
        raw = json.dumps(payload, ensure_ascii=False)
        if self._keyring is not None:
            try:
                self._keyring.set_password(SERVICE_NAME, _device_account(), raw)
                return True
            except Exception as exc:
                print(f"Aviso: keyring indisponível ({exc}); usando fallback.")
        return self._save_fallback(raw)

    def load_session(self) -> dict[str, Any] | None:
        if self._keyring is not None:
            try:
                raw = self._keyring.get_password(SERVICE_NAME, _device_account())
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                print(f"Aviso: falha ao ler keyring ({exc}).")
        return self._load_fallback()

    def clear_session(self) -> None:
        if self._keyring is not None:
            try:
                self._keyring.delete_password(SERVICE_NAME, _device_account())
            except Exception:
                pass
        if os.path.exists(self._fallback_path):
            try:
                os.remove(self._fallback_path)
            except OSError:
                pass

    def get_or_create_device_id(self) -> str:
        path = os.path.join(os.path.expanduser("~"), ".prontu_device_id")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    device_id = fh.read().strip()
                    if device_id:
                        return device_id
            except OSError:
                pass
        import uuid

        device_id = str(uuid.uuid4())
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(device_id)
        except OSError as exc:
            print(f"Aviso: não foi possível persistir device_id ({exc}).")
        return device_id

    def load_legacy_consultorio_hint(self) -> int | None:
        """Lê consultorio_id legado apenas como hint — NÃO autentica."""
        path = _legacy_config_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            val = data.get("consultorio_id")
            return int(val) if val is not None else None
        except (OSError, ValueError, TypeError):
            return None

    def mark_legacy_requires_revalidation(self) -> None:
        """Marca config legado para forçar revalidação da chave."""
        path = _legacy_config_path()
        payload = {"requires_revalidation": True}
        hint = self.load_legacy_consultorio_hint()
        if hint is not None:
            payload["previous_consultorio_id"] = hint
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except OSError:
            pass

    def _save_fallback(self, raw: str) -> bool:
        try:
            blob = self._protect(raw.encode("utf-8"))
        except RuntimeError:
            return False
        try:
            with open(self._fallback_path, "wb") as fh:
                fh.write(blob)
            if sys.platform != "win32":
                try:
                    os.chmod(self._fallback_path, 0o600)
                except OSError:
                    pass
            return True
        except OSError as exc:
            print(f"Erro ao salvar sessão (fallback): {exc}")
            return False

    def _load_fallback(self) -> dict[str, Any] | None:
        if not os.path.exists(self._fallback_path):
            return None
        try:
            with open(self._fallback_path, "rb") as fh:
                blob = fh.read()
            raw = self._unprotect(blob)
            if raw is None:
                return None
            return json.loads(raw.decode("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _protect(self, data: bytes) -> bytes:
        if self._dpapi_available:
            try:
                import win32crypt  # type: ignore

                return win32crypt.CryptProtectData(data, None, None, None, None, 0)
            except ImportError:
                pass
        # Fallback genérico: base64 + permissões restritas (documentado como limitado)
        # Do not downgrade tokens to merely encoded data. If neither the OS
        # vault nor DPAPI is available, the session remains memory-only.
        raise RuntimeError("Secure token storage is unavailable")

    def _unprotect(self, blob: bytes) -> bytes | None:
        if self._dpapi_available and not blob.startswith(b"PLAIN:"):
            try:
                import win32crypt  # type: ignore

                return win32crypt.CryptUnprotectData(blob, None, None, None, 0)[1]
            except ImportError:
                pass
        return None
