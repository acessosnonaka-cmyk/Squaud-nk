"""Configuração do Squad NK Web. Tudo vem do ambiente; nada é hardcoded.

Regra 3 do CLAUDE.md: caminho absoluto de máquina é bug. Toda raiz é derivada
de variável de ambiente ou da posição deste arquivo.
"""
from __future__ import annotations

import os
import pathlib

# Raiz do repositório: apps/web/squadnk/config.py -> sobe 3 níveis.
REPO_ROOT = pathlib.Path(os.environ.get("SQUAD_REPO_ROOT") or
                         pathlib.Path(__file__).resolve().parents[3])

# Raiz dos dados de produção. FORA do git, sempre.
DATA_HOME = pathlib.Path(os.environ.get("SQUAD_DATA_HOME") or
                         (pathlib.Path.home() / ".squad-nk")).expanduser()

JOBS_DIR = DATA_HOME / "jobs"
DB_PATH = DATA_HOME / "db.sqlite"

APP_DIR = pathlib.Path(__file__).resolve().parent
TOOLS_DIR = APP_DIR.parent / "tools"
AGENTS_FILE = APP_DIR.parent / "agents.yaml"

# Sessão. Sem valor padrão em produção: o app recusa subir sem isso definido.
SESSION_SECRET = os.environ.get("SQUAD_WEB_SESSION_SECRET", "")
SESSION_MAX_AGE = int(os.environ.get("SQUAD_SESSION_MAX_AGE", 60 * 60 * 12))
COOKIE_SECURE = os.environ.get("SQUAD_COOKIE_SECURE", "0") == "1"

# Bootstrap do primeiro usuário. Só é usado quando a tabela está vazia.
BOOTSTRAP_EMAIL = os.environ.get("SQUAD_ADMIN_EMAIL", "")
BOOTSTRAP_PASSWORD = os.environ.get("SQUAD_ADMIN_PASSWORD", "")

MAX_UPLOAD_MB = int(os.environ.get("SQUAD_MAX_UPLOAD_MB", 500))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Tetos de concorrência. O host tem RAM limitada: dois jobs pesados em paralelo
# derrubam a máquina antes de qualquer outra coisa (docs/arquitetura-web.md §7).
GLOBAL_SLOTS = int(os.environ.get("SQUAD_GLOBAL_SLOTS", 2))
KEY_SLOTS = {
    "whisper": int(os.environ.get("SQUAD_SLOTS_WHISPER", 1)),
    "ffmpeg": int(os.environ.get("SQUAD_SLOTS_FFMPEG", 1)),
    "chromium": int(os.environ.get("SQUAD_SLOTS_CHROMIUM", 1)),
}
DEFAULT_KEY_SLOTS = 1

WORKER_POLL_S = float(os.environ.get("SQUAD_WORKER_POLL_S", 1.0))


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def slots_for(key: str) -> int:
    return KEY_SLOTS.get(key, DEFAULT_KEY_SLOTS)
