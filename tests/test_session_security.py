import json
import tempfile
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

_spec = importlib.util.spec_from_file_location(
    "secure_storage_under_test", Path(__file__).parents[1] / "database" / "secure_storage.py"
)
_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_module)
SecureStorage = _module.SecureStorage


class SessionSecurityTests(unittest.TestCase):
    def test_legacy_consultorio_id_is_only_a_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / ".prontu_config.json"
            legacy.write_text(json.dumps({"consultorio_id": 999}), encoding="utf-8")
            with patch.object(_module, "_legacy_config_path", return_value=str(legacy)):
                storage = SecureStorage()
                storage._keyring = None
                storage._dpapi_available = False
                storage._fallback_path = str(Path(directory) / "session.enc")
                self.assertEqual(storage.load_legacy_consultorio_hint(), 999)
                # A legacy file is not a source of access tokens or a session.
                self.assertIsNone(storage.load_session())
