-- Agrega marcas de auditoria administradas por PostgreSQL.
-- Ejecutar una vez sobre la base de datos del proyecto.
CREATE OR REPLACE FUNCTION mantener_fechas_auditoria()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.creado := statement_timestamp();
        NEW.actualizado := NEW.creado;
    ELSE
        NEW.creado := OLD.creado;
        NEW.actualizado := statement_timestamp();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tabla TEXT;
    tablas TEXT[] := ARRAY[
        'actividad_docente',
        'actividad',
        'acudiente',
        'asistencia',
        'autorizacion',
        'categoria_actividad',
        'estudiante',
        'inscripcion',
        'modulo',
        'modulo_rol',
        'notificacion',
        'rol',
        'usuario'
    ];
BEGIN
    FOREACH tabla IN ARRAY tablas LOOP
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS creado TIMESTAMPTZ', tabla);
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS actualizado TIMESTAMPTZ', tabla);
        EXECUTE format(
            'UPDATE %I SET creado = COALESCE(creado, statement_timestamp()), actualizado = COALESCE(actualizado, creado, statement_timestamp())',
            tabla
        );
        EXECUTE format('ALTER TABLE %I ALTER COLUMN creado SET DEFAULT statement_timestamp()', tabla);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN actualizado SET DEFAULT statement_timestamp()', tabla);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN creado SET NOT NULL', tabla);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN actualizado SET NOT NULL', tabla);
        EXECUTE format('DROP TRIGGER IF EXISTS trigger_fechas_auditoria ON %I', tabla);
        EXECUTE format(
            'CREATE TRIGGER trigger_fechas_auditoria BEFORE INSERT OR UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION mantener_fechas_auditoria()',
            tabla
        );
    END LOOP;
END;
$$;
