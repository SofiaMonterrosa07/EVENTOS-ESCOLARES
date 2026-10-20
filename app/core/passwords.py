"""Centralized password hashing and verification for user credentials."""

from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a new Argon2 hash; never accept missing or non-text credentials."""
    if not isinstance(password, str):
        raise TypeError("La contraseña debe ser texto.")
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")
    return password_hasher.hash(password)


def verificar_password(password: str, almacenada: str | None) -> tuple[bool, str | None]:
    """Verify a supported hash and return an upgraded hash when required.

    Only hash formats provided by ``PasswordHash.recommended()`` are accepted.
    In particular, unknown values are never compared as if they were plaintext.
    A replacement hash is returned only after successful verification and only
    when ``pwdlib`` recommends an upgrade.
    """
    if not isinstance(password, str) or not password:
        return False, None
    if not isinstance(almacenada, str) or not almacenada:
        return False, None

    try:
        valido, hash_actualizado = password_hasher.verify_and_update(password, almacenada)
    except Exception:
        # Malformed and unknown hashes must fail as ordinary invalid credentials.
        return False, None
    return bool(valido), hash_actualizado if valido else None
