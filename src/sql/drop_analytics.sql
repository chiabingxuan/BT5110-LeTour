-- Removes every analytics view and fn_* function so the base tables can be dropped or the layer rebuilt.
DO $$
DECLARE obj RECORD;
BEGIN
    FOR obj IN SELECT viewname FROM pg_views WHERE schemaname = 'public' LOOP
        EXECUTE format('DROP VIEW IF EXISTS %I CASCADE', obj.viewname);
    END LOOP;
    FOR obj IN
        SELECT p.oid::regprocedure AS signature
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.proname LIKE 'fn\_%'
    LOOP
        EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', obj.signature);
    END LOOP;
END $$;
