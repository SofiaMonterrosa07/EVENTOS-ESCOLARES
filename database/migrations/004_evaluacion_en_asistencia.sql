-- Mueve la evaluación de cada inscripción al registro de asistencia.
ALTER TABLE asistencia
    ADD COLUMN IF NOT EXISTS nota NUMERIC(3, 2),
    ADD COLUMN IF NOT EXISTS retroalimentacion TEXT;

-- La migración puede crear un registro de evaluación sin afirmar una asistencia
-- que nunca se registró; NULL representa que la asistencia aún es desconocida.
ALTER TABLE asistencia
    ALTER COLUMN asistio DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_asistencia_nota_rango'
          AND conrelid = 'asistencia'::regclass
    ) THEN
        ALTER TABLE asistencia
            ADD CONSTRAINT chk_asistencia_nota_rango
            CHECK (nota IS NULL OR (nota >= 0 AND nota <= 5));
    END IF;
END;
$$;

-- Conserva las evaluaciones existentes en la primera asistencia de cada
-- inscripción. Si aún no existía una asistencia, crea una con asistencia NULL.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'inscripcion'
          AND column_name = 'nota'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'inscripcion'
          AND column_name = 'retroalimentacion'
    ) THEN
        WITH primera_asistencia AS (
            SELECT DISTINCT ON (inscripcion_id) id, inscripcion_id
            FROM asistencia
            ORDER BY inscripcion_id, id
        )
        UPDATE asistencia a
        SET nota = COALESCE(a.nota, i.nota),
            retroalimentacion = COALESCE(a.retroalimentacion, i.retroalimentacion)
        FROM inscripcion i
        JOIN primera_asistencia p ON p.inscripcion_id = i.id
        WHERE a.id = p.id
          AND (i.nota IS NOT NULL OR i.retroalimentacion IS NOT NULL);

        INSERT INTO asistencia
            (inscripcion_id, asistio, observacion, nota, retroalimentacion, estado)
        SELECT i.id, NULL, NULL, i.nota, i.retroalimentacion, COALESCE(i.estado, TRUE)
        FROM inscripcion i
        WHERE (i.nota IS NOT NULL OR i.retroalimentacion IS NOT NULL)
          AND NOT EXISTS (
              SELECT 1 FROM asistencia a WHERE a.inscripcion_id = i.id
          );

        ALTER TABLE inscripcion
            DROP COLUMN IF EXISTS nota,
            DROP COLUMN IF EXISTS retroalimentacion;
    END IF;
END;
$$;
