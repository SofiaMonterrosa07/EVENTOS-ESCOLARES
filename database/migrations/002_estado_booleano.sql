-- Garantiza un campo estado BOOLEAN NOT NULL en las 13 tablas.
-- Los estados textuales anteriores se convierten a true/false conservando
-- el significado conocido de cada valor; los valores desconocidos pasan a false.
-- Esta restricción antigua limita actividad.estado a etiquetas de texto y debe
-- retirarse antes de convertir la columna a BOOLEAN.
ALTER TABLE actividad DROP CONSTRAINT IF EXISTS chk_actividad_estado;

DO $$
DECLARE
    tabla TEXT;
    expresion_true TEXT;
    tipo_estado TEXT;
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
        expresion_true := CASE tabla
            WHEN 'actividad' THEN
                'LOWER(BTRIM(estado::text)) IN (''true'', ''t'', ''1'', ''activo'', ''activa'', ''próxima'', ''proxima'', ''en curso'')'
            WHEN 'autorizacion' THEN
                'LOWER(BTRIM(estado::text)) IN (''true'', ''t'', ''1'', ''autorizada'', ''confirmada'', ''confirmado'')'
            WHEN 'inscripcion' THEN
                'LOWER(BTRIM(estado::text)) IN (''true'', ''t'', ''1'', ''confirmada'', ''confirmado'', ''activo'', ''activa'')'
            ELSE
                'LOWER(BTRIM(estado::text)) IN (''true'', ''t'', ''1'')'
        END;

        -- Los estados nuevos se agregan como booleanos desde el inicio.
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS estado BOOLEAN', tabla);

        SELECT data_type
        INTO tipo_estado
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = tabla
          AND column_name = 'estado';

        IF tipo_estado IS DISTINCT FROM 'boolean' THEN
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN estado DROP DEFAULT',
                tabla
            );
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN estado TYPE BOOLEAN USING CASE WHEN %s THEN TRUE ELSE FALSE END',
                tabla,
                expresion_true
            );
        END IF;

        EXECUTE format(
            'UPDATE %I SET estado = COALESCE(estado, %L::boolean)',
            tabla,
            CASE WHEN tabla IN ('autorizacion', 'inscripcion') THEN 'false' ELSE 'true' END
        );
        EXECUTE format(
            'ALTER TABLE %I ALTER COLUMN estado SET DEFAULT %L::boolean',
            tabla,
            CASE WHEN tabla IN ('autorizacion', 'inscripcion') THEN 'false' ELSE 'true' END
        );
        EXECUTE format('ALTER TABLE %I ALTER COLUMN estado SET NOT NULL', tabla);
    END LOOP;
END;
$$;
