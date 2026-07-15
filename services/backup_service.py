"""Coleta e restauração de dados para backup local criptografado."""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable

from services.backup_crypto import (
    build_backup_document,
    default_backup_filename,
    read_encrypted_backup,
    write_encrypted_backup,
)

BACKUP_TABLES = [
    "pacientes",
    "agenda",
    "pastas",
    "modelos_fichas",
    "fichas_preenchidas",
    "configuracoes",
]

ProgressCallback = Callable[[str], None]


class BackupService:
    def __init__(self, db) -> None:
        self.db = db

    def collect_tables(self, on_progress: ProgressCallback | None = None) -> dict[str, list]:
        if not self.db.supabase or self.db.consultorio_id is None:
            return {}
        data: dict[str, list] = {}
        cid = self.db.consultorio_id
        for table in BACKUP_TABLES:
            if on_progress:
                on_progress(f"Coletando {table}...")
            query = (
                self.db.supabase.table(table)
                .select("*")
                .eq("consultorio_id", cid)
            )
            if table in ("pacientes", "fichas_preenchidas"):
                query = query.is_("deleted_at", "null")
            resposta = query.execute()
            data[table] = resposta.data or []
        return data

    def collect_attachments(self, include_content: bool = False) -> list[dict[str, Any]]:
        if not self.db.supabase or self.db.consultorio_id is None:
            return []
        try:
            resposta = (
                self.db.supabase.table("fichas_preenchidas")
                .select("id, anexos")
                .eq("consultorio_id", self.db.consultorio_id)
                .is_("deleted_at", "null")
                .execute()
            )
        except Exception:
            return []
        index = []
        for row in resposta.data or []:
            anexos_raw = row.get("anexos")
            if not anexos_raw:
                continue
            item = {"ficha_id": row["id"], "anexos": anexos_raw}
            if include_content:
                try:
                    anexos = anexos_raw if isinstance(anexos_raw, list) else json.loads(anexos_raw)
                    files = []
                    for anexo in anexos:
                        path = anexo.get("caminho")
                        if not path or not path.startswith(f"{self.db.consultorio_id}/"):
                            continue
                        content = self.db.supabase.storage.from_("fichas-anexos").download(path)
                        files.append({"path": path, "content_b64": base64.b64encode(content).decode("ascii")})
                    item["files"] = files
                except Exception:
                    # A missing attachment must not disclose details or abort
                    # the data backup; metadata remains available for review.
                    item["files"] = []
            index.append(item)
        return index

    def create_backup(
        self,
        dest_dir: str,
        password: str,
        include_attachments: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        tables = self.collect_tables(on_progress)
        attachments = self.collect_attachments(include_content=include_attachments) if include_attachments else []
        document = build_backup_document(
            consultorio_id=self.db.consultorio_id,
            tables_data=tables,
            include_attachments=include_attachments,
            attachments_meta=attachments,
        )
        filename = default_backup_filename(self.db.consultorio_id)
        path = os.path.join(dest_dir, filename)
        size = write_encrypted_backup(path, document, password)
        self.db.registrar_evento_auditoria(
            "backup_export",
            "backup_local",
            contexto={"path_hint": os.path.basename(path), "size_bytes": size},
        )
        return {
            "path": path,
            "size_bytes": size,
            "created_at": document["created_at"],
            "filename": filename,
        }

    def restore_backup(
        self,
        path: str,
        password: str,
        safe_mode: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        document = read_encrypted_backup(path, password)
        backup_cid = document.get("consultorio_id")
        if backup_cid != self.db.consultorio_id:
            if safe_mode:
                raise ValueError(
                    "Backup pertence a outro consultório. "
                    "Use modo seguro apenas após confirmar o destino correto."
                )

        stats = {"inserted": 0, "skipped": 0}
        allowed_tables = set(BACKUP_TABLES)
        for table, rows in (document.get("tables") or {}).items():
            if table not in allowed_tables or not isinstance(rows, list):
                continue
            if on_progress:
                on_progress(f"Restaurando {table}...")
            for row in rows:
                payload = dict(row)
                payload.pop("id", None)
                payload["consultorio_id"] = self.db.consultorio_id
                if safe_mode:
                    payload.pop("deleted_at", None)
                    payload.pop("deleted_by", None)
                try:
                    self.db.supabase.table(table).insert(payload).execute()
                    stats["inserted"] += 1
                except Exception:
                    stats["skipped"] += 1

        # Storage restoration is additive: existing objects are never
        # overwritten, and every object path is restricted to this tenant.
        if document.get("include_attachments"):
            for attachment in document.get("attachments_index") or []:
                for item in attachment.get("files") or []:
                    path = item.get("path", "")
                    if not path.startswith(f"{self.db.consultorio_id}/"):
                        continue
                    try:
                        content = base64.b64decode(item["content_b64"], validate=True)
                        self.db.supabase.storage.from_("fichas-anexos").upload(
                            path, content, {"upsert": "false"}
                        )
                    except Exception:
                        stats["skipped"] += 1

        self.db.registrar_evento_auditoria(
            "backup_restore",
            "backup_local",
            contexto={"safe_mode": safe_mode, **stats},
        )
        return stats

    @staticmethod
    def update_backup_status(db, result: dict[str, Any] | None, error: str | None = None):
        agora = datetime.now(timezone.utc).isoformat()
        if result:
            db.salvar_configuracao("backup_last_success", agora)
            db.salvar_configuracao("backup_last_path", result.get("path", ""))
            db.salvar_configuracao("backup_last_size", str(result.get("size_bytes", 0)))
            db.salvar_configuracao("backup_last_error", "")
        elif error:
            db.salvar_configuracao("backup_last_error", error[:500])
