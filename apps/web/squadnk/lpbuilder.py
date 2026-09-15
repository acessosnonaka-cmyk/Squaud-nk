"""O que a aplicação precisa saber sobre o LP Builder — e só isso.

Os motores (`lp_qa.py`, `publish.py`) não são tocados nem reimplementados. Este
módulo faz três coisas: descobre onde os previews moram, decide se a publicação
remota está configurada, e resolve um caminho de preview com segurança.

Raiz dos previews: os motores usam `os.path.expanduser('~/.claude/lp-builder')`,
que respeita `$HOME`. O runner lança os processos do LP com
`HOME=$SQUAD_DATA_HOME/home`, então tudo cai fora do repositório sem uma linha de
mudança no motor (docs/arquitetura-web.md §7).
"""
from __future__ import annotations

import json
import pathlib
import re

from . import config

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")

# Extensões que o preview pode servir. Tudo fora desta lista é negado — um
# preview é um site estático, não um sistema de arquivos.
TIPOS = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif", ".avif": "image/avif", ".ico": "image/x-icon",
    ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
    ".otf": "font/otf", ".mp4": "video/mp4", ".webm": "video/webm",
    ".txt": "text/plain; charset=utf-8", ".webmanifest": "application/manifest+json",
    ".map": "application/json",
}


def lp_home() -> pathlib.Path:
    """O mesmo `~/.claude/lp-builder` que o motor enxerga, com o HOME que damos a ele."""
    return config.DATA_HOME / "home" / ".claude" / "lp-builder"


def previews_root() -> pathlib.Path:
    return lp_home() / "previews"


def conf_path() -> pathlib.Path:
    return lp_home() / "publish.conf.json"


def slug_valido(slug: str) -> bool:
    return bool(SLUG_RE.match(slug or ""))


def garantir_conf(base_url: str) -> None:
    """Escreve o publish.conf.json se não existir.

    `base_url` aponta para a rota interna de verificação da própria aplicação:
    o motor testa por HTTP se o preview subiu, e sem um alvo válido ele encerra
    com erro. Nunca escreve bloco `remote` — servidor não se inventa.
    """
    caminho = conf_path()
    if caminho.exists():
        return
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps({"base_url": base_url, "remote": None}, indent=2), encoding="utf-8"
    )


def ler_conf() -> dict:
    caminho = conf_path()
    if not caminho.is_file():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def publicacao_remota() -> dict:
    """Estado da publicação remota, para a interface dizer a verdade.

    Dois estados e nada de mistério: configurada ou não. Nenhum host é inventado
    e nenhuma credencial é lida daqui — só a presença do bloco `remote`.
    """
    remoto = (ler_conf().get("remote") or None)
    if not isinstance(remoto, dict) or not remoto.get("host"):
        return {
            "configurada": False,
            "resumo": "Publicação remota ainda não configurada.",
            "detalhe": (
                "Os previews ficam disponíveis aqui dentro, pela rota autenticada. "
                "Para publicar num servidor externo, preencha o bloco `remote` de "
                "publish.conf.json com host, usuário, caminho e chave SSH."
            ),
            "base_url": None,
        }
    return {
        "configurada": True,
        "resumo": "Publicação remota disponível.",
        "detalhe": f"Os previews também são enviados por rsync para {remoto['host']}.",
        "base_url": remoto.get("base_url"),
    }


def versoes(slug: str) -> dict:
    """Versões publicadas de um slug. Leitura pura, sem tocar em nada."""
    cli = previews_root() / slug
    vers = cli / "versions"
    if not slug_valido(slug) or not vers.is_dir():
        return {"existe": False, "versoes": [], "atual": None}
    todas = sorted(d.name for d in vers.iterdir()
                   if d.is_dir() and re.match(r"^\d{8}-\d{6}$", d.name))
    atual = None
    ponteiro = cli / "current"
    if ponteiro.is_symlink() or ponteiro.exists():
        try:
            atual = ponteiro.resolve().name
        except OSError:
            atual = None
    return {"existe": bool(todas), "versoes": todas, "atual": atual}


def resolver_arquivo(slug: str, relativo: str) -> pathlib.Path | None:
    """Caminho real de um arquivo do preview, ou None se não for servível.

    Cinco travas, nesta ordem: slug no formato do motor; nada de `..` nem caminho
    absoluto; o caminho real precisa estar DENTRO de `current/` já resolvido —
    o que também barra symlink apontando para fora; precisa ser arquivo comum,
    não diretório nem socket nem fifo; e a extensão precisa estar na lista.
    """
    if not slug_valido(slug):
        return None
    base = previews_root() / slug / "current"
    try:
        base_real = base.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    if not base_real.is_dir():
        return None

    relativo = (relativo or "").strip("/")
    if not relativo:
        relativo = "index.html"
    # Byte nulo e caracteres de controle fazem o pathlib levantar ValueError lá
    # na frente, o que virava erro 500. Aqui viram "não encontrado", como devem.
    if any(c in relativo for c in "\x00") or any(ord(c) < 32 for c in relativo):
        return None
    if relativo.startswith("/") or ".." in pathlib.PurePosixPath(relativo).parts:
        return None

    try:
        alvo_real = (base_real / relativo).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None

    # Containment: precisa estar sob a raiz REAL, e o próprio diretório não serve.
    if alvo_real != base_real and base_real not in alvo_real.parents:
        return None
    if alvo_real.is_dir():
        indice = alvo_real / "index.html"
        if not indice.is_file():
            return None
        alvo_real = indice
        if base_real not in alvo_real.parents:
            return None
    if not alvo_real.is_file():
        return None
    if alvo_real.suffix.lower() not in TIPOS:
        return None
    return alvo_real


def tipo_de(caminho: pathlib.Path) -> str:
    return TIPOS.get(caminho.suffix.lower(), "application/octet-stream")
