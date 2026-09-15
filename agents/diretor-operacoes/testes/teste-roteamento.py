#!/usr/bin/env python3
"""Testes internos de orquestração — roteamento, contrato e travas.

Não produz entregável, não aciona especialista, não executa ação externa e não
toca em dado de cliente: roda inteiro num SQUAD_DATA_HOME temporário. O que ele
prova é que o Diretor consegue rotear pela capability certa, que o briefing sai
com o contrato completo e que as travas de entrada e saída realmente barram.

    python3 agents/diretor-operacoes/testes/teste-roteamento.py
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

TMP = tempfile.mkdtemp(prefix="squad-nk-teste-")
os.environ["SQUAD_DATA_HOME"] = TMP

from engine import auditoria, demanda, modelo, roster   # noqa: E402

falhas = []


def checar(nome: str, condicao: bool, detalhe: str = "") -> None:
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


def erro_de(fn, *args, **kwargs) -> str:
    """Executa esperando recusa. Devolve a mensagem; string vazia se passou."""
    try:
        fn(*args, **kwargs)
        return ""
    except modelo.ErroDeEstado as exc:
        return str(exc)


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ------------------------------------------------------------ 1 · roteamento

CENARIOS = [
    ("copy",              ["copywriting.meta_ads"],                                    ["copywriter"]),
    ("criativo",          ["copywriting.meta_ads", "design.peca_grafica", "revisao.visual"],
                          ["copywriter", "designer", "revisor-arte"]),
    ("revisao",           ["revisao.visual"],                                          ["revisor-arte"]),
    ("landing page",      ["copywriting.landing_page", "lp.implementacao", "lp.qa"],
                          ["copywriter", "lp-builder"]),
    ("video",             ["copywriting.script", "video.edicao"],                      ["copywriter", "legend-ia"]),
    ("trafego",           ["trafego.criacao"],                                         ["gestor-trafego"]),
    ("campanha completa", ["copywriting.landing_page", "design.peca_grafica", "video.edicao",
                           "lp.implementacao", "revisao.visual"],
                          ["copywriter", "designer", "legend-ia", "lp-builder", "revisor-arte"]),
]

for nome, capabilities, esperado in CENARIOS:
    donos = []
    for c in capabilities:
        dono = roster.dono_da_capability(c)
        checar(f"roteamento/{nome}", dono is not None, f"capability sem dono: {c}")
        if dono and dono["id"] not in donos:
            donos.append(dono["id"])
    checar(f"roteamento/{nome}", sorted(donos) == sorted(esperado), f"{donos} != {esperado}")

# O menor Squad: capability de copy não arrasta ninguém além do Copywriter.
checar("menor-squad", roster.dono_da_capability("copywriting")["id"] == "copywriter")
checar("menor-squad", roster.dono_da_capability("revisao")["id"] == "revisor-arte")

# ------------------------------------------------------------ 2 · roster íntegro

_falhas_roster, _notas, _ = auditoria.auditar()
checar("auditoria", not _falhas_roster, "; ".join(_falhas_roster))
checar("auditoria/conceito", [n.split(":")[0] for n in _notas] == ["gestor-trafego"],
       "o único bloqueio conhecido é o Gestor de Tráfego")

# ------------------------------------------------------------ 3 · ensaio do contrato

PEDIDO = "Quero 2 criativos para Meta Ads do implante unitário, com copy e revisão."
did = None


def rodar(fn, **kw) -> int:
    return fn(Args(**kw))


rodar(demanda.cmd_nova, cliente="cliente-teste", titulo="Ensaio", descricao=PEDIDO,
      objetivo="testar o contrato", contexto="", prioridade="normal")
did = modelo.listar()[0]["id"]

rodar(demanda.cmd_planejar, demanda=did, plano="copy -> arte -> revisão")

# Agente sem executor não recebe job: o motor recusa em vez de fingir integração.
msg = erro_de(rodar, demanda.cmd_job_add, demanda=did, agente="gestor-trafego",
              objetivo="subir campanha", entrada=None, saida="campanha", depende=None,
              criterio=None, restricao=None)
checar("conceito/job", "CONCEITO" in msg, msg or "job para o Gestor de Tráfego foi aceito")

rodar(demanda.cmd_job_add, demanda=did, agente="copywriter", objetivo="copy dos 2 criativos",
      entrada=None, saida="primary text + headline", depende=None, criterio=None, restricao=None)
rodar(demanda.cmd_job_add, demanda=did, agente="designer", objetivo="2 peças",
      entrada=None, saida="2 PNG", depende=["JOB-001"], criterio=None, restricao=None)

# REQUEST_CHECKLIST: todo requisito tem dono.
rodar(demanda.cmd_requisito_add, demanda=did, texto="2 criativos para Meta Ads",
      dono="designer", job="JOB-002")
rodar(demanda.cmd_requisito_add, demanda=did, texto="copy dos criativos",
      dono="copywriter", job="JOB-001")
msg = erro_de(rodar, demanda.cmd_requisito_add, demanda=did, texto="qualquer coisa",
              dono="quem-nao-existe", job=None)
checar("checklist/dono", "não existe" in msg, msg or "dono inventado foi aceito")

d = modelo.carregar(did)
checar("gate/bloqueia", bool(demanda.avaliar_gate(d)), "gate liberou com tudo pendente")

# O briefing carrega o contrato inteiro: silêncio e requisitos do job.
rodar(demanda.cmd_briefing, demanda=did, job="JOB-001", json=True, forcar=False)
b = modelo.ler_json(modelo.dir_demanda(did) / "handoffs" / "JOB-001.briefing.json")
checar("briefing/silent", b.get("execution_mode") == "SILENT")
checar("briefing/requisitos", any("copy dos criativos" in r for r in b.get("requisitos", [])),
       str(b.get("requisitos")))
checar("briefing/schema", not modelo.validar(b, "briefing"))

# O pedido original não se reescreve.
d = modelo.carregar(did)
d["descricao"] = "resumo do pedido"
checar("original/imutavel", "imutável" in erro_de(modelo.salvar, d))

# Alteração entra ao lado, e o original continua.
rodar(demanda.cmd_alteracao, demanda=did, texto="agora são 3 criativos", afeta=["REQ-001"])
d = modelo.carregar(did)
checar("alteracao", d["descricao"] == PEDIDO and len(d["alteracoes"]) == 1)

# CUMPRIDO sem evidência não passa — 'provavelmente cumprido' não existe.
msg = erro_de(rodar, demanda.cmd_requisito_estado, demanda=did, requisito="REQ-001",
              estado="cumprido", evidencia=None, motivo=None)
checar("checklist/evidencia", "evidencia" in msg.lower() or "evidência" in msg.lower(), msg)

for jid, agente in (("JOB-001", "copywriter"), ("JOB-002", "designer")):
    rodar(demanda.cmd_job_iniciar, demanda=did, job=jid)
    rodar(demanda.cmd_job_concluir, demanda=did, job=jid, retorno=None, status="concluido",
          resumo="pronto", artefato=[f"{TMP}/{jid}.txt"], decisao=None, observacao=None,
          proximo=None, pendencia=None)

d = modelo.carregar(did)
trava = demanda.avaliar_gate(d)
checar("gate/requisito-pendente", bool(trava), "gate liberou com requisito pendente")
checar("gate/jobs-ok", not any("JOB-" in x for x in trava), str(trava))

rodar(demanda.cmd_requisito_estado, demanda=did, requisito="REQ-001", estado="cumprido",
      evidencia="JOB-002 · 3 PNG", motivo=None)
rodar(demanda.cmd_requisito_estado, demanda=did, requisito="REQ-002", estado="cumprido",
      evidencia="JOB-001", motivo=None)

d = modelo.carregar(did)
checar("gate/libera", not demanda.avaliar_gate(d), str(demanda.avaliar_gate(d)))
checar("concluir", rodar(demanda.cmd_concluir, demanda=did, motivo="") == 0)
checar("concluir/status", modelo.carregar(did)["status"] == "CONCLUIDA")

# Uma demanda incompleta não fecha, por mais que os jobs tenham sido aprovados.
rodar(demanda.cmd_nova, cliente="outro-cliente", titulo="Incompleta",
      descricao="5 criativos", objetivo="", contexto="", prioridade="normal")
outro = modelo.listar()[0]["id"]
rodar(demanda.cmd_planejar, demanda=outro, plano="arte")
rodar(demanda.cmd_requisito_add, demanda=outro, texto="5 criativos", dono="designer", job=None)
checar("concluir/incompleta", rodar(demanda.cmd_concluir, demanda=outro, motivo="") == 2)
checar("isolamento", modelo.carregar(outro)["cliente"] == "outro-cliente"
       and modelo.carregar(did)["cliente"] == "cliente-teste")

# ------------------------------------------------------------ 4 · leitor do roster

try:
    import yaml                                             # só se existir na máquina
    ref = yaml.safe_load(roster.ARQUIVO.read_text(encoding="utf-8"))
    meu = roster.carregar()
    for r, m in zip(ref["agentes"], meu["agentes"]):
        for campo in ("id", "agente", "prompt", "subagent_type", "capabilities", "skills"):
            esperado = r.get(campo) or ([] if campo in roster.LISTAS else None)
            checar("roster/parser", esperado == m.get(campo), f"{r['id']}.{campo}")
except ImportError:
    pass

# ------------------------------------------------------------ veredito

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"\nteste-roteamento: {len(CENARIOS)} cenários e o contrato completo · OK")
sys.exit(0)
