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

# --- LP Builder ---------------------------------------------------------
# O publish.py testa por HTTP se o preview subiu e encerra com erro se não
# responder 200. Em vez de expor o servidor embutido do motor — que escuta em
# 0.0.0.0 e LISTA todos os clientes na raiz — apontamos esse teste para uma rota
# interna da própria aplicação, que só devolve 200 ou 404 e nenhum conteúdo.
WEB_PORT = os.environ.get("SQUAD_WEB_PORT", "8000")
INTERNAL_BASE_URL = os.environ.get("SQUAD_INTERNAL_BASE_URL",
                                   f"http://127.0.0.1:{WEB_PORT}")


def preview_check_token() -> str:
    """Segredo da rota de verificação. Gerado uma vez e guardado fora do git."""
    do_ambiente = os.environ.get("SQUAD_PREVIEW_CHECK_TOKEN", "").strip()
    if do_ambiente:
        return do_ambiente
    caminho = DATA_HOME / ".preview-check-token"
    if caminho.is_file():
        return caminho.read_text(encoding="utf-8").strip()
    import secrets
    token = secrets.token_urlsafe(32)
    DATA_HOME.mkdir(parents=True, exist_ok=True)
    caminho.write_text(token, encoding="utf-8")
    caminho.chmod(0o600)
    return token


def internal_check_base() -> str:
    return f"{INTERNAL_BASE_URL.rstrip('/')}/_preview-check/{preview_check_token()}"


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def slots_for(key: str) -> int:
    return KEY_SLOTS.get(key, DEFAULT_KEY_SLOTS)
