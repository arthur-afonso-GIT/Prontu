from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "supabase" / "migrations" / "028_proteger_horarios_agenda.sql"
)


def test_migracao_da_agenda_arquiva_antes_de_remover_duplicatas():
    sql = MIGRATION.read_text(encoding="utf-8")

    archive = sql.index("INSERT INTO public.agenda_duplicatas_resolvidas")
    delete = sql.index("DELETE FROM public.agenda")

    assert archive < delete
    assert "TO_JSONB(agenda)" in sql
    assert "agenda_id_preservado" in sql


def test_migracao_da_agenda_aplica_indice_unico_definitivo():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "agenda_horario_unico_por_consultorio"
    ) in sql
    assert "ON public.agenda (consultorio_id, data, horario)" in sql
