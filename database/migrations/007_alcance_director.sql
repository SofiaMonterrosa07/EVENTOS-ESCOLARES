-- La Dirección supervisa resultados agregados; los expedientes nominales
-- de asistencia, inscripciones y autorizaciones quedan para los roles operativos.
UPDATE modulo_rol mr
SET estado = FALSE,
    actualizado = statement_timestamp()
FROM rol r, modulo m
WHERE mr.rol_id = r.id
  AND mr.modulo_id = m.id
  AND LOWER(TRIM(r.nombre)) = 'director'
  AND LOWER(TRIM(m.nombre)) IN ('asistencia', 'inscripciones', 'autorizaciones')
  AND mr.estado IS TRUE;
