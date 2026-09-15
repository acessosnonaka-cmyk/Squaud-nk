"""Autenticação mínima e suficiente para uso interno.

Senha nunca em texto puro: scrypt da stdlib, com sal por usuário. Sem dependência
externa de hashing e sem credencial no repositório — o primeiro usuário vem do
ambiente e só é criado quando a tabela está vazia.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from . import config, db

# Parâmetros do scrypt. n=2**15 leva ~100 ms nesta classe de máquina: caro o
# bastante para força bruta, barato o bastante para um login interno.
_N, _R, _P, _DKLEN = 2 ** 15, 8, 1, 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN,
                        maxmem=64 * 1024 * 1024)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_hex, want_hex = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                            n=int(n), r=int(r), p=int(p), dklen=len(want_hex) // 2,
                            maxmem=64 * 1024 * 1024)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), want_hex)


def create_user(email: str, password: str) -> int:
    email = email.strip().lower()
    if not email or len(password) < 8:
        raise ValueError("E-mail obrigatório e senha de no mínimo 8 caracteres.")
    with db.cursor() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?,?,?)",
            (email, hash_password(password), db.now()),
        )
        return cur.lastrowid


def get_user_by_email(email: str):
    with db.cursor() as conn:
        return conn.execute("SELECT * FROM users WHERE email=? AND is_active=1",
                            (email.strip().lower(),)).fetchone()


def get_user(user_id: int):
    with db.cursor() as conn:
        return conn.execute("SELECT * FROM users WHERE id=? AND is_active=1",
                            (user_id,)).fetchone()


def authenticate(email: str, password: str):
    user = get_user_by_email(email)
    if user is None:
        # Gasta o mesmo tempo de um hash real para não vazar, pelo relógio,
        # se o e-mail existe.
        hash_password(secrets.token_hex(16))
        return None
    return user if verify_password(password, user["password_hash"]) else None


def count_users() -> int:
    with db.cursor() as conn:
        return conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]


def bootstrap() -> str | None:
    """Cria o primeiro usuário a partir do ambiente, se não houver nenhum.

    Nunca sobrescreve usuário existente e nunca grava credencial no repositório.
    """
    if count_users() > 0:
        return None
    email, password = config.BOOTSTRAP_EMAIL, config.BOOTSTRAP_PASSWORD
    if not email or not password:
        return None
    create_user(email, password)
    return email


def require_secret() -> str:
    """O app recusa subir sem segredo de sessão. Sem isso, o cookie é forjável."""
    secret = config.SESSION_SECRET
    if not secret or len(secret) < 32:
        raise SystemExit(
            "SQUAD_WEB_SESSION_SECRET ausente ou curto demais (mínimo 32 caracteres).\n"
            "Gere um com:  python3 -c \"import secrets;print(secrets.token_urlsafe(48))\"\n"
            "e coloque no .env. Nunca comite esse valor."
        )
    return secret
