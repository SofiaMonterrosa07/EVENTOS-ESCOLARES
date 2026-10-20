-- Ajusta permisos concretos que faltaban en la matriz de roles.
-- Los estudiantes necesitan consultar asistencia, notas y retroalimentación.
-- Secretaría administra estudiantes y acudientes, pero no configura roles.

UPDATE modulo_rol mr
SET estado = TRUE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'estudiante'
  AND LOWER(TRIM(m.nombre)) = 'asistencia';

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE LOWER(TRIM(r.nombre)) = 'estudiante'
  AND LOWER(TRIM(m.nombre)) = 'asistencia'
  AND r.estado IS TRUE
  AND m.estado IS TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );

-- Entrenadores supervisan sus actividades y califican asistencia igual que docentes.
UPDATE modulo_rol mr
SET estado = TRUE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'entrenador'
  AND LOWER(TRIM(m.nombre)) = 'asistencia';

INSERT INTO modulo_rol (rol_id, modulo_id, estado)
SELECT r.id, m.id, TRUE
FROM rol r
CROSS JOIN modulo m
WHERE LOWER(TRIM(r.nombre)) = 'entrenador'
  AND LOWER(TRIM(m.nombre)) = 'asistencia'
  AND r.estado IS TRUE
  AND m.estado IS TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM modulo_rol mr
      WHERE mr.rol_id = r.id AND mr.modulo_id = m.id
  );

UPDATE modulo_rol mr
SET estado = FALSE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'secretaria'
  AND LOWER(TRIM(m.nombre)) = 'roles'
  AND mr.estado IS TRUE;

-- Bienestar y orientación trabajan con indicadores agregados, no con la tabla nominal.
UPDATE modulo_rol mr
SET estado = FALSE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) IN ('bienestar', 'orientador')
  AND LOWER(TRIM(m.nombre)) = 'inscripciones'
  AND mr.estado IS TRUE;

-- Retira del selector los perfiles sin cuentas activas y sin módulos asignados.
-- Las filas se conservan para poder reactivar esos roles en el futuro.
UPDATE rol r
SET estado = FALSE,
    actualizado = statement_timestamp()
WHERE r.estado IS TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM usuario u
      WHERE u.rol_id = r.id AND u.estado IS TRUE
  )
  AND NOT EXISTS (
      SELECT 1
      FROM modulo_rol mr
      JOIN modulo m ON m.id = mr.modulo_id
      WHERE mr.rol_id = r.id
        AND mr.estado IS TRUE
        AND m.estado IS TRUE
  );
