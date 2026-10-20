-- Relación familiar permanente entre acudientes y estudiantes.
-- Conserva como vínculos los acudientes que ya aparecen en autorizaciones.
CREATE TABLE IF NOT EXISTS acudiente_estudiante (
    acudiente_id INTEGER NOT NULL REFERENCES acudiente(id) ON DELETE CASCADE,
    estudiante_id INTEGER NOT NULL REFERENCES estudiante(id) ON DELETE CASCADE,
    parentesco VARCHAR(50),
    PRIMARY KEY (acudiente_id, estudiante_id)
);

CREATE INDEX IF NOT EXISTS idx_acudiente_estudiante_estudiante
    ON acudiente_estudiante (estudiante_id, acudiente_id);

INSERT INTO acudiente_estudiante (acudiente_id, estudiante_id, parentesco)
SELECT DISTINCT au.acudiente_id, i.estudiante_id, ac.parentesco
FROM autorizacion au
JOIN inscripcion i ON i.id = au.inscripcion_id
JOIN acudiente ac ON ac.id = au.acudiente_id
ON CONFLICT (acudiente_id, estudiante_id) DO NOTHING;
