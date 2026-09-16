#!/usr/bin/env python3
"""Playwright e Chromium portáteis para os motores do Squad NK.

Dois problemas de PORTABILIDADE, e nada além disso. Nenhuma decisão de produto
vive aqui: é infraestrutura, compartilhada para não duplicar lógica entre o
motor do Design IA e o do LP Builder.

1. INTERPRETADOR — o render do Design IA é chamado como `python3 render.py`, e
   o `python3` do sistema não tem Playwright. Quem tem é o venv de
   `apps/lp-builder/venv`, que atende os dois motores. `garantir_playwright()`
   re-executa o script nesse interpretador quando o atual não consegue
   importar o Playwright. **Um venv só, compartilhado — nada é duplicado.**

2. NAVEGADOR — o Chromium que o Playwright gerencia nem sempre é o que existe
   na máquina. Um container do Claude Code Web já traz um Chromium pronto em
   `PLAYWRIGHT_BROWSERS_PATH`, cuja build não bate com o pin do Playwright:
   o launch padrão falha procurando uma build que ninguém baixou.
   `lancar_chromium()` tenta, em ordem declarada, o primeiro que subir.

Ordem de busca do navegador, do mais explícito ao mais genérico:

    1. PLAYWRIGHT_CHROMIUM_PATH        — override manual, sempre vence
    2. Chromium da plataforma          — dentro de PLAYWRIGHT_BROWSERS_PATH
    3. Chromium gerenciado pelo Playwright  — o comportamento padrão de sempre
    4. Chromium do sistema             — /usr/bin/chromium e equivalentes
    5. erro claro, listando o que foi tentado

Nenhum caminho é obrigatório e nenhum é hardcoded como única possibilidade.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

VENV_ENV = "SQUAD_PLAYWRIGHT_PYTHON"
CHROMIUM_ENV = "PLAYWRIGHT_CHROMIUM_PATH"
_REEXEC_FLAG = "SQUADNK_PLAYWRIGHT_REEXEC"

# Chromium instalado pelo gerenciador de pacotes, em ordem de preferência.
CHROMIUM_DO_SISTEMA = (
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium",
)


class BrowserIndisponivel(RuntimeError):
    """Nenhum Chromium utilizável, ou nenhum Python com Playwright."""


def _raiz_do_clone() -> pathlib.Path:
    # .../shared/pylib/squadnk_browser.py -> sobe 2 níveis = raiz do clone
    return pathlib.Path(__file__).resolve().parents[2]


# --------------------------------------------------------------- interpretador

def _pythons_candidatos() -> list[pathlib.Path]:
    """Interpretadores que podem ter Playwright, do mais explícito ao padrão."""
    out: list[pathlib.Path] = []
    explicito = os.environ.get(VENV_ENV)
    if explicito:
        out.append(pathlib.Path(explicito).expanduser())
    # O clone (resolvido a partir deste arquivo) e a âncora ~/.claude/squad-nk
    # apontam para o mesmo lugar quando o setup rodou; manter os dois cobre
    # quem executa o motor pelo symlink em ~/.claude/art-builder.
    for base in (_raiz_do_clone(), pathlib.Path.home() / ".claude" / "squad-nk"):
        out.append(base / "apps" / "lp-builder" / "venv" / "bin" / "python")
    vistos: set[str] = set()
    unicos: list[pathlib.Path] = []
    for p in out:
        chave = str(p)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(p)
    return unicos


def _garantir(modulos: tuple[str, ...]) -> None:
    """Garante que este processo importa `modulos`; se não, troca de interpretador.

    Só troca uma vez — o laço é impedido por uma variável de ambiente, não por
    comparar caminhos. Comparar `resolve()` seria errado: o `bin/python` de um
    venv é symlink para o interpretador base, e o venv seria descartado como se
    fosse o mesmo Python.
    """
    faltando = []
    for m in modulos:
        try:
            __import__(m)
        except ImportError:
            faltando.append(m)
    if not faltando:
        return

    rotulo = ", ".join(faltando)
    if os.environ.get(_REEXEC_FLAG) == "1":
        raise BrowserIndisponivel(
            f"{rotulo} continua indisponível depois de trocar de interpretador. "
            "Rode: bash scripts/setup.sh"
        )

    teste_import = "import " + ", ".join(modulos)
    tentados: list[str] = []
    for py in _pythons_candidatos():
        tentados.append(str(py))
        if not py.is_file() or str(py) == sys.executable:
            continue
        # Só troca para um interpretador que comprovadamente tem tudo.
        if subprocess.run([str(py), "-c", teste_import], capture_output=True).returncode != 0:
            continue
        os.environ[_REEXEC_FLAG] = "1"
        os.execv(str(py), [str(py), *sys.argv])  # não retorna

    raise BrowserIndisponivel(
        f"{rotulo} não está disponível em nenhum interpretador conhecido.\n"
        "Procurei em:\n  " + "\n  ".join(tentados) + "\n"
        f"Defina {VENV_ENV} para um python com as dependências, "
        "ou rode: bash scripts/setup.sh"
    )


def garantir_playwright() -> None:
    """Para quem sobe navegador: render do Design IA e QA do LP Builder."""
    _garantir(("playwright",))


def garantir_pillow() -> None:
    """Para quem lê imagem: validate.py do Design IA e drive_ingest.py do LP."""
    _garantir(("PIL",))


# ------------------------------------------------------------------- navegador

def _chromium_da_plataforma() -> list[pathlib.Path]:
    """Chromium já provisionado pelo ambiente, via PLAYWRIGHT_BROWSERS_PATH."""
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    # "0" significa "guarde os browsers junto do pacote" — não é um diretório.
    if not base or base == "0":
        return []
    raiz = pathlib.Path(base)
    if not raiz.is_dir():
        return []
    achados: list[pathlib.Path] = []
    atalho = raiz / "chromium"          # algumas imagens deixam um symlink pronto
    if atalho.is_file():
        achados.append(atalho)
    # Mais recente primeiro: o número da build ordena lexicograficamente bem.
    achados += sorted(raiz.glob("chromium-*/chrome-linux/chrome"), reverse=True)
    achados += sorted(raiz.glob("chromium-*/chrome-linux64/chrome"), reverse=True)
    achados += sorted(raiz.glob("chromium_headless_shell-*/chrome-linux/headless_shell"),
                      reverse=True)
    return achados


def chromium_candidatos() -> list[pathlib.Path | None]:
    """Candidatos na ordem documentada. `None` = deixar o Playwright decidir."""
    fila: list[pathlib.Path | None] = []

    explicito = os.environ.get(CHROMIUM_ENV)
    if explicito:
        fila.append(pathlib.Path(explicito).expanduser())

    fila += _chromium_da_plataforma()
    fila.append(None)
    fila += [pathlib.Path(p) for p in CHROMIUM_DO_SISTEMA]

    vistos: set[str] = set()
    unicos: list[pathlib.Path | None] = []
    for c in fila:
        chave = "" if c is None else str(c)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(c)
    return unicos


def _erro(tentativas: list[str]) -> BrowserIndisponivel:
    return BrowserIndisponivel(
        "nenhum Chromium utilizável foi encontrado.\n"
        "Tentei, nesta ordem:\n  " + "\n  ".join(tentativas) + "\n"
        f"Aponte um navegador com {CHROMIUM_ENV}=/caminho/para/chrome, "
        "ou instale o do Playwright:\n"
        "  apps/lp-builder/venv/bin/python -m playwright install chromium"
    )


def lancar_chromium(chromium, **kwargs):
    """Sobe o Chromium no primeiro candidato que funcionar (API síncrona)."""
    tentativas: list[str] = []
    for cand in chromium_candidatos():
        rotulo = str(cand) if cand else "navegador gerenciado pelo Playwright"
        if cand is not None and not cand.is_file():
            tentativas.append(f"{rotulo}  (não existe)")
            continue
        try:
            extra = {"executable_path": str(cand)} if cand else {}
            return chromium.launch(**extra, **kwargs)
        except Exception as e:  # noqa: BLE001 - o motivo vai para a mensagem final
            tentativas.append(f"{rotulo}  ({str(e).splitlines()[0][:110]})")
    raise _erro(tentativas)


async def lancar_chromium_async(chromium, **kwargs):
    """Mesma ordem de busca, para a API assíncrona (QA do LP Builder)."""
    tentativas: list[str] = []
    for cand in chromium_candidatos():
        rotulo = str(cand) if cand else "navegador gerenciado pelo Playwright"
        if cand is not None and not cand.is_file():
            tentativas.append(f"{rotulo}  (não existe)")
            continue
        try:
            extra = {"executable_path": str(cand)} if cand else {}
            return await chromium.launch(**extra, **kwargs)
        except Exception as e:  # noqa: BLE001
            tentativas.append(f"{rotulo}  ({str(e).splitlines()[0][:110]})")
    raise _erro(tentativas)


def instalar_no_sys_path() -> None:
    """Deixa este módulo importável a partir de um motor. Uso:

        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[N] / "shared" / "pylib"))
        import squadnk_browser
    """
    d = str(pathlib.Path(__file__).resolve().parent)
    if d not in sys.path:
        sys.path.insert(0, d)


if __name__ == "__main__":
    # Diagnóstico: `python3 shared/pylib/squadnk_browser.py`
    print("interpretadores candidatos:")
    for p in _pythons_candidatos():
        print(f"  {'OK ' if p.is_file() else '-- '} {p}")
    print("navegadores candidatos:")
    for c in chromium_candidatos():
        if c is None:
            print("  ?   navegador gerenciado pelo Playwright")
        else:
            print(f"  {'OK ' if c.is_file() else '-- '} {c}")
