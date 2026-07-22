from types import SimpleNamespace

import pytest

from services.backup_crypto import BackupIntegrityError, build_backup_document
from services.backup_service import BACKUP_TABLES, BackupService


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.operation = "select"
        self.filters = []
        self.payload = None

    def select(self, _columns):
        self.operation = "select"
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = dict(payload)
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = dict(payload)
        return self

    def upsert(self, payload, on_conflict="id"):
        self.operation = "upsert"
        self.payload = dict(payload)
        self.on_conflict = on_conflict
        return self

    def _matches(self, row):
        return all(row.get(column) == value for column, value in self.filters)

    def execute(self):
        rows = self.client.rows.setdefault(self.table, [])
        if self.operation == "select":
            return SimpleNamespace(data=[dict(row) for row in rows if self._matches(row)])
        if self.operation == "update":
            for row in rows:
                if self._matches(row):
                    row.update(self.payload)
            return SimpleNamespace(data=[])
        if self.operation == "delete":
            self.client.rows[self.table] = [row for row in rows if not self._matches(row)]
            return SimpleNamespace(data=[])
        if self.operation == "insert":
            rows.append(dict(self.payload))
            return SimpleNamespace(data=[dict(self.payload)])
        if self.operation == "upsert":
            key = self.payload[self.on_conflict]
            current = next((row for row in rows if row.get(self.on_conflict) == key), None)
            if current is None:
                rows.append(dict(self.payload))
            else:
                current.update(self.payload)
            return SimpleNamespace(data=[dict(self.payload)])
        raise AssertionError(f"Operação não suportada: {self.operation}")


class FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return FakeQuery(self, name)


class FakeDatabase:
    consultorio_id = 2

    def __init__(self, rows):
        self.supabase = FakeSupabase(rows)
        self.audit = []

    def obter_auth_user_id_atual(self):
        return "00000000-0000-0000-0000-000000000002"

    def registrar_evento_auditoria(self, evento, recurso, contexto=None):
        self.audit.append((evento, recurso, contexto))


def _documento_completo(**overrides):
    tables = {table: [] for table in BACKUP_TABLES}
    tables.update(overrides)
    return build_backup_document(2, tables)


def test_substituir_arquiva_extras_e_restaura_backup(monkeypatch):
    rows = {table: [] for table in BACKUP_TABLES}
    rows["pacientes"] = [
        {"id": 1, "consultorio_id": 2, "nome": "Nome atual", "deleted_at": None},
        {"id": 2, "consultorio_id": 2, "nome": "Paciente extra", "deleted_at": None},
    ]
    rows["pagamentos_consultas"] = [
        {"id": 11, "consultorio_id": 2, "valor": 50},
    ]
    document = _documento_completo(
        pacientes=[
            {"id": 1, "consultorio_id": 2, "nome": "Nome do backup", "deleted_at": None}
        ],
        pagamentos_consultas=[
            {"id": 10, "consultorio_id": 2, "valor": 100}
        ],
    )
    monkeypatch.setattr(
        "services.backup_service.read_encrypted_backup",
        lambda _path, _password: document,
    )

    db = FakeDatabase(rows)
    stats = BackupService(db).restore_backup(
        "backup.prntbk", "senha", replace_existing=True
    )

    pacientes = {row["id"]: row for row in rows["pacientes"]}
    assert pacientes[1]["nome"] == "Nome do backup"
    assert pacientes[1].get("deleted_at") is None
    assert pacientes[2]["deleted_at"] is not None
    assert [row["id"] for row in rows["pagamentos_consultas"]] == [10]
    assert stats == {"inserted": 2, "skipped": 0, "removed": 2}
    assert db.audit[0][0] == "backup_restore"


def test_substituir_recusa_backup_incompleto_antes_de_alterar(monkeypatch):
    rows = {table: [] for table in BACKUP_TABLES}
    rows["pacientes"] = [
        {"id": 1, "consultorio_id": 2, "nome": "Preservado", "deleted_at": None}
    ]
    incomplete = build_backup_document(2, {"pacientes": []})
    monkeypatch.setattr(
        "services.backup_service.read_encrypted_backup",
        lambda _path, _password: incomplete,
    )

    with pytest.raises(BackupIntegrityError):
        BackupService(FakeDatabase(rows)).restore_backup(
            "backup.prntbk", "senha", replace_existing=True
        )

    assert rows["pacientes"][0]["nome"] == "Preservado"
    assert rows["pacientes"][0]["deleted_at"] is None
