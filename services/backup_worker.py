"""Worker em segundo plano para backup automático."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from services.backup_service import BackupService


class BackupWorker(QThread):
    finished_ok = Signal(dict)
    finished_error = Signal(str)
    progress = Signal(str)

    def __init__(
        self,
        db,
        dest_dir: str,
        password: str,
        include_attachments: bool = False,
        retention_days: int | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.db = db
        self.dest_dir = dest_dir
        self.password = password
        self.include_attachments = include_attachments
        self.retention_days = retention_days

    def run(self):
        try:
            service = BackupService(self.db)
            result = service.create_backup(
                self.dest_dir,
                self.password,
                include_attachments=self.include_attachments,
                retention_days=self.retention_days,
                on_progress=lambda msg: self.progress.emit(msg),
            )
            BackupService.update_backup_status(self.db, result)
            self.finished_ok.emit(result)
        except Exception as exc:
            BackupService.update_backup_status(self.db, None, str(exc))
            self.finished_error.emit(str(exc))
