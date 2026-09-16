#!/usr/bin/env python3
"""Testes do contexto externo de cliente — o acervo do Drive lido pelo Diretor.

Não toca no Drive: o conector é do agente, não do motor. O que se prova aqui é a
decisão que o motor sustenta — qual cliente é este, o que do acervo vale como
Source of Truth, o que é apenas referência e o que nunca atravessa de um cliente
para outro. Roda inteiro num SQUAD_DATA_HOME temporário.

    python3 agents/diretor-operacoes/testes/teste-contexto-cliente.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

TMP = tempfile.mkdtemp(prefix="squad-nk-contexto-")
os.environ["SQUAD_DATA_HOME"] = TMP

from engine import demanda, modelo                            # noqa: E402

falhas = []


def checar(nome: str, condicao: bool, detalhe: str = "") -> None:
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@contextlib.contextmanager
def calado():
    """O teste roda o CLI de verdade; o que importa é o efeito, não a tela."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def base(cliente, pasta_id, pasta_nome="", aliases=()):
    with calado():
        demanda.cmd_cliente_base_definir(Args(
            cliente=cliente, fonte_externa="drive", pasta_id=pasta_id,
            pasta_nome=pasta_nome, alias=list(aliases)))


def fonte(cliente, classe, titulo, *, ref="", resumo="", verificado_em=None):
    with calado():
        demanda.cmd_cliente_fonte_add(Args(
            cliente=cliente, classe=classe, titulo=titulo, resumo=resumo,
            fonte_externa="drive", ref=ref, link="", verificado_em=verificado_em,
            demanda=None))
    return ultima_fonte(cliente)


def ultima_fonte(cliente):
    return modelo.carregar_fontes(cliente)["fontes"][-1]["id"]


def montar_briefing(cliente, agente="designer", fontes=None, objetivo="peça de feed"):
    """Abre uma demanda de verdade pelo CLI e devolve o briefing gravado."""
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        demanda.cmd_nova(Args(cliente=cliente, titulo=objetivo, descricao=objetivo,
                              objetivo=objetivo, contexto=None, prioridade="normal"))
    did = saida.getvalue().strip().splitlines()[0].strip()
    with calado():
        demanda.cmd_planejar(Args(demanda=did, plano="um job"))
        demanda.cmd_job_add(Args(demanda=did, agente=agente, objetivo=objetivo,
                                 entrada=None, saida="peça pronta", criterio=None,
                                 restricao=None, depende=None, fonte=list(fontes or [])))
        demanda.cmd_briefing(Args(demanda=did, job="JOB-001", forcar=False, json=True))
    return modelo.ler_json(modelo.dir_demanda(did) / "handoffs" / "JOB-001.briefing.json")


def texto_do(briefing) -> str:
    return "\n".join(briefing.get("fontes_canonicas", []))


def referencias_do(briefing) -> str:
    return "\n".join(briefing.get("referencias_nao_canonicas", []))


# ------------------------------------------------ 1 · cliente encontrado no acervo

base("camarero-vix", "1CAM", "Clientes/Camarero VIX", ["CamareroVIX", "Camarero Vix Restaurante"])
achados = modelo.resolver_cliente("camarero-vix")
checar("1/encontrado", len(achados) == 1 and achados[0]["cliente"] == "camarero-vix",
       str([a["cliente"] for a in achados]))
checar("1/base", (achados[0]["base"] or {}).get("pasta_id") == "1CAM")

# ------------------------------------------------ 2 · cliente não encontrado

checar("2/nao-encontrado", modelo.resolver_cliente("Padaria Que Nunca Existiu") == [])
ctx = modelo.contexto_cliente("padaria-que-nunca-existiu")
checar("2/nao-derruba", ctx["base_externa"] == "" and ctx["fontes_canonicas"] == [],
       "contexto de cliente sem base precisa sair vazio, não levantar")

# ------------------------------------------------ 3 · variação inequívoca do nome

for variacao in ("CamareroVIX", "Camarero VIX", "camarero vix restaurante", "CAMARERO  VIX"):
    achados = modelo.resolver_cliente(variacao)
    checar(f"3/variacao[{variacao}]", len(achados) == 1 and achados[0]["cliente"] == "camarero-vix",
           str([a["cliente"] for a in achados]))

# ------------------------------------------------ 3b · acento não cria outro cliente

# Um cliente escrito com e sem acento é o mesmo cliente. Quando não era, o
# acervo dele nascia partido em dois arquivos e a segunda demanda não
# enxergava o que a primeira tinha registrado.
for par in [("Vandário Garnet", "Vandario Garnet"),
            ("Açaí & Cia", "Acai & Cia"),
            ("João Pão", "Joao Pao")]:
    checar(f"3b/acento[{par[0]}]", modelo.slug(par[0]) == modelo.slug(par[1]),
           f"{modelo.slug(par[0])} != {modelo.slug(par[1])}")
checar("3b/legivel", modelo.slug("Vandário Garnet") == "vandario-garnet",
       modelo.slug("Vandário Garnet"))
checar("3b/nao-vira-traco", "-" not in modelo.slug("Açaí").replace("acai", ""),
       modelo.slug("Açaí"))

base("Vandário Garnet", "1VG", "Vandário Garnet - Nonaka ADS")
checar("3b/resolve-sem-acento", len(modelo.resolver_cliente("Vandario Garnet")) == 1,
       "cliente sem acento não achou o registro gravado com acento")
checar("3b/um-arquivo-so",
       modelo.caminho_fontes("Vandário Garnet") == modelo.caminho_fontes("VANDARIO GARNET"))

# ------------------------------------------------ 4 · dois resultados ambíguos

base("studio-nk-sao-paulo", "1SP", "Clientes/Studio NK São Paulo", ["Studio NK"])
base("studio-nk-rio", "1RJ", "Clientes/Studio NK Rio", ["Studio NK"])
ambiguos = modelo.resolver_cliente("Studio NK")
checar("4/ambiguo", len(ambiguos) == 2, str([a["cliente"] for a in ambiguos]))
with calado():
    ambiguo_rc = demanda.cmd_cliente_resolver(Args(cliente="Studio NK"))
    unico_rc = demanda.cmd_cliente_resolver(Args(cliente="Studio NK Rio"))
checar("4/nao-escolhe", ambiguo_rc == 2,
       "dúvida material precisa parar o fluxo, não eleger um dos dois")
checar("4/inequivoco-ainda-resolve", unico_rc == 0)

# ------------------------------------------------ 5 · dado atual versus histórico antigo

fonte("camarero-vix", "fato", "Tabela de preços 2026", ref="1PRECO",
      resumo="ticket médio R$ 380")
fonte("camarero-vix", "fato", "Telefone da unidade", ref="1TEL", verificado_em="2025-01-01")
antigo = ultima_fonte("camarero-vix")

b = montar_briefing("camarero-vix")
checar("5/atual-e-verdade", "Tabela de preços 2026" in texto_do(b), texto_do(b))
checar("5/antigo-sai-da-verdade", "Telefone da unidade" not in texto_do(b), texto_do(b))
checar("5/antigo-rebaixado",
       modelo.classe_efetiva(modelo.achar_fonte(modelo.carregar_fontes("camarero-vix"), antigo))
       == "possivelmente_desatualizada")
b2 = montar_briefing("camarero-vix", fontes=[antigo])
checar("5/antigo-so-como-referencia", "Telefone da unidade" in referencias_do(b2), referencias_do(b2))

# ------------------------------------------------ 6 · instrução atual contradiz o histórico

fonte("camarero-vix", "decisao_vigente", "Oferta vigente: menu executivo R$ 59", ref="1OF")
fonte("camarero-vix", "campanha_anterior", "Campanha 2025: rodízio R$ 89", ref="1CAMP")
campanha = ultima_fonte("camarero-vix")
b = montar_briefing("camarero-vix", fontes=[campanha])
checar("6/vigente-e-verdade", "menu executivo R$ 59" in texto_do(b), texto_do(b))
checar("6/anterior-nao-e-verdade", "rodízio R$ 89" not in texto_do(b), texto_do(b))
checar("6/anterior-e-referencia", "rodízio R$ 89" in referencias_do(b), referencias_do(b))

# ------------------------------------------------ 7 · dois clientes completamente isolados

base("boteco-do-ze", "1ZE", "Clientes/Boteco do Zé")
fonte("boteco-do-ze", "fato", "Endereço: Rua das Palmeiras 12", ref="1END")
bz = montar_briefing("boteco-do-ze")
bc = montar_briefing("camarero-vix")
checar("7/ze-nao-ve-camarero",
       "Camarero" not in (texto_do(bz) + referencias_do(bz) + bz["base_externa"]),
       texto_do(bz) + bz["base_externa"])
checar("7/camarero-nao-ve-ze",
       "Palmeiras" not in (texto_do(bc) + referencias_do(bc)), texto_do(bc))
checar("7/arquivos-separados",
       modelo.caminho_fontes("boteco-do-ze") != modelo.caminho_fontes("camarero-vix"))
try:
    demanda._validar_fontes("boteco-do-ze", [campanha])
    checar("7/fonte-de-outro-cliente-recusada", False,
           "aceitou anexar fonte de outro cliente")
except modelo.ErroDeEstado:
    pass

# ------------------------------------------------ 8 · campanha antiga não contamina demanda nova

b = montar_briefing("camarero-vix", objetivo="campanha de setembro, conceito novo")
checar("8/nao-herda-campanha", "rodízio R$ 89" not in (texto_do(b) + referencias_do(b)),
       texto_do(b) + referencias_do(b))
checar("8/herda-fato", "Tabela de preços 2026" in texto_do(b), texto_do(b))
checar("8/referencia-exige-decisao", b["referencias_nao_canonicas"] == [],
       "não canônico viajou sem ninguém ter anexado ao job")

# ------------------------------------------------ 9 · Drive indisponível não derruba a demanda

b = montar_briefing("cliente-sem-acervo-nenhum", objetivo="peça a partir do que o gestor mandou")
checar("9/demanda-anda", b["job"] == "JOB-001" and b["execution_mode"] == "SILENT")
checar("9/sem-acervo", b["base_externa"] == "" and b["fontes_canonicas"] == [],
       "sem acervo o briefing sai sem Source of Truth externa, e sai")
with calado():
    sem_base_rc = demanda.cmd_cliente_resolver(Args(cliente="cliente-sem-acervo-nenhum"))
checar("9/resolver-nao-levanta", sem_base_rc == 0)

# ------------------------------------------------ contrato

checar("contrato/briefing-valido", modelo.validar(b, "briefing") == [])
reg = modelo.carregar_fontes("camarero-vix")
for f in reg["fontes"]:
    checar(f"contrato/fonte[{f['id']}]", modelo.validar(f, "fonte") == [])
    checar(f"contrato/rastro[{f['id']}]", bool(f.get("ref")), "fonte sem rastro de origem")
checar("contrato/sem-copia-do-acervo",
       all(not (modelo.dir_clientes() / n).is_dir() for n in ("drive", "acervo", "downloads")),
       "o registro é memória com rastro, não cópia do Drive")

# ------------------------------------------------ veredito

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print("\nteste-contexto-cliente: 9 cenários de acervo externo + contrato das fontes · OK")
sys.exit(0)
