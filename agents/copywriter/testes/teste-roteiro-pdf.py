#!/usr/bin/env python3
"""Testes do motor que fecha roteiro em PDF.

Roda num diretório temporário, não toca em entrega de cliente e não publica nada.
Prova o que já quebrou uma vez: hashtag virando título, quebra de linha do autor
sumindo no parágrafo, e o PDF que simplesmente não sai.

    python3 agents/copywriter/testes/teste-roteiro-pdf.py
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))

import roteiro_pdf                                         # noqa: E402

falhas = []


def checar(nome: str, condicao: bool, detalhe: str = "") -> None:
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


EXEMPLO = """# 2 roteiros · Cliente Exemplo

Talking head · até 30s

# ROTEIRO 1 · "Gancho de teste"

**3. HOOK (0-3s)**

> Primeira frase falada.

**9. Variações de hook (A/B)**
A. "Variação um."
B. "Variação dois."

| Bloco | O que aparece |
|---|---|
| 0-3s | Plano fechado |

**8. Legenda do post**

> Corpo da legenda.
>
> #TagUm #TagDois #TagTres

# ROTEIRO 2 · "Segundo"

> Outra fala.
"""

# ------------------------------------------------ 1 · hashtag não vira título

html = roteiro_pdf.markdown_para_html(EXEMPLO)
checar("hashtag/nao-vira-titulo", "<h1>TagUm" not in html and ">TagUm" not in html,
       "hashtag no começo da linha foi lida como heading")
checar("hashtag/sobrevive", "#TagUm #TagDois #TagTres" in html, html[-400:])

# ------------------------------------------------ 2 · quebra de linha do autor

checar("quebra/variacoes-separadas", html.count("<br") >= 1,
       "A e B viraram um parágrafo só — a quebra do autor se perdeu")

# ------------------------------------------------ 3 · estrutura preservada

# Três: o título do documento mais um por roteiro. O do documento vira capa e sai
# do corpo dentro do main() — aqui a conversão é do texto cru.
checar("estrutura/titulos", html.count("<h1>") == 3, f"{html.count('<h1>')} h1")
checar("estrutura/tabela", "<table>" in html and "<th>" in html)
checar("estrutura/fala", "<blockquote>" in html)

# ------------------------------------------------ 4 · capa e título

checar("capa/titulo", roteiro_pdf.primeiro_titulo(EXEMPLO) == "2 roteiros · Cliente Exemplo",
       roteiro_pdf.primeiro_titulo(EXEMPLO))

# ------------------------------------------------ 5 · o PDF sai de verdade

with tempfile.TemporaryDirectory(prefix="squad-nk-roteiro-") as tmp:
    origem = pathlib.Path(tmp) / "roteiros.md"
    origem.write_text(EXEMPLO, encoding="utf-8")
    codigo = roteiro_pdf.main([str(origem), "--cliente", "Cliente Exemplo"])
    destino = origem.with_suffix(".pdf")
    checar("pdf/codigo", codigo == 0)
    checar("pdf/existe", destino.is_file(), "o motor não gravou o PDF")
    if destino.is_file():
        bruto = destino.read_bytes()
        checar("pdf/assinatura", bruto[:5] == b"%PDF-", str(bruto[:8]))
        paginas = bruto.count(b"/Type /Page") - bruto.count(b"/Type /Pages")
        checar("pdf/um-roteiro-por-pagina", paginas >= 2, f"{paginas} página(s)")

# ------------------------------------------------ veredito

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print("\nteste-roteiro-pdf: markdown, quebra de linha, hashtag e render do PDF · OK")
sys.exit(0)
