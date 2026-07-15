-- Pagamentos vinculados a consultas da Agenda.
CREATE TABLE IF NOT EXISTS public.pagamentos_consultas (
    id BIGSERIAL PRIMARY KEY,
    consultorio_id BIGINT NOT NULL,
    agenda_data TEXT NOT NULL,
    agenda_horario TEXT NOT NULL,
    paciente TEXT NOT NULL,
    procedimento TEXT,
    valor NUMERIC(12,2) NOT NULL DEFAULT 0,
    valor_recebido NUMERIC(12,2) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Pendente',
    forma_pagamento TEXT,
    observacao TEXT,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (consultorio_id, agenda_data, agenda_horario)
);

ALTER TABLE public.pagamentos_consultas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pagamentos_consultas_select ON public.pagamentos_consultas;
CREATE POLICY pagamentos_consultas_select ON public.pagamentos_consultas FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));

DROP POLICY IF EXISTS pagamentos_consultas_insert ON public.pagamentos_consultas;
CREATE POLICY pagamentos_consultas_insert ON public.pagamentos_consultas FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS pagamentos_consultas_update ON public.pagamentos_consultas;
CREATE POLICY pagamentos_consultas_update ON public.pagamentos_consultas FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
