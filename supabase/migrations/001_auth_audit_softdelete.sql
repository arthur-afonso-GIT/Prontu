-- Migração 001: vínculo auth-consultório, soft delete, auditoria e versionamento
-- Idempotente — seguro para reexecução parcial

-- Extensões
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Vínculo entre auth.users e consultórios
CREATE TABLE IF NOT EXISTS public.usuarios_consultorios (
    id BIGSERIAL PRIMARY KEY,
    auth_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    consultorio_id BIGINT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (auth_user_id, consultorio_id)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_consultorios_auth
    ON public.usuarios_consultorios (auth_user_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_consultorios_consultorio
    ON public.usuarios_consultorios (consultorio_id);

-- Dispositivos ativados por chave
CREATE TABLE IF NOT EXISTS public.dispositivos_consultorio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultorio_id BIGINT NOT NULL,
    auth_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL,
    device_name TEXT,
    ativado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_acesso TIMESTAMPTZ,
    revogado_em TIMESTAMPTZ,
    UNIQUE (consultorio_id, device_id)
);

-- Soft delete em tabelas clínicas
ALTER TABLE public.pacientes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.pacientes ADD COLUMN IF NOT EXISTS deleted_by UUID;
ALTER TABLE public.fichas_preenchidas ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE public.fichas_preenchidas ADD COLUMN IF NOT EXISTS deleted_by UUID;

-- Versionamento de fichas preenchidas
CREATE TABLE IF NOT EXISTS public.fichas_preenchidas_versoes (
    id BIGSERIAL PRIMARY KEY,
    ficha_id BIGINT NOT NULL,
    consultorio_id BIGINT NOT NULL,
    versao INT NOT NULL,
    dados_respostas JSONB,
    anexos JSONB,
    alterado_por UUID,
    alterado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fichas_versoes_ficha
    ON public.fichas_preenchidas_versoes (ficha_id, versao DESC);

-- Auditoria imutável
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    consultorio_id BIGINT,
    auth_user_id UUID,
    acao TEXT NOT NULL,
    entidade TEXT NOT NULL,
    registro_id TEXT,
    contexto JSONB DEFAULT '{}'::jsonb,
    valor_anterior JSONB,
    valor_novo JSONB,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_consultorio
    ON public.audit_logs (consultorio_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entidade
    ON public.audit_logs (entidade, registro_id);

-- Funções auxiliares RLS
CREATE OR REPLACE FUNCTION public.get_auth_consultorio_ids()
RETURNS SETOF BIGINT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT consultorio_id
    FROM public.usuarios_consultorios
    WHERE auth_user_id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.consultorio_autorizado(p_consultorio_id BIGINT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.usuarios_consultorios
        WHERE auth_user_id = auth.uid()
          AND consultorio_id = p_consultorio_id
    );
$$;

-- RPC para auditoria de eventos de alto nível (backup/export)
CREATE OR REPLACE FUNCTION public.registrar_audit_log(
    p_acao TEXT,
    p_entidade TEXT,
    p_registro_id TEXT DEFAULT NULL,
    p_contexto JSONB DEFAULT '{}'::jsonb
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_consultorio BIGINT;
    v_id BIGINT;
BEGIN
    SELECT consultorio_id INTO v_consultorio
    FROM public.usuarios_consultorios
    WHERE auth_user_id = auth.uid()
    LIMIT 1;

    INSERT INTO public.audit_logs (
        consultorio_id, auth_user_id, acao, entidade, registro_id, contexto
    ) VALUES (
        v_consultorio, auth.uid(), p_acao, p_entidade, p_registro_id, p_contexto
    ) RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.registrar_audit_log(TEXT, TEXT, TEXT, JSONB) TO authenticated;

-- Trigger genérico de auditoria
CREATE OR REPLACE FUNCTION public.audit_trigger_fn()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_consultorio BIGINT;
    v_registro TEXT;
    v_old JSONB;
    v_new JSONB;
    v_acao TEXT;
BEGIN
    v_acao := TG_OP;
    IF TG_OP = 'DELETE' THEN
        v_registro := COALESCE(OLD.id::text, OLD.consultorio_id::text);
        v_consultorio := OLD.consultorio_id;
        v_old := to_jsonb(OLD);
        v_new := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_registro := COALESCE(NEW.id::text, NEW.consultorio_id::text);
        v_consultorio := NEW.consultorio_id;
        v_old := to_jsonb(OLD);
        v_new := to_jsonb(NEW);
    ELSE
        v_registro := COALESCE(NEW.id::text, NEW.consultorio_id::text);
        v_consultorio := NEW.consultorio_id;
        v_old := NULL;
        v_new := to_jsonb(NEW);
    END IF;

    -- Keep lower-criticality patient metadata out of the generic audit trail.
    -- Full clinical revision history is retained only for filled forms.
    IF TG_TABLE_NAME <> 'fichas_preenchidas' THEN
        v_old := v_old - ARRAY['queixa_principal', 'endereco', 'telefone', 'nascimento'];
        v_new := v_new - ARRAY['queixa_principal', 'endereco', 'telefone', 'nascimento'];
    END IF;

    INSERT INTO public.audit_logs (
        consultorio_id, auth_user_id, acao, entidade, registro_id,
        valor_anterior, valor_novo, contexto
    ) VALUES (
        v_consultorio,
        auth.uid(),
        v_acao,
        TG_TABLE_NAME,
        v_registro,
        v_old,
        v_new,
        jsonb_build_object('trigger', TG_NAME)
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

-- Versionamento antes de UPDATE em fichas_preenchidas
CREATE OR REPLACE FUNCTION public.versionar_ficha_preenchida()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_proxima INT;
BEGIN
    IF OLD.dados_respostas IS DISTINCT FROM NEW.dados_respostas
       OR OLD.anexos IS DISTINCT FROM NEW.anexos THEN
        SELECT COALESCE(MAX(versao), 0) + 1 INTO v_proxima
        FROM public.fichas_preenchidas_versoes
        WHERE ficha_id = OLD.id;

        INSERT INTO public.fichas_preenchidas_versoes (
            ficha_id, consultorio_id, versao, dados_respostas, anexos, alterado_por
        ) VALUES (
            OLD.id, OLD.consultorio_id, v_proxima,
            OLD.dados_respostas, OLD.anexos, auth.uid()
        );
    END IF;
    RETURN NEW;
END;
$$;

-- Impedir UPDATE/DELETE em audit_logs pelo cliente
CREATE OR REPLACE FUNCTION public.bloquear_mutacao_audit_logs()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs é imutável para papéis de aplicativo';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_logs_no_update ON public.audit_logs;
CREATE TRIGGER trg_audit_logs_no_update
    BEFORE UPDATE OR DELETE ON public.audit_logs
    FOR EACH ROW EXECUTE FUNCTION public.bloquear_mutacao_audit_logs();

-- Aplicar triggers de auditoria (idempotente)
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'pacientes', 'agenda', 'pastas', 'modelos_fichas',
        'fichas_preenchidas', 'configuracoes'
    ] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_audit_%I ON public.%I', t, t);
        EXECUTE format(
            'CREATE TRIGGER trg_audit_%I AFTER INSERT OR UPDATE OR DELETE ON public.%I
             FOR EACH ROW EXECUTE FUNCTION public.audit_trigger_fn()',
            t, t
        );
    END LOOP;
END $$;

DROP TRIGGER IF EXISTS trg_versionar_ficha ON public.fichas_preenchidas;
CREATE TRIGGER trg_versionar_ficha
    BEFORE UPDATE ON public.fichas_preenchidas
    FOR EACH ROW EXECUTE FUNCTION public.versionar_ficha_preenchida();

-- Impedir hard DELETE de pacientes/fichas pelo cliente autenticado (soft delete)
CREATE OR REPLACE FUNCTION public.impedir_delete_clinico()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Exclusão definitiva bloqueada — use exclusão lógica (deleted_at)';
END;
$$;

DROP TRIGGER IF EXISTS trg_no_hard_delete_pacientes ON public.pacientes;
CREATE TRIGGER trg_no_hard_delete_pacientes
    BEFORE DELETE ON public.pacientes
    FOR EACH ROW EXECUTE FUNCTION public.impedir_delete_clinico();

DROP TRIGGER IF EXISTS trg_no_hard_delete_fichas ON public.fichas_preenchidas;
CREATE TRIGGER trg_no_hard_delete_fichas
    BEFORE DELETE ON public.fichas_preenchidas
    FOR EACH ROW EXECUTE FUNCTION public.impedir_delete_clinico();
