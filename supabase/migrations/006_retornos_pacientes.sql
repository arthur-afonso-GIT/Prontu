-- Retornos e acompanhamento de pacientes.
CREATE TABLE IF NOT EXISTS public.retornos_pacientes (
    id BIGSERIAL PRIMARY KEY,
    consultorio_id BIGINT NOT NULL,
    paciente_id BIGINT NOT NULL REFERENCES public.pacientes(id) ON DELETE CASCADE,
    data_prevista DATE NOT NULL,
    motivo TEXT,
    status TEXT NOT NULL DEFAULT 'Pendente'
        CHECK (status IN ('Pendente', 'Agendado', 'Concluído', 'Não retornou', 'Cancelado')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_retornos_consultorio_status_data
    ON public.retornos_pacientes (consultorio_id, status, data_prevista);
CREATE INDEX IF NOT EXISTS idx_retornos_paciente
    ON public.retornos_pacientes (paciente_id, data_prevista DESC);

ALTER TABLE public.retornos_pacientes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS retornos_pacientes_select ON public.retornos_pacientes;
CREATE POLICY retornos_pacientes_select ON public.retornos_pacientes FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));

DROP POLICY IF EXISTS retornos_pacientes_insert ON public.retornos_pacientes;
CREATE POLICY retornos_pacientes_insert ON public.retornos_pacientes FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS retornos_pacientes_update ON public.retornos_pacientes;
CREATE POLICY retornos_pacientes_update ON public.retornos_pacientes FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS retornos_pacientes_delete ON public.retornos_pacientes;
CREATE POLICY retornos_pacientes_delete ON public.retornos_pacientes FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));
