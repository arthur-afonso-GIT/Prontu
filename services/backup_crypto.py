"""Serviço de backup local criptografado por consultório."""
from __future__ import annotations

import json
import os
import struct
import zlib
from datetime import datetime, timezone
from typing import Any

BACKUP_MAGIC = b"PRNTBK1\x00"
BACKUP_VERSION = 1


class BackupCryptoError(Exception):
    pass


class BackupIntegrityError(Exception):
    pass


def _derive_key(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))


def encrypt_backup_payload(plaintext: bytes, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(password, salt)
    # Bind the ciphertext to the backup format to prevent cross-protocol use.
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, BACKUP_MAGIC)
    return salt + nonce + ciphertext


def decrypt_backup_payload(blob: bytes, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(blob) < 44:
        raise BackupCryptoError("Arquivo de backup inválido ou corrompido.")
    salt, nonce, ciphertext = blob[:16], blob[16:28], blob[28:]
    key = _derive_key(password, salt)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, BACKUP_MAGIC)
    except Exception as exc:
        raise BackupCryptoError("Senha incorreta ou arquivo corrompido.") from exc


def build_backup_document(
    consultorio_id: int,
    tables_data: dict[str, list[dict[str, Any]]],
    include_attachments: bool = False,
    attachments_meta: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": BACKUP_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "consultorio_id": consultorio_id,
        "include_attachments": include_attachments,
        "tables": tables_data,
        "attachments_index": attachments_meta or [],
    }


def serialize_backup(document: dict[str, Any]) -> bytes:
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(raw, level=6)
    size = struct.pack(">I", len(compressed))
    return BACKUP_MAGIC + size + compressed


def parse_backup_file(data: bytes) -> dict[str, Any]:
    if not data.startswith(BACKUP_MAGIC):
        raise BackupIntegrityError("Formato de backup não reconhecido.")
    header_len = len(BACKUP_MAGIC)
    if len(data) < header_len + 4:
        raise BackupIntegrityError("Arquivo truncado.")
    (compressed_len,) = struct.unpack(">I", data[header_len : header_len + 4])
    compressed = data[header_len + 4 : header_len + 4 + compressed_len]
    if len(compressed) != compressed_len:
        raise BackupIntegrityError("Tamanho do payload inconsistente.")
    raw = zlib.decompress(compressed)
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("schema_version", 0) > BACKUP_VERSION:
        raise BackupIntegrityError(
            "Backup criado por versão mais recente do aplicativo."
        )
    return doc


def write_encrypted_backup(path: str, document: dict[str, Any], password: str) -> int:
    plaintext = serialize_backup(document)
    encrypted = encrypt_backup_payload(plaintext, password)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(encrypted)
    return len(encrypted)


def read_encrypted_backup(path: str, password: str) -> dict[str, Any]:
    with open(path, "rb") as fh:
        encrypted = fh.read()
    plaintext = decrypt_backup_payload(encrypted, password)
    return parse_backup_file(plaintext)


def verify_backup_password(path: str, password: str) -> bool:
    try:
        read_encrypted_backup(path, password)
        return True
    except BackupCryptoError:
        return False


def default_backup_filename(consultorio_id: int) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"prontu_backup_c{consultorio_id}_{stamp}.prntbk"
