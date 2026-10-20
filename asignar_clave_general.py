"""Asigna una contraseña nueva común a todas las cuentas existentes."""

from getpass import getpass
import sys

from dotenv import load_dotenv

from app.core.database import Database
from app.core.passwords import hash_password


def main() -> int:
    load_dotenv()
    nueva = getpass("Nueva contraseña general (8 a 128 caracteres): ")
    confirmar = getpass("Confirma la contraseña: ")
    if nueva != confirmar:
        print("Las contraseñas no coinciden. No se cambió nada.", file=sys.stderr)
        return 1
    if not 8 <= len(nueva) <= 128:
        print("La contraseña debe tener entre 8 y 128 caracteres.", file=sys.stderr)
        return 1

    conn = Database().get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM usuario ORDER BY id FOR UPDATE;")
            usuarios = cursor.fetchall()
            if not usuarios:
                conn.rollback()
                print("No hay cuentas; no se cambió nada.", file=sys.stderr)
                return 1

            print(f"Se actualizarán {len(usuarios)} cuentas existentes.")
            confirmacion = input("Escribe RESTABLECER TODAS para continuar: ").strip()
            if confirmacion != "RESTABLECER TODAS":
                conn.rollback()
                print("Cancelado. No se cambió nada.")
                return 1

            for usuario in usuarios:
                if isinstance(usuario, dict):
                    usuario_id = usuario.get("id")
                else:
                    usuario_id = usuario[0]

                if usuario_id is None:
                    raise ValueError("No se pudo determinar el id del usuario.")

                cursor.execute(
                    "UPDATE usuario SET password = %s WHERE id = %s;",
                    (hash_password(nueva), usuario_id),
                )

        conn.commit()
        print(
            f"Contraseña actualizada para {len(usuarios)} cuentas. "
            "Usa cada correo y selecciona el perfil correspondiente."
        )
        return 0
    except Exception as error:
        conn.rollback()
        print(f"No se pudieron actualizar las cuentas: {error}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
