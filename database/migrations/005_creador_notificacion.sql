-- Registra quién creó cada notificación para que también pueda verla.
ALTER TABLE notificacion
    ADD COLUMN IF NOT EXISTS creador_usuario_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_notificacion_creador_usuario'
          AND conrelid = 'notificacion'::regclass
    ) THEN
        ALTER TABLE notificacion
            ADD CONSTRAINT fk_notificacion_creador_usuario
            FOREIGN KEY (creador_usuario_id)
            REFERENCES usuario(id)
            ON DELETE SET NULL;
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_notificacion_creador_usuario_id
    ON notificacion (creador_usuario_id);
