"""Persistência: SQLite em modo WAL.

Um host, um desenvolvedor, dezenas de jobs por dia. Postgres traria um container,
um backup e uma senha em troca de nada (docs/arquitetura-web.md §7).

A fila também é uma tabela: `BEGIN IMMEDIATE` serializa a reivindicação do job.
"""
from __future__ import annotations

import contextlib
import json
import secrets
import sqlite3
import time
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    tool_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    status          TEXT NOT NULL,
    params_json     TEXT NOT NULL DEFAULT '{}',
    workdir         TEXT NOT NULL,
    concurrency_key TEXT NOT NULL DEFAULT 'cpu',
    timeout_s       INTEGER NOT NULL DEFAULT 1800,
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    exit_code       INTEGER,
    error_summary   TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_jobs_status  ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user    ON jobs(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS artifacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    rel_path   TEXT NOT NULL,
    kind       TEXT NOT NULL,
    label      TEXT NOT NULL,
    bytes      INTEGER NOT NULL DEFAULT 0,
    is_primary INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id);
"""

RUNNABLE = ("queued",)
TERMINAL = ("done", "failed", "canceled")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextlib.contextmanager
def cursor():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init() -> None:
    with cursor() as conn:
        conn.executescript(SCHEMA)


def new_job_id() -> str:
    """Ordenável por tempo e único: a ordenação importa para a fila e para o histórico."""
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"


# ----------------------------------------------------------------- jobs

def create_job(*, job_id, user_id, tool_id, title, params, workdir,
               concurrency_key, timeout_s) -> None:
    with cursor() as conn:
        conn.execute(
            "INSERT INTO jobs (id, user_id, tool_id, title, status, params_json, workdir,"
            " concurrency_key, timeout_s, created_at)"
            " VALUES (?,?,?,?,'queued',?,?,?,?,?)",
            (job_id, user_id, tool_id, title, json.dumps(params, ensure_ascii=False),
             str(workdir), concurrency_key, timeout_s, now()),
        )


def get_job(job_id: str):
    with cursor() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def list_jobs(user_id: int, limit: int = 100):
    with cursor() as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def claim_next_job():
    """Reivindica um job respeitando os tetos de concorrência.

    `BEGIN IMMEDIATE` pega o lock de escrita antes de ler, então dois workers nunca
    reivindicam o mesmo job nem estouram o teto por corrida.
    """
    with cursor() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            running = conn.execute(
                "SELECT concurrency_key, COUNT(*) c FROM jobs WHERE status='running'"
                " GROUP BY concurrency_key"
            ).fetchall()
            total = sum(r["c"] for r in running)
            if total >= config.GLOBAL_SLOTS:
                conn.execute("COMMIT")
                return None
            por_chave = {r["concurrency_key"]: r["c"] for r in running}

            for row in conn.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 20"
            ).fetchall():
                key = row["concurrency_key"]
                if por_chave.get(key, 0) >= config.slots_for(key):
                    continue
                conn.execute(
                    "UPDATE jobs SET status='running', started_at=?, attempts=attempts+1"
                    " WHERE id=? AND status='queued'",
                    (now(), row["id"]),
                )
                conn.execute("COMMIT")
                return dict(row)
            conn.execute("COMMIT")
            return None
        except Exception:
            conn.execute("ROLLBACK")
            raise


def finish_job(job_id: str, *, status: str, exit_code=None, error_summary=None) -> None:
    with cursor() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, finished_at=?, exit_code=?, error_summary=? WHERE id=?",
            (status, now(), exit_code, (error_summary or "")[:500] or None, job_id),
        )


def requeue_orphans() -> int:
    """Jobs que ficaram 'running' quando o worker morreu viram 'failed'.

    Sem isso, um restart deixa job fantasma ocupando slot de concorrência para sempre.
    """
    with cursor() as conn:
        cur = conn.execute(
            "UPDATE jobs SET status='failed', finished_at=?,"
            " error_summary='Interrompido: o worker foi reiniciado durante a execução.'"
            " WHERE status='running'",
            (now(),),
        )
        return cur.rowcount


# ----------------------------------------------------------------- artifacts

def add_artifact(job_id, rel_path, kind, label, size, is_primary=False) -> None:
    with cursor() as conn:
        conn.execute(
            "INSERT INTO artifacts (job_id, rel_path, kind, label, bytes, is_primary)"
            " VALUES (?,?,?,?,?,?)",
            (job_id, rel_path, kind, label, size, 1 if is_primary else 0),
        )


def list_artifacts(job_id: str):
    with cursor() as conn:
        return conn.execute(
            "SELECT * FROM artifacts WHERE job_id=? ORDER BY is_primary DESC, id",
            (job_id,),
        ).fetchall()


def get_artifact(artifact_id: int):
    with cursor() as conn:
        return conn.execute(
            "SELECT a.*, j.user_id, j.workdir FROM artifacts a"
            " JOIN jobs j ON j.id = a.job_id WHERE a.id=?",
            (artifact_id,),
        ).fetchone()
