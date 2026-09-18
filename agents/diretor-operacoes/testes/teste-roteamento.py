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

from engine import auditoria, demanda, entrega_pdf, modelo, policy, roster   # noqa: E402

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
checar("auditoria/sem-bloqueio", not _notas, "; ".join(_notas))
checar("auditoria/seis", len(modelo.agentes_acionaveis()) == 6, str(modelo.agentes_acionaveis()))
checar("auditoria/gestor", "gestor-de-trafego" in modelo.agentes_acionaveis())

# Repositório íntegro não quer dizer squad acionável: numa máquina onde o setup.sh
# nunca rodou, nenhum agente chega ao Claude Code. Auditar só o repositório e dizer
# "VALIDADO" já fez o Diretor prometer acionamento que a máquina não tinha.
_home_vazio = pathlib.Path(TMP) / "claude-home-vazio"
_home_vazio.mkdir(parents=True, exist_ok=True)
_pendencias, _linhas_maquina = auditoria.instalacao(_home_vazio)
checar("instalacao/vazia", len(_pendencias) == 8, f"{len(_pendencias)} pendências, esperado 8: âncora + 7 agentes")
checar("instalacao/ancora", any("âncora" in x for x in _pendencias))
checar("instalacao/linhas", len(_linhas_maquina) == 8, str(len(_linhas_maquina)))

_home_cheio = pathlib.Path(TMP) / "claude-home-cheio"
(_home_cheio / "agents").mkdir(parents=True, exist_ok=True)
(_home_cheio / "squad-nk").symlink_to(roster.REPO)
for _a in roster.agentes():
    if _a.get("subagent_type"):
        (_home_cheio / "agents" / f"{_a['subagent_type']}.md").write_text("", encoding="utf-8")
checar("instalacao/completa", auditoria.instalacao(_home_cheio)[0] == [],
       "; ".join(auditoria.instalacao(_home_cheio)[0]))

# A regra do agente-conceito continua valendo para quem entrar amanhã, e é testada
# contra um roster de mentira — o roster real não tem nenhum hoje.
_falso = pathlib.Path(TMP) / "roster-conceito.yaml"
_falso.write_text('''agentes:
  - id: fulano
    nome: "Fulano"
    papel: especialista
    emoji: "🧪"
    agente: conceito
    prompt: null
    subagent_type: null
    capabilities: [teste.coisa]
''', encoding="utf-8")
checar("conceito/roster", roster.acionaveis(_falso) == [], str(roster.acionaveis(_falso)))
checar("conceito/roster", roster.conceitos(_falso)[0]["id"] == "fulano")

# ------------------------------------------------------------ 3 · ensaio do contrato

PEDIDO = "Quero 2 criativos para Meta Ads do implante unitário, com copy e revisão."
did = None


def rodar(fn, **kw) -> int:
    return fn(Args(**kw))


rodar(demanda.cmd_nova, cliente="cliente-teste", titulo="Ensaio", descricao=PEDIDO,
      objetivo="testar o contrato", contexto="", prioridade="normal")
did = modelo.listar()[0]["id"]

rodar(demanda.cmd_planejar, demanda=did, plano="copy -> arte -> revisão")

# Agente que não existe não recebe job — nem por engano de grafia.
msg = erro_de(rodar, demanda.cmd_job_add, demanda=did, agente="gestor-trafego",
              objetivo="subir campanha", entrada=None, saida="campanha", depende=None,
              criterio=None, restricao=None)
checar("job/agente-inexistente", "não é acionável" in msg, msg or "id do roster foi aceito como agente")

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

# ------------------------------------- 3b · teste seco DIRETOR -> GESTOR DE TRÁFEGO

# Prova que o Gestor recebe job real, briefing completo e devolve retorno ao Diretor —
# sem tocar em conta de anúncios, sem publicar e sem gastar. Nada aqui executa ação externa.
rodar(demanda.cmd_nova, cliente="cliente-trafego", titulo="Ensaio de tráfego",
      descricao="Analise a conta e diga se escalo a campanha de implante.",
      objetivo="decidir escala", contexto="", prioridade="normal")
dt = modelo.listar()[0]["id"]
rodar(demanda.cmd_planejar, demanda=dt, plano="gestor analisa e recomenda")
rodar(demanda.cmd_job_add, demanda=dt, agente="gestor-de-trafego",
      objetivo="diagnóstico da conta e recomendação de escala", entrada=None,
      saida="parecer com evidência", depende=None, criterio=None,
      restricao=["não executar ação na conta"])
rodar(demanda.cmd_requisito_add, demanda=dt, texto="parecer sobre escalar ou não",
      dono="gestor-de-trafego", job="JOB-001")

rodar(demanda.cmd_briefing, demanda=dt, job="JOB-001", json=True, forcar=False)
bt = modelo.ler_json(modelo.dir_demanda(dt) / "handoffs" / "JOB-001.briefing.json")
checar("gestor/briefing", bt["agente"] == "gestor-de-trafego", bt["agente"])
checar("gestor/briefing", bt.get("execution_mode") == "SILENT")
checar("gestor/briefing", any("parecer" in r for r in bt.get("requisitos", [])), str(bt.get("requisitos")))
checar("gestor/briefing", not modelo.validar(bt, "briefing"))

# Retorno do especialista, registrado pelo Diretor. Ele recomenda; não executa.
rodar(demanda.cmd_job_iniciar, demanda=dt, job="JOB-001")
rodar(demanda.cmd_job_concluir, demanda=dt, job="JOB-001", retorno=None,
      status="precisa_de_aprovacao", resumo="recomenda escalar 20% no conjunto A",
      artefato=[f"{TMP}/parecer.md"], decisao=["escala depende de aprovação"],
      observacao=None, proximo="levar ao portão",
      pendencia="subir orçamento exige aprovação humana")
d = modelo.carregar(dt)
j = modelo.achar_job(d, "JOB-001")
checar("gestor/retorno", j["status"] == "AGUARDANDO_APROVACAO", j["status"])
checar("gestor/retorno", j["resultado"]["resumo"].startswith("recomenda"))

# A trava financeira continua de pé: integrar ao motor não autoriza gasto.
for acao in ("subir a campanha no meta ads", "aumentar o orcamento da campanha",
             "ativar o conjunto de anuncios"):
    checar("gestor/policy", policy.classificar(acao)["classe"] == "REQUER_APROVACAO", acao)
checar("gestor/aprovacao",
       rodar(demanda.cmd_aprovacao_solicitar, demanda=dt,
             acao="subir a campanha no meta ads", job="JOB-001") == 2)
d = modelo.carregar(dt)
ap = d["aprovacoes"][0]
checar("gestor/aprovacao", ap["status"] == "PENDENTE", ap["status"])
checar("gestor/gate", any(ap["id"] in x for x in demanda.avaliar_gate(d)),
       "aprovação pendente não barrou o fechamento")

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

# ------------------------------------------------------------ 5 · motor de entrega em PDF

# O conversor é próprio: o que ele precisa aguentar é o markdown que o especialista
# escreve numa entrega. Tabela de três trilhas, lista de ganchos e negrito.
_html = entrega_pdf.converter("""## Roteiro 1 · Confiança

Ângulo: **prova** com endereço.

### Variantes de gancho

1. Pergunte onde fica a fábrica.
- item solto

| Tempo | Fala |
|---|---|
| 0-3s | Pergunte onde fica. |

| | |
|---|---|
| Cliente | Toraflex |
""".split("\n"))
checar("entrega-pdf/quebra", '<h2 class="quebra">Roteiro 1' in _html, _html[:120])
checar("entrega-pdf/negrito", "<strong>prova</strong>" in _html)
checar("entrega-pdf/ol", "<ol>" in _html and "<ul>" in _html)
checar("entrega-pdf/tabela", _html.count("<table>") == 2, str(_html.count("<table>")))
checar("entrega-pdf/thead", _html.count("<thead>") == 1,
       "tabela sem cabeçalho não pode virar faixa vazia")
checar("entrega-pdf/escape", "&" not in entrega_pdf.inline("a < b") or
       "&lt;" in entrega_pdf.inline("a < b"))

# Regra 2: entrega é dado de cliente e não pode ser gravada dentro do repositório.
_md = pathlib.Path(TMP) / "entrega.md"
_md.write_text("# Peça\n\nlinha\n", encoding="utf-8")
checar("entrega-pdf/trava-git",
       entrega_pdf.main([str(_md), "-o", str(roster.REPO / "peca.pdf")]) == 2,
       "o motor aceitou gravar entrega dentro do repositório")
checar("entrega-pdf/trava-git", not (roster.REPO / "peca.pdf").exists())

# ------------------------------------------------------------ veredito

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"\nteste-roteamento: {len(CENARIOS)} cenários de roteamento, o teste seco "
      "DIRETOR -> GESTOR DE TRÁFEGO e o contrato completo · OK")
sys.exit(0)
