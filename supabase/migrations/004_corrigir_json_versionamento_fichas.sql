-- Compatibilidade com fichas antigas onde dados_respostas e anexos
-- foram criados como TEXT, enquanto o histórico de versões usa JSONB.
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
            OLD.id,
            OLD.consultorio_id::BIGINT,
            v_proxima,
            CASE
                WHEN OLD.dados_respostas IS NULL OR btrim(OLD.dados_respostas) = '' THEN '{}'::JSONB
                ELSE OLD.dados_respostas::JSONB
            END,
            CASE
                WHEN OLD.anexos IS NULL OR btrim(OLD.anexos) = '' THEN '[]'::JSONB
                ELSE OLD.anexos::JSONB
            END,
            auth.uid()
        );
    END IF;
    RETURN NEW;
END;
NAO$$;
