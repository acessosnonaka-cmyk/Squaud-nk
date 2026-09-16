#!/usr/bin/env python3
"""Fecha um roteiro em PDF — o formato de entrega de roteiro do Squad.

Por que motor e não "o agente gera": PDF de entrega não pode depender de o
Copywriter lembrar de montar um. Roteiro vai para um set de gravação, é aberto
no celular de quem dirige e impresso por quem opera a câmera. Formato de entrega
é contrato, e contrato mora em código.

    python3 roteiro_pdf.py entrega.md
    python3 roteiro_pdf.py entrega.md --saida /caminho/roteiros.pdf
    python3 roteiro_pdf.py entrega.md --cliente "Guilherme Luiz" --titulo "4 roteiros"

Entra Markdown, sai PDF A4. Cada `# ` vira uma página nova: um roteiro por
folha, que é como a peça é usada na gravação. O bloco citado (`> `) é o texto
falado e sai em corpo grande — é o que a pessoa lê na hora.

Depende de playwright + chromium (o mesmo do render do Designer e do QA do LP
Builder) e do pacote markdown. `scripts/check.sh` confere os dois.
"""
from __future__ import annotations

import argparse
import datetime
import html
import pathlib
import re
import sys

A4 = {"width": "210mm", "height": "297mm"}


def _erro(msg: str) -> "NoReturn":                       # type: ignore[valid-type]
    print(f"erro: {msg}", file=sys.stderr)
    raise SystemExit(1)


# ------------------------------------------------------------------ markdown

# Roteiro tem hashtag, e hashtag começa com o mesmo caractere de título. Sem
# isto, "#LeiSeca" no fim de uma legenda vira um H1 no meio da página.
HASHTAG_NO_COMECO = re.compile(r"^((?:>\s*)*)#(?=\S)", re.MULTILINE)


def markdown_para_html(texto: str) -> str:
    try:
        import markdown                                   # type: ignore
    except ImportError:
        _erro("pacote 'markdown' ausente — rode: python3 -m pip install markdown")
    return markdown.markdown(
        HASHTAG_NO_COMECO.sub(r"\1\\#", texto),
        # nl2br porque em roteiro a quebra de linha é do autor: fala, marcação de
        # tempo e variação de gancho perdem o sentido se o parágrafo as costura.
        extensions=["tables", "sane_lists", "attr_list", "nl2br"],
        output_format="html5",
    )


def primeiro_titulo(texto: str) -> str:
    for linha in texto.splitlines():
        if linha.startswith("# "):
            return linha[2:].strip()
    return ""


# ------------------------------------------------------------------ documento

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }

:root {
  --tinta:   #16181d;
  --suave:   #5b6472;
  --linha:   #dfe3ea;
  --marca:   #2a78d6;
  --fundo:   #f4f6fa;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  color: var(--tinta);
  background: #fff;
  font-family: system-ui, -apple-system, "Segoe UI", "DejaVu Sans", Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

/* Capa do documento: quem é o cliente, o que é a peça, quando foi fechada. */
.capa { padding: 8mm 0 6mm; border-bottom: 2px solid var(--tinta); margin-bottom: 8mm; }
.capa .cliente {
  font-size: 9pt; letter-spacing: .14em; text-transform: uppercase;
  color: var(--marca); font-weight: 700; margin-bottom: 3mm;
}
.capa h1 { font-size: 21pt; line-height: 1.2; margin: 0 0 3mm; letter-spacing: -.01em; }
.capa .meta { font-size: 8.5pt; color: var(--suave); }

/* Um roteiro por folha. O primeiro não quebra, senão a capa fica sozinha. */
h1 { font-size: 16pt; line-height: 1.25; margin: 0 0 4mm; letter-spacing: -.01em;
     page-break-before: always; page-break-after: avoid; }
h1:first-of-type { page-break-before: auto; }
.capa + h1 { page-break-before: auto; }

h2 { font-size: 12pt; margin: 7mm 0 2.5mm; page-break-after: avoid; }
h3 { font-size: 10pt; margin: 5mm 0 2mm; color: var(--suave);
     letter-spacing: .06em; text-transform: uppercase; page-break-after: avoid; }

p { margin: 0 0 2.5mm; }
strong { font-weight: 700; }

/* O texto falado. É o que se lê na gravação, então é o maior elemento da
   página — e não quebra no meio de uma fala. */
blockquote {
  margin: 2mm 0 4mm; padding: 3.5mm 5mm;
  background: var(--fundo); border-left: 3px solid var(--marca);
  border-radius: 0 3px 3px 0;
  font-size: 13pt; line-height: 1.5; page-break-inside: avoid;
}
blockquote p { margin: 0 0 2mm; }
blockquote p:last-child { margin-bottom: 0; }

table {
  width: 100%; border-collapse: collapse; margin: 2mm 0 5mm;
  font-size: 9.5pt; page-break-inside: avoid;
}
th {
  text-align: left; padding: 2mm 3mm; background: var(--fundo);
  border-bottom: 1.5px solid var(--linha); font-size: 8.5pt;
  letter-spacing: .06em; text-transform: uppercase; color: var(--suave);
}
td { padding: 2mm 3mm; border-bottom: 1px solid var(--linha); vertical-align: top; }
td:first-child { white-space: nowrap; font-weight: 600; width: 1%; }

ul, ol { margin: 0 0 3mm; padding-left: 5mm; }
li { margin-bottom: 1.5mm; }

hr { border: 0; border-top: 1px solid var(--linha); margin: 6mm 0; }

code {
  font-family: "DejaVu Sans Mono", ui-monospace, Menlo, Consolas, monospace;
  font-size: 9pt; background: var(--fundo); padding: .4mm 1.2mm; border-radius: 2px;
}
"""

MOLDE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<style>{css}</style>
</head>
<body>
<div class="capa">
  {cliente}
  <h1>{titulo}</h1>
  <div class="meta">{meta}</div>
</div>
{corpo}
</body>
</html>
"""


def montar_html(corpo: str, *, titulo: str, cliente: str, meta: str) -> str:
    return MOLDE.format(
        css=CSS,
        titulo=html.escape(titulo),
        cliente=f'<div class="cliente">{html.escape(cliente)}</div>' if cliente else "",
        meta=html.escape(meta),
        corpo=corpo,
    )


# ------------------------------------------------------------------ render

def gravar_pdf(html_doc: str, destino: pathlib.Path, rodape: str) -> None:
    try:
        from playwright.sync_api import sync_playwright    # type: ignore
    except ImportError:
        _erro("playwright ausente — rode: python3 -m pip install playwright "
              "&& python3 -m playwright install chromium")

    # Rodapé do Chromium: procedência em toda página, porque a folha circula
    # solta no set e uma página perdida precisa dizer de quem ela é.
    modelo_rodape = (
        '<div style="width:100%;font-size:7pt;color:#5b6472;'
        'padding:0 16mm;display:flex;justify-content:space-between;">'
        f'<span>{html.escape(rodape)}</span>'
        '<span class="pageNumber"></span>'
        '</div>'
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        try:
            navegador = pw.chromium.launch()
        except Exception as exc:                            # noqa: BLE001
            _erro(f"chromium não abriu ({exc}). Confira com: bash scripts/check.sh")
        pagina = navegador.new_page()
        pagina.set_content(html_doc, wait_until="load")
        pagina.pdf(
            path=str(destino), format="A4", print_background=True,
            display_header_footer=True,
            header_template='<div></div>', footer_template=modelo_rodape,
            margin={"top": "18mm", "bottom": "20mm", "left": "0mm", "right": "0mm"},
        )
        navegador.close()


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="roteiro_pdf",
        description="Fecha um roteiro em PDF — formato de entrega de roteiro do Squad.")
    ap.add_argument("markdown", help="arquivo .md com o roteiro pronto")
    ap.add_argument("--saida", help="PDF de destino. Padrão: mesmo nome, extensão .pdf")
    ap.add_argument("--titulo", help="título da capa. Padrão: o primeiro # do arquivo")
    ap.add_argument("--cliente", default="", help="nome do cliente, impresso na capa")
    ap.add_argument("--data", help="data da entrega. Padrão: hoje")
    a = ap.parse_args(argv)

    origem = pathlib.Path(a.markdown).expanduser().resolve()
    if not origem.is_file():
        _erro(f"arquivo não encontrado: {origem}")
    texto = origem.read_text(encoding="utf-8")

    titulo = a.titulo or primeiro_titulo(texto) or origem.stem
    data = a.data or datetime.date.today().isoformat()
    meta = " · ".join(x for x in ("Roteiro", data) if x)
    rodape = " · ".join(x for x in (a.cliente, titulo, data) if x)

    # O primeiro # já virou capa: tirar daqui evita o título repetido na página 1.
    corpo = re.sub(r"^#\s+.*?$\n?", "", texto, count=1, flags=re.MULTILINE)

    destino = pathlib.Path(a.saida).expanduser() if a.saida else origem.with_suffix(".pdf")
    gravar_pdf(montar_html(markdown_para_html(corpo), titulo=titulo,
                           cliente=a.cliente, meta=meta),
               destino, rodape)
    print(destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
