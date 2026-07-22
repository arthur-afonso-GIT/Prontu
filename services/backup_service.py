"""Coleta e restauração de dados para backup local criptografado."""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable

from services.backup_crypto import (
    BackupIntegrityError,
    build_backup_document,
    default_backup_filename,
    read_encrypted_backup,
    write_encrypted_backup,
)

BACKUP_TABLES = [
    "pacientes",
    "pastas",
    "modelos_fichas",
    "fichas_preenchidas",
    "retornos_pacientes",
    "agenda",
    "pagamentos_consultas",
    "configuracoes",
]

# A ordem preserva as relações entre paciente, retorno, agenda e pagamentos.
RESTORE_INSERT_ORDER = [
    "pastas",
    "modelos_fichas",
    "configuracoes",
    "pacientes",
    "retornos_pacientes",
    "fichas_preenchidas",
    "agenda",
    "pagamentos_consultas",
]
RESTORE_DELETE_ORDER = list(reversed(RESTORE_INSERT_ORDER))
SOFT_DELETE_TABLES = {"pacientes", "fichas_preenchidas"}

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
        retention_days: int | None = None,
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
        removidos = self.remove_expired_backups(dest_dir, retention_days)
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
            "expired_removed": removidos,
        }

    def remove_expired_backups(self, dest_dir: str, retention_days: int | None) -> int:
        """Remove somente backups antigos criados para o consultorio atual."""
        try:
            dias = int(retention_days or 0)
        except (TypeError, ValueError):
            return 0
        if dias < 1 or not os.path.isdir(dest_dir):
            return 0

        limite = datetime.now(timezone.utc).timestamp() - (dias * 24 * 60 * 60)
        prefixo = f"prontu_backup_c{self.db.consultorio_id}_"
        removidos = 0
        for nome in os.listdir(dest_dir):
            if not nome.startswith(prefixo) or not nome.endswith(".prntbk"):
                continue
            caminho = os.path.join(dest_dir, nome)
            try:
                if os.path.isfile(caminho) and os.path.getmtime(caminho) < limite:
                    os.remove(caminho)
                    removidos += 1
            except OSError:
                # Falha em um arquivo antigo nao deve invalidar o backup novo.
                continue
        return removidos

    def restore_backup(
        self,
        path: str,
        password: str,
        safe_mode: bool = True,
        replace_existing: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        document = read_encrypted_backup(path, password)
        try:
            backup_cid = int(document.get("consultorio_id"))
        except (TypeError, ValueError):
            raise ValueError("O arquivo não possui a identificação válida do consultório.")
        if backup_cid != self.db.consultorio_id:
            raise ValueError("Este backup pertence a outro consultório e não pode ser restaurado aqui.")

        if replace_existing:
            safe_mode = False

        stats = {"inserted": 0, "skipped": 0, "removed": 0}
        tables_data = document.get("tables") or {}
        if replace_existing:
            ausentes = [table for table in BACKUP_TABLES if table not in tables_data]
            if ausentes:
                raise BackupIntegrityError(
                    "O backup está incompleto e não pode substituir os dados atuais."
                )
            for table in BACKUP_TABLES:
                if not isinstance(tables_data.get(table), list):
                    raise BackupIntegrityError(
                        f"Os dados de {table} estão em formato inválido."
                    )
                if any(not isinstance(row, dict) for row in tables_data[table]):
                    raise BackupIntegrityError(
                        f"Os registros de {table} estão em formato inválido."
                    )
            for table in SOFT_DELETE_TABLES:
                if any(row.get("id") is None for row in tables_data[table]):
                    raise BackupIntegrityError(
                        f"O backup não identifica corretamente os registros de {table}."
                    )
        if replace_existing:
            # A senha já foi validada acima. Só então os dados atuais são removidos.
            for table in RESTORE_DELETE_ORDER:
                if on_progress:
                    on_progress(f"Removendo dados atuais de {table}...")
                try:
                    existentes = (
                        self.db.supabase.table(table)
                        .select("id,consultorio_id")
                        .eq("consultorio_id", self.db.consultorio_id)
                        .execute()
                    )
                    if table in SOFT_DELETE_TABLES:
                        ids_backup = {
                            row["id"] for row in tables_data.get(table, [])
                        }
                        auth_user_id = None
                        if hasattr(self.db, "obter_auth_user_id_atual"):
                            auth_user_id = self.db.obter_auth_user_id_atual()
                        payload_exclusao = {
                            "deleted_at": datetime.now(timezone.utc).isoformat(),
                            "deleted_by": auth_user_id,
                        }
                        removidos_tabela = 0
                        # Pacientes e fichas usam exclusão lógica por
                        # segurança. Arquivamos apenas o que não existe no
                        # backup; registros que serão restaurados continuam
                        # visíveis para o UPSERT sob as regras de RLS.
                        for existente in existentes.data or []:
                            if existente.get("id") in ids_backup:
                                continue
                            (
                                self.db.supabase.table(table)
                                .update(payload_exclusao)
                                .eq("consultorio_id", self.db.consultorio_id)
                                .eq("id", existente["id"])
                                .execute()
                            )
                            removidos_tabela += 1
                    else:
                        (
                            self.db.supabase.table(table)
                            .delete()
                            .eq("consultorio_id", self.db.consultorio_id)
                            .execute()
                        )
                        removidos_tabela = len(existentes.data or [])
                    stats["removed"] += removidos_tabela
                except Exception as exc:
                    print(f"Falha ao preparar substituição em {table}: {exc}")
                    raise RuntimeError(
                        f"Não foi possível preparar a substituição dos dados ({table})."
                    ) from exc

        allowed_tables = set(BACKUP_TABLES)
        for table in RESTORE_INSERT_ORDER:
            rows = tables_data.get(table) or []
            if table not in allowed_tables or not isinstance(rows, list):
                continue
            if on_progress:
                on_progress(f"Restaurando {table}...")
            for row in rows:
                payload = dict(row)
                if not replace_existing:
                    payload.pop("id", None)
                payload["consultorio_id"] = self.db.consultorio_id
                if safe_mode:
                    payload.pop("deleted_at", None)
                    payload.pop("deleted_by", None)
                try:
                    if replace_existing and table in SOFT_DELETE_TABLES:
                        self.db.supabase.table(table).upsert(
                            payload, on_conflict="id"
                        ).execute()
                    else:
                        self.db.supabase.table(table).insert(payload).execute()
                    stats["inserted"] += 1
                except Exception as exc:
                    if replace_existing:
                        print(f"Falha ao restaurar {table}: {exc}")
                        raise RuntimeError(
                            f"Não foi possível restaurar os dados de {table}."
                        ) from exc
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
            contexto={"safe_mode": safe_mode, "replace_existing": replace_existing, **stats},
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
