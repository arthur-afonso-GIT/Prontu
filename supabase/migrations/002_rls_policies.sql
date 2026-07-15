-- Migração 002: Row Level Security multi-tenant

-- Habilitar RLS
ALTER TABLE public.pacientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agenda ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pastas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.modelos_fichas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fichas_preenchidas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.configuracoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chaves_acesso ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios_consultorios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dispositivos_consultorio ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fichas_preenchidas_versoes ENABLE ROW LEVEL SECURITY;

-- chaves_acesso: nenhum acesso direto por clientes
DROP POLICY IF EXISTS chaves_acesso_deny_all ON public.chaves_acesso;
CREATE POLICY chaves_acesso_deny_all ON public.chaves_acesso
    FOR ALL TO authenticated, anon
    USING (false) WITH CHECK (false);

-- Macro helper via políticas por tabela
-- PACIENTES
DROP POLICY IF EXISTS pacientes_select ON public.pacientes;
CREATE POLICY pacientes_select ON public.pacientes FOR SELECT TO authenticated
    USING (
        consultorio_id IN (SELECT public.get_auth_consultorio_ids())
        AND deleted_at IS NULL
    );

DROP POLICY IF EXISTS pacientes_insert ON public.pacientes;
CREATE POLICY pacientes_insert ON public.pacientes FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS pacientes_update ON public.pacientes;
CREATE POLICY pacientes_update ON public.pacientes FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS pacientes_delete ON public.pacientes;
CREATE POLICY pacientes_delete ON public.pacientes FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));

-- AGENDA
DROP POLICY IF EXISTS agenda_select ON public.agenda;
CREATE POLICY agenda_select ON public.agenda FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));

DROP POLICY IF EXISTS agenda_insert ON public.agenda;
CREATE POLICY agenda_insert ON public.agenda FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS agenda_update ON public.agenda;
CREATE POLICY agenda_update ON public.agenda FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));

DROP POLICY IF EXISTS agenda_delete ON public.agenda;
CREATE POLICY agenda_delete ON public.agenda FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));

-- PASTAS
DROP POLICY IF EXISTS pastas_all ON public.pastas;
DROP POLICY IF EXISTS pastas_select ON public.pastas;
DROP POLICY IF EXISTS pastas_insert ON public.pastas;
DROP POLICY IF EXISTS pastas_update ON public.pastas;
DROP POLICY IF EXISTS pastas_delete ON public.pastas;
CREATE POLICY pastas_select ON public.pastas FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));
CREATE POLICY pastas_insert ON public.pastas FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
CREATE POLICY pastas_update ON public.pastas FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
CREATE POLICY pastas_delete ON public.pastas FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));

-- MODELOS_FICHAS
DROP POLICY IF EXISTS modelos_fichas_select ON public.modelos_fichas;
CREATE POLICY modelos_fichas_select ON public.modelos_fichas FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));
DROP POLICY IF EXISTS modelos_fichas_insert ON public.modelos_fichas;
CREATE POLICY modelos_fichas_insert ON public.modelos_fichas FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
DROP POLICY IF EXISTS modelos_fichas_update ON public.modelos_fichas;
CREATE POLICY modelos_fichas_update ON public.modelos_fichas FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
DROP POLICY IF EXISTS modelos_fichas_delete ON public.modelos_fichas;
CREATE POLICY modelos_fichas_delete ON public.modelos_fichas FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));

-- FICHAS_PREENCHIDAS
DROP POLICY IF EXISTS fichas_preenchidas_select ON public.fichas_preenchidas;
CREATE POLICY fichas_preenchidas_select ON public.fichas_preenchidas FOR SELECT TO authenticated
    USING (
        consultorio_id IN (SELECT public.get_auth_consultorio_ids())
        AND deleted_at IS NULL
    );
DROP POLICY IF EXISTS fichas_preenchidas_insert ON public.fichas_preenchidas;
CREATE POLICY fichas_preenchidas_insert ON public.fichas_preenchidas FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
DROP POLICY IF EXISTS fichas_preenchidas_update ON public.fichas_preenchidas;
CREATE POLICY fichas_preenchidas_update ON public.fichas_preenchidas FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
DROP POLICY IF EXISTS fichas_preenchidas_delete ON public.fichas_preenchidas;
CREATE POLICY fichas_preenchidas_delete ON public.fichas_preenchidas FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));

-- CONFIGURACOES
DROP POLICY IF EXISTS configuracoes_select ON public.configuracoes;
CREATE POLICY configuracoes_select ON public.configuracoes FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));
DROP POLICY IF EXISTS configuracoes_insert ON public.configuracoes;
CREATE POLICY configuracoes_insert ON public.configuracoes FOR INSERT TO authenticated
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
DROP POLICY IF EXISTS configuracoes_update ON public.configuracoes;
CREATE POLICY configuracoes_update ON public.configuracoes FOR UPDATE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id))
    WITH CHECK (public.consultorio_autorizado(consultorio_id));
DROP POLICY IF EXISTS configuracoes_delete ON public.configuracoes;
CREATE POLICY configuracoes_delete ON public.configuracoes FOR DELETE TO authenticated
    USING (public.consultorio_autorizado(consultorio_id));

-- AUDIT_LOGS: somente leitura do próprio consultório
DROP POLICY IF EXISTS audit_logs_select ON public.audit_logs;
CREATE POLICY audit_logs_select ON public.audit_logs FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));

-- No direct INSERT policy: only registrar_audit_log() and SECURITY DEFINER
-- triggers may append audit records. This prevents forged client audit events.
DROP POLICY IF EXISTS audit_logs_insert ON public.audit_logs;

-- Versões de fichas
DROP POLICY IF EXISTS fichas_versoes_select ON public.fichas_preenchidas_versoes;
CREATE POLICY fichas_versoes_select ON public.fichas_preenchidas_versoes FOR SELECT TO authenticated
    USING (consultorio_id IN (SELECT public.get_auth_consultorio_ids()));

-- usuarios_consultorios / dispositivos: leitura própria
DROP POLICY IF EXISTS usuarios_consultorios_select ON public.usuarios_consultorios;
CREATE POLICY usuarios_consultorios_select ON public.usuarios_consultorios FOR SELECT TO authenticated
    USING (auth_user_id = auth.uid());

DROP POLICY IF EXISTS dispositivos_select ON public.dispositivos_consultorio;
CREATE POLICY dispositivos_select ON public.dispositivos_consultorio FOR SELECT TO authenticated
    USING (auth_user_id = auth.uid());

-- Storage: políticas para bucket fichas-anexos (primeira pasta = consultorio_id)
-- Executar no SQL Editor do Supabase Storage ou via migration storage schema
-- Nota: storage.objects RLS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'objects') THEN
        ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS fichas_anexos_select ON storage.objects;
        CREATE POLICY fichas_anexos_select ON storage.objects FOR SELECT TO authenticated
            USING (
                bucket_id = 'fichas-anexos'
                AND (storage.foldername(name))[1]::bigint IN (SELECT public.get_auth_consultorio_ids())
            );

        DROP POLICY IF EXISTS fichas_anexos_insert ON storage.objects;
        CREATE POLICY fichas_anexos_insert ON storage.objects FOR INSERT TO authenticated
            WITH CHECK (
                bucket_id = 'fichas-anexos'
                AND (storage.foldername(name))[1]::bigint IN (SELECT public.get_auth_consultorio_ids())
            );

        DROP POLICY IF EXISTS fichas_anexos_update ON storage.objects;
        CREATE POLICY fichas_anexos_update ON storage.objects FOR UPDATE TO authenticated
            USING (
                bucket_id = 'fichas-anexos'
                AND (storage.foldername(name))[1]::bigint IN (SELECT public.get_auth_consultorio_ids())
            );

        DROP POLICY IF EXISTS fichas_anexos_delete ON storage.objects;
        CREATE POLICY fichas_anexos_delete ON storage.objects FOR DELETE TO authenticated
            USING (
                bucket_id = 'fichas-anexos'
                AND (storage.foldername(name))[1]::bigint IN (SELECT public.get_auth_consultorio_ids())
            );
    END IF;
END $$;
