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

# ------------------------------------------------ 7b · legenda de template nao e ideia
#     Achado da prova do Bloco 2: a resposta que DESCREVE onde cada slot ficou
#     passava no piso. "headline centralizada sobre fundo solido, botao abaixo"
#     e a legenda do arranjo padrao -- exatamente o que o piso existe para
#     rejeitar. Agora so passa quem nomeia o que acontece com o QUADRO.
legenda_de_template = [
    "headline centralizada sobre fundo solido da cor primaria, com o botao logo abaixo",
    "fundo azul, titulo em cima, subtitulo no meio, botao e logo no rodape",
    "texto alinhado a esquerda sobre o fundo da cor da marca, assinatura no rodape",
    "eyebrow acima, headline ao centro, CTA abaixo e wordmark embaixo",
    "composicao centralizada: titulo, subtitulo e botao um sobre o outro no fundo chapado",
]
for i, v in enumerate(legenda_de_template, 1):
    ad = {"suficiencia": dict(BOM, ideia_visual=v)}
    msg = bloqueia(ad) or ""
    checar(f"7b/legenda[{i}]-bloqueia", msg != "", v[:60])
    checar(f"7b/legenda[{i}]-explica", "decisao de composicao" in msg, msg[:90])

#     E o inverso: citar um slot nao condena a resposta, desde que haja movimento.
com_movimento = [
    "a headline invade a foto pela esquerda, sangrando no corte do quadro",
    "o prato ocupa dois tercos do quadro em plano fechado e o preco entra dentro da foto",
    "o numero 25 vira imagem, recortado pela borda superior, e o texto ocupa o negativo",
    "hierarquia invertida - o dado vem maior que a chamada, com respiro assimetrico",
    "o grafismo da marca atravessa o quadro em diagonal e separa preco de servico",
    "tipografia como imagem, em caixa alta vazada sobre a textura do acervo",
]
for i, v in enumerate(com_movimento, 1):
    checar(f"7b/movimento[{i}]-passa", bloqueia({"suficiencia": dict(BOM, ideia_visual=v)}) is None, v[:60])

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
