#!/usr/bin/env python3
"""Motor de entrega: markdown do especialista -> PDF para o cliente.

Quem consolida a entrega e leva ao gestor é o Diretor, então o PDF é motor dele.
O especialista escreve markdown; este motor paginha e nada mais. Ele não decide
conteúdo, não reescreve texto e não inventa capa: título e subtítulo vêm do
argumento ou das duas primeiras linhas do arquivo.

Duas travas que vêm das regras do repositório:

* **Nada de caminho de máquina.** O Chromium é descoberto em quatro tentativas,
  nesta ordem: `$SQUAD_CHROMIUM`, o que o Playwright resolve, o que está no PATH
  e o que existe sob `$PLAYWRIGHT_BROWSERS_PATH`. Nenhum caminho fixo no código.
* **Nada de dado de cliente no git.** Entrega é peça de cliente: o motor recusa
  gravar dentro do repositório, que é onde ela não pode estar.

Roda com o python do sistema, sem venv e sem dependência externa — o conversor
de markdown é próprio, pelo mesmo motivo do leitor de `squad.yaml`: o formato é
nosso e é pequeno. Cabeçalho, tabela, lista, parágrafo, negrito, código e régua.

    python3 agents/diretor-operacoes/engine/entrega_pdf.py <entrega.md>
    python3 agents/diretor-operacoes/engine/entrega_pdf.py <entrega.md> -o <saida.pdf> \
        --titulo "Cliente · peça" --subtitulo "campanha"
"""
from __future__ import annotations

import argparse
import glob
import html
import os
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", Arial, Helvetica, sans-serif;
       font-size: 9.6pt; line-height: 1.5; color: #1b1d21; margin: 0; }
.capa { padding: 26mm 0 10mm 0; border-bottom: 3px solid #0f3b6e; margin-bottom: 10mm; }
.capa h1 { font-size: 26pt; margin: 0 0 4mm 0; color: #0f3b6e; letter-spacing: -0.4pt; }
.capa .sub { font-size: 11pt; color: #55595f; margin: 0; }
h1 { font-size: 15pt; color: #0f3b6e; margin: 9mm 0 3mm 0; page-break-after: avoid; }
h2 { font-size: 13pt; color: #0f3b6e; margin: 8mm 0 3mm 0; padding-bottom: 1.5mm;
     border-bottom: 1.5px solid #d8dde3; page-break-after: avoid; }
h3 { font-size: 10.5pt; color: #24272c; margin: 5mm 0 2mm 0; page-break-after: avoid; }
p { margin: 0 0 2.6mm 0; }
ol, ul { margin: 0 0 3mm 0; padding-left: 5mm; }
li { margin-bottom: 1.2mm; }
strong { color: #0f3b6e; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.6pt; background: #f2f4f7;
       padding: 0 1mm; border-radius: 1mm; }
hr { border: none; border-top: 1px solid #e3e7ec; margin: 7mm 0; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 4mm 0;
        font-size: 8.4pt; page-break-inside: avoid; }
th { background: #0f3b6e; color: #fff; text-align: left; font-weight: 600;
     padding: 2mm 2.2mm; border: 1px solid #0f3b6e; }
td { padding: 2mm 2.2mm; border: 1px solid #d8dde3; vertical-align: top; }
tbody tr:nth-child(even) { background: #f5f7f9; }
table td:first-child { white-space: nowrap; font-weight: 600; color: #0f3b6e; }
.quebra { page-break-before: always; }
"""

# Uma seção por página quando o documento é uma coleção de peças numeradas.
QUEBRA = re.compile(r"^(roteiro|peça|peca|criativo|variação|variacao|anúncio|anuncio)\s", re.I)


def inline(texto: str) -> str:
    """Negrito, código e escape. Nada além disso entra numa entrega."""
    partes = re.split(r"(`[^`]+`)", texto)
    saida = []
    for i, parte in enumerate(partes):
        if i % 2:
            saida.append(f"<code>{html.escape(parte[1:-1])}</code>")
        else:
            esc = html.escape(parte)
            esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
            saida.append(esc)
    return "".join(saida)


def celulas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def converter(linhas: list[str]) -> str:
    """Markdown do squad -> HTML. Conversor próprio, sem dependência externa."""
    fora: list[str] = []
    lista: str | None = None          # 'ul' | 'ol' | None
    paragrafo: list[str] = []
    i = 0

    def fecha_lista():
        nonlocal lista
        if lista:
            fora.append(f"</{lista}>")
            lista = None

    def fecha_paragrafo():
        if paragrafo:
            fora.append(f"<p>{inline(' '.join(paragrafo))}</p>")
            paragrafo.clear()

    def fecha_tudo():
        fecha_paragrafo()
        fecha_lista()

    while i < len(linhas):
        linha = linhas[i].rstrip()
        cru = linha.strip()

        if not cru:
            fecha_tudo()
            i += 1
            continue

        if cru.startswith("|") and i + 1 < len(linhas) and re.fullmatch(
                r"\|[\s:|-]+\|", linhas[i + 1].strip()):
            fecha_tudo()
            cabecalho = celulas(linha)
            i += 2
            corpo = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                corpo.append(celulas(linhas[i]))
                i += 1
            fora.append("<table>")
            if any(c for c in cabecalho):          # cabeçalho vazio não vira faixa
                fora.append("<thead><tr>"
                            + "".join(f"<th>{inline(c)}</th>" for c in cabecalho)
                            + "</tr></thead>")
            fora.append("<tbody>")
            for linha_corpo in corpo:
                fora.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in linha_corpo) + "</tr>")
            fora.append("</tbody></table>")
            continue

        if re.fullmatch(r"-{3,}|_{3,}|\*{3,}", cru):
            fecha_tudo()
            fora.append("<hr>")
            i += 1
            continue

        cabecalho = re.match(r"(#{1,4})\s+(.*)", cru)
        if cabecalho:
            fecha_tudo()
            nivel = min(len(cabecalho.group(1)), 3)
            titulo = cabecalho.group(2).strip()
            classe = ' class="quebra"' if nivel == 2 and QUEBRA.match(titulo) else ""
            fora.append(f"<h{nivel}{classe}>{inline(titulo)}</h{nivel}>")
            i += 1
            continue

        item = re.match(r"(?:([-*+])|(\d+)[.)])\s+(.*)", cru)
        if item:
            fecha_paragrafo()
            tipo = "ul" if item.group(1) else "ol"
            if lista != tipo:
                fecha_lista()
                fora.append(f"<{tipo}>")
                lista = tipo
            fora.append(f"<li>{inline(item.group(3))}</li>")
            i += 1
            continue

        fecha_lista()
        paragrafo.append(cru)
        i += 1

    fecha_tudo()
    return "\n".join(fora)


def chromium() -> str:
    """Onde está o Chromium desta máquina. Sem caminho fixo, sem chute."""
    env = os.environ.get("SQUAD_CHROMIUM")
    if env and pathlib.Path(env).is_file():
        return env

    try:                                            # o mesmo que o check.sh consulta
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            caminho = pw.chromium.executable_path
        if caminho and pathlib.Path(caminho).is_file():
            return caminho
    except Exception:
        pass

    for nome in ("chromium", "chromium-browser", "chrome", "google-chrome",
                 "google-chrome-stable"):
        achado = shutil.which(nome)
        if achado:
            return achado

    raiz = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if raiz:
        for padrao in ("chromium*/chrome-linux/chrome",
                       "chromium*/chrome-linux/headless_shell",
                       "chromium*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
            for achado in sorted(glob.glob(str(pathlib.Path(raiz) / padrao)), reverse=True):
                if os.access(achado, os.X_OK):
                    return achado

    raise SystemExit(
        "Chromium não encontrado. Defina SQUAD_CHROMIUM no .env, instale o Chromium do "
        "Playwright ('python3 -m playwright install chromium') ou deixe um chromium no PATH."
    )


def gerar(origem: pathlib.Path, destino: pathlib.Path,
          titulo: str = "", subtitulo: str = "") -> pathlib.Path:
    linhas = origem.read_text(encoding="utf-8").split("\n")

    if linhas and linhas[0].startswith("# "):       # a primeira linha é a capa
        titulo = titulo or linhas[0][2:].strip()
        linhas = linhas[1:]
        while linhas and not linhas[0].strip():
            linhas = linhas[1:]
        if linhas and not linhas[0].startswith("#") and not linhas[0].startswith("|"):
            subtitulo = subtitulo or linhas[0].strip()
            linhas = linhas[1:]
    titulo = titulo or origem.stem

    doc = (
        '<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8">\n'
        f"<title>{html.escape(titulo)}</title><style>{CSS}</style></head>\n<body>\n"
        f'<div class="capa"><h1>{html.escape(titulo)}</h1>'
        f'<p class="sub">{html.escape(subtitulo)}</p></div>\n'
        f"{converter(linhas)}\n</body></html>"
    )

    pagina = destino.with_suffix(".entrega.html")
    pagina.write_text(doc, encoding="utf-8")
    try:
        subprocess.run(
            [chromium(), "--headless", "--no-sandbox", "--disable-gpu",
             "--no-pdf-header-footer", f"--print-to-pdf={destino}", pagina.as_uri()],
            check=True, capture_output=True,
        )
    finally:
        pagina.unlink(missing_ok=True)
    return destino


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="entrega_pdf", description="Markdown da entrega -> PDF para o cliente")
    ap.add_argument("entrada", help="markdown escrito pelo especialista")
    ap.add_argument("-o", "--saida", help="PDF de saída (padrão: mesmo nome, fora do repositório)")
    ap.add_argument("--titulo", default="", help="capa; padrão: o '# ' do arquivo")
    ap.add_argument("--subtitulo", default="", help="linha sob o título")
    a = ap.parse_args(argv)

    origem = pathlib.Path(a.entrada).expanduser().resolve()
    if not origem.is_file():
        print(f"erro: entrada não existe: {origem}", file=sys.stderr)
        return 2
    destino = pathlib.Path(a.saida).expanduser().resolve() if a.saida else origem.with_suffix(".pdf")

    # Regra 2 do repositório: peça de cliente não entra no git, nem por engano.
    if REPO == destino or REPO in destino.parents:
        print(f"erro: {destino} está dentro do repositório. Entrega é dado de cliente e fica "
              "fora do git — use SQUAD_DATA_HOME (padrão ~/.squad-nk).", file=sys.stderr)
        return 2

    destino.parent.mkdir(parents=True, exist_ok=True)
    gerar(origem, destino, a.titulo, a.subtitulo)
    print(f"{destino}  ({destino.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
