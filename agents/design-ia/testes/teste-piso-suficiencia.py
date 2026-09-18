#!/usr/bin/env python3
"""O piso de suficiência no ponto onde a peça ainda pode mudar.

A barreira de defeito responde "há erro?". Este piso responde "a peça presta?".
Peça sem defeito nenhum passava direto — era exatamente assim que o layout
preenchido chegava ao cliente. Aqui se prova que ele não passa mais.

    python3 agents/design-ia/testes/teste-piso-suficiencia.py
"""
from __future__ import annotations

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))

import artdirection                                        # noqa: E402

falhas = []


def checar(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


def bloqueia(ad) -> str | None:
    """Devolve a mensagem de bloqueio, ou None se a direção passou."""
    try:
        artdirection.validar_suficiencia(ad)
        return None
    except SystemExit as e:
        return str(e)


BOM = {
    "especifico": "25 anos de casa e o endereco da Savassi - nenhum concorrente tem essa data",
    "ideia_visual": "a abobora sai do quadro pela esquerda em escala forcada e o texto ocupa o negativo",
    "motivo_de_parada": "o laranja saturado contra o preto, num feed que em outubro esta cheio de branco",
}

# ------------------------------------------------ 1 · o bloco tem de existir
checar("1/sem-bloco-bloqueia", bloqueia({}) is not None)
checar("1/sem-bloco-explica", "suficiencia" in (bloqueia({}) or ""))
checar("1/bloco-nao-dict-bloqueia", bloqueia({"suficiencia": "sim"}) is not None)

# ------------------------------------------------ 2 · vazio não é resposta
for vazio in ("", "   ", "-", "n/a", "nada", "padrao", "ok", "a definir"):
    ad = {"suficiencia": dict(BOM, especifico=vazio)}
    checar(f"2/vazio[{vazio.strip() or 'branco'}]-bloqueia", bloqueia(ad) is not None)

# ------------------------------------------------ 3 · resposta curta não é verificável
ad = {"suficiencia": dict(BOM, ideia_visual="recorte")}
msg = bloqueia(ad)
checar("3/curta-bloqueia", msg is not None)
checar("3/curta-diz-o-motivo", "curta demais" in (msg or ""), (msg or "")[:80])

# ------------------------------------------------ 4 · cada campo é cobrado
for campo in ("especifico", "ideia_visual", "motivo_de_parada"):
    ad = {"suficiencia": dict(BOM, **{campo: ""})}
    msg = bloqueia(ad) or ""
    checar(f"4/{campo}-cobrado", campo in msg, msg[:80])

# ------------------------------------------------ 5 · as três de uma vez
ad = {"suficiencia": {"especifico": "", "ideia_visual": "", "motivo_de_parada": ""}}
msg = bloqueia(ad) or ""
checar("5/lista-as-tres", all(c in msg for c in artdirection.SUFICIENCIA_CAMPOS), msg[:120])

# ------------------------------------------------ 6 · resposta concreta passa
checar("6/bom-passa", bloqueia({"suficiencia": BOM}) is None, bloqueia({"suficiencia": BOM}) or "")

# ------------------------------------------------ 7 · peça sóbria também passa
#     O piso não exige originalidade: exige que a peça seja daquele cliente e
#     tenha sido composta. Um anúncio clássico e simples atende sem esforço.
sobrio = {
    "especifico": "a tabela de precos do combo executivo, que so o Camarero pratica nesse horario",
    "ideia_visual": "o prato ocupa dois tercos do quadro e o preco entra dentro da propria foto",
    "motivo_de_parada": "o preco grande em cima da comida, que e o que a pessoa procura no almoco",
}
checar("7/sobrio-passa", bloqueia({"suficiencia": sobrio}) is None)

# ------------------------------------------------ 8 · o compilador chama o piso
fonte = (RAIZ / "engine" / "artdirection.py").read_text(encoding="utf-8")
checar("8/compile-chama-o-piso", "validar_suficiencia(ad)" in fonte)
checar("8/schema-documenta-o-piso", '"suficiencia"' in artdirection.SCHEMA)

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print("\nteste-piso-suficiencia: bloco, vazio, enrolação, curto e peça sóbria · OK")
sys.exit(0)
