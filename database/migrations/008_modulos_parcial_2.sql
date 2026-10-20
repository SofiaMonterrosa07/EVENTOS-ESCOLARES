-- Retira del portal pantallas auxiliares o duplicadas que no forman parte
-- del flujo solicitado para el Parcial 2. Conserva sus registros históricos.

UPDATE modulo_rol mr
SET estado = FALSE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(m.nombre)) IN (
      'administracion', 'auditoria', 'calendario', 'configuracion',
      'cupos', 'eventos', 'notificaciones', 'seguridad'
  )
  AND mr.estado IS TRUE;

UPDATE modulo m
SET estado = FALSE,
    actualizado = statement_timestamp()
WHERE LOWER(TRIM(m.nombre)) IN (
    'administracion', 'auditoria', 'calendario', 'configuracion',
    'cupos', 'eventos', 'notificaciones', 'seguridad'
)
AND m.estado IS TRUE;

-- Bienestar y Orientacion conservan tres paginas con la vista agregada.
UPDATE modulo_rol mr
SET estado = TRUE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) IN ('bienestar', 'orientador')
  AND LOWER(TRIM(m.nombre)) = 'analitica'
  AND r.estado IS TRUE
  AND m.estado IS TRUE;

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE LOWER(TRIM(r.nombre)) IN ('bienestar', 'orientador')
  AND LOWER(TRIM(m.nombre)) = 'analitica'
  AND r.estado IS TRUE
  AND m.estado IS TRUE
  AND NOT EXISTS (
      SELECT 1 FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );
