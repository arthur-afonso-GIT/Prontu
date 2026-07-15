import tempfile
import unittest
import importlib.util
from pathlib import Path

from services.backup_crypto import (
    BackupCryptoError,
    build_backup_document,
    read_encrypted_backup,
    write_encrypted_backup,
)


@unittest.skipUnless(importlib.util.find_spec("cryptography"), "cryptography is not installed")
class BackupCryptoTests(unittest.TestCase):
    def test_round_trip_requires_correct_password(self):
        document = build_backup_document(7, {"pacientes": [{"id": 1, "nome": "Teste"}]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.prntbk"
            write_encrypted_backup(str(path), document, "senha-forte-de-teste")
            self.assertEqual(
                read_encrypted_backup(str(path), "senha-forte-de-teste")["consultorio_id"], 7
            )
            with self.assertRaises(BackupCryptoError):
                read_encrypted_backup(str(path), "senha-errada")
