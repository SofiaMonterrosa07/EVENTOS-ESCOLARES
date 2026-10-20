-- Permite a docentes registrar una nota y observaciones en cada inscripción.
-- Las columnas son opcionales para conservar las inscripciones ya existentes.
ALTER TABLE inscripcion
    ADD COLUMN IF NOT EXISTS nota NUMERIC(3, 2),
    ADD COLUMN IF NOT EXISTS retroalimentacion TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_inscripcion_nota_rango'
          AND conrelid = 'inscripcion'::regclass
    ) THEN
        ALTER TABLE inscripcion
            ADD CONSTRAINT chk_inscripcion_nota_rango
            CHECK (nota IS NULL OR (nota >= 0 AND nota <= 5));
    END IF;
END;
$$;
