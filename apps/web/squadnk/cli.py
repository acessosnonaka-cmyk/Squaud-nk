"""Administração pela linha de comando. Só para inicialização e manutenção —
a operação normal do time é inteiramente pelo navegador."""
from __future__ import annotations

import argparse
import getpass
import secrets
import sys

from . import auth, config, db


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="squadnk", description="Administração do Squad NK Web")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("adduser", help="cria um usuário")
    p.add_argument("email")
    p.add_argument("--password", help="se omitido, é pedido interativamente")

    sub.add_parser("initdb", help="cria as tabelas (idempotente)")
    sub.add_parser("secret", help="gera um SQUAD_WEB_SESSION_SECRET")
    sub.add_parser("status", help="mostra caminhos e contagens")

    args = parser.parse_args(argv)

    if args.cmd == "secret":
        print(secrets.token_urlsafe(48))
        return 0

    db.init()

    if args.cmd == "initdb":
        print(f"banco pronto em {config.DB_PATH}")
    elif args.cmd == "adduser":
        senha = args.password or getpass.getpass("Senha (mín. 8): ")
        try:
            auth.create_user(args.email, senha)
        except ValueError as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        print(f"usuário criado: {args.email}")
    elif args.cmd == "status":
        with db.cursor() as conn:
            jobs = conn.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status").fetchall()
        print(f"repo   : {config.REPO_ROOT}")
        print(f"dados  : {config.DATA_HOME}")
        print(f"banco  : {config.DB_PATH}")
        print(f"usuários: {auth.count_users()}")
        print("jobs   : " + (", ".join(f"{r['status']}={r['c']}" for r in jobs) or "nenhum"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
