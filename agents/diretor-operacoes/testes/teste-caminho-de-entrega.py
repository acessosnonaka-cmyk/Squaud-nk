#!/usr/bin/env python3
"""Testes adversariais do caminho de entrega — as invariantes F1, F2, F3 e F7.

Não testam o caminho feliz de bom humor: cada bloco tenta furar o motor pelo
buraco que a auditoria de integridade encontrou de verdade, e falha se o motor
deixar passar.

O que está sob teste, em uma frase cada:

  F1  job com dependência aberta não inicia nem conclui
  F2  peça não entra na área de entrega sem inspeção e parecer persistidos
  F3  demanda não sai para o gestor sem fechamento formal do Diretor
  F7  "liberou" só nomeia quem este job realmente destravou

Roda inteiro em diretórios temporários: nenhum dado de cliente, nenhuma ação
externa, nenhum especialista acionado.

    python3 agents/diretor-operacoes/testes/teste-caminho-de-entrega.py
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

RAIZ = pathlib.Path(__file__).resolve().parents[1]
REPO = RAIZ.parents[1]
sys.path.insert(0, str(RAIZ))

TMP = tempfile.mkdtemp(prefix="squad-nk-entrega-")
os.environ["SQUAD_DATA_HOME"] = TMP

from engine import demanda, modelo   # noqa: E402

falhas = []
feitos = []


def checar(nome: str, condicao: bool, detalhe: str = "") -> None:
    feitos.append(nome)
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def roda(fn, **kw):
    """Executa um comando do CLI capturando a saída. Devolve (exit, texto)."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = fn(Args(**kw))
    except modelo.ErroDeEstado as exc:
        return None, str(exc)
    return code, buf.getvalue()


def nova_demanda(titulo: str, descricao: str) -> str:
    code, saida = roda(demanda.cmd_nova, titulo=titulo, cliente="cliente-ficticio-teste",
                       descricao=descricao, objetivo="prova de invariante",
                       contexto="", prioridade="normal", fonte=None)
    return saida.strip().split()[-1]


# ============================================================ F1 · A e B
# JOB-002 depende de JOB-001. O grafo tem de ser trava nos dois comandos que
# movem estado, não só na listagem de elegíveis.

dem = nova_demanda("Dependência é trava", "quero a legenda e a arte")
roda(demanda.cmd_planejar, demanda=dem, plano="copy, depois arte")
roda(demanda.cmd_job_add, demanda=dem, agente="copywriter", objetivo="escrever a legenda",
     entrada=None, saida=None, depende=None, criterio=None, restricao=None, fonte=None)
roda(demanda.cmd_job_add, demanda=dem, agente="designer", objetivo="montar a arte",
     entrada=None, saida=None, depende=["JOB-001"], criterio=None, restricao=None, fonte=None)

code, msg = roda(demanda.cmd_job_iniciar, demanda=dem, job="JOB-002")
checar("A · iniciar job com dependência aberta é barrado", code is None, f"exit={code}")
checar("A · a recusa nomeia o job solicitado", "JOB-002" in msg, msg[:90])
checar("A · a recusa nomeia a dependência aberta e o estado dela",
       "JOB-001" in msg and "PENDENTE" in msg, msg[:140])

code, msg = roda(demanda.cmd_job_concluir, demanda=dem, job="JOB-002", retorno=None,
                 status="concluido", resumo="arte furando a fila", artefato=None,
                 decisao=None, observacao=None, proximo=None, pendencia=None)
checar("B · concluir job com dependência aberta é barrado", code is None, f"exit={code}")
checar("B · o job não mudou de estado",
       modelo.achar_job(modelo.carregar(dem), "JOB-002")["status"] == "PENDENTE")

# ============================================================ F7 · liberação verdadeira
# Ao concluir JOB-001, só JOB-002 foi destravado por ele. JOB-003, que não
# depende de ninguém, já estava elegível e não pode aparecer como "liberou".

roda(demanda.cmd_job_add, demanda=dem, agente="lp-builder", objetivo="job independente",
     entrada=None, saida=None, depende=None, criterio=None, restricao=None, fonte=None)
roda(demanda.cmd_job_iniciar, demanda=dem, job="JOB-001")
code, saida = roda(demanda.cmd_job_concluir, demanda=dem, job="JOB-001", retorno=None,
                   status="concluido", resumo="legenda escrita", artefato=None,
                   decisao=None, observacao=None, proximo=None, pendencia=None)
linha = next((l for l in saida.splitlines() if "liberou" in l), "")
checar("F7 · liberou nomeia quem este job destravou", "JOB-002" in linha, linha or "(sem linha)")
checar("F7 · liberou não nomeia job que já estava elegível", "JOB-003" not in linha, linha)

# agora JOB-002 pode andar, porque a dependência fechou de verdade
code, _ = roda(demanda.cmd_job_iniciar, demanda=dem, job="JOB-002")
checar("F1 · com a dependência fechada, o job inicia normalmente", code == 0, f"exit={code}")

# ============================================================ F3 · E, G, H
# E — demanda não fecha com job obrigatório pendente.
# G — entrega barrada com demanda PLANEJADA/EM_EXECUCAO.
# H — especialista e Revisor prontos, Diretor ainda não liberou.

code, _ = roda(demanda.cmd_concluir, demanda=dem, motivo="")
checar("E · concluir demanda com job pendente é barrado", code == 2, f"exit={code}")

code, msg = roda(demanda.cmd_entregar, demanda=dem)
checar("G · entregar com demanda EM_EXECUCAO é barrado", code == 2, f"exit={code}")
checar("G · a recusa diz que o Diretor não liberou", "não CONCLUIDA" in msg or "CONCLUIDA" in msg,
       msg[:120])

d = modelo.carregar(dem)
checar("G · nada foi registrado como entregue", not d.get("entregue_em"))

# ============================================================ F3 · F
# Peça visual concluída sem job de Revisor ligado a ela: o gate trava.

dem2 = nova_demanda("Revisão obrigatória", "quero uma arte de feed")
roda(demanda.cmd_planejar, demanda=dem2, plano="só a arte")
roda(demanda.cmd_job_add, demanda=dem2, agente="designer", objetivo="montar a arte",
     entrada=None, saida=None, depende=None, criterio=None, restricao=None, fonte=None)
roda(demanda.cmd_requisito_add, demanda=dem2, texto="uma arte de feed", dono="designer", job="JOB-001")
roda(demanda.cmd_job_iniciar, demanda=dem2, job="JOB-001")
roda(demanda.cmd_job_concluir, demanda=dem2, job="JOB-001", retorno=None, status="concluido",
     resumo="arte pronta", artefato=["/tmp/peca-ficticia.png"], decisao=None,
     observacao=None, proximo=None, pendencia=None)
roda(demanda.cmd_requisito_estado, demanda=dem2, requisito="REQ-001", estado="cumprido",
     evidencia="arte entregue", motivo=None)

trava = demanda.avaliar_gate(modelo.carregar(dem2))
checar("F · peça sem job de Revisor trava o gate",
       any("revisão obrigatória ausente" in t for t in trava), str(trava))
code, _ = roda(demanda.cmd_concluir, demanda=dem2, motivo="")
checar("F · e a demanda não fecha", code == 2, f"exit={code}")

# com o Revisor no grafo, mas ainda não concluído, continua travado
roda(demanda.cmd_job_add, demanda=dem2, agente="revisor-de-criacao", objetivo="parecer da arte",
     entrada=None, saida=None, depende=["JOB-001"], criterio=None, restricao=None, fonte=None)
trava = demanda.avaliar_gate(modelo.carregar(dem2))
checar("F · Revisor no grafo mas não concluído continua travando",
       any("revisão não terminou" in t for t in trava), str(trava))

# ============================================================ F3 · I e J
# I — tudo concluído, mas o Diretor barra por requisito reaberto.
# J — fluxo completo legítimo chega até a entrega.

roda(demanda.cmd_job_iniciar, demanda=dem2, job="JOB-002")
roda(demanda.cmd_job_concluir, demanda=dem2, job="JOB-002", retorno=None, status="concluido",
     resumo="parecer: aprovado", artefato=["/tmp/parecer.md"], decisao=None,
     observacao=None, proximo=None, pendencia=None)
roda(demanda.cmd_requisito_add, demanda=dem2, texto="parecer do Revisor registrado",
     dono="revisor-de-criacao", job="JOB-002")

# I · o Diretor reabre um requisito porque o artefato não bate com o pedido
roda(demanda.cmd_requisito_estado, demanda=dem2, requisito="REQ-001", estado="pendente",
     evidencia=None, motivo="artefato diverge do pedido original")
code, _ = roda(demanda.cmd_concluir, demanda=dem2, motivo="")
checar("I · Diretor barra material que os especialistas já aprovaram", code == 2, f"exit={code}")
code, _ = roda(demanda.cmd_entregar, demanda=dem2)
checar("I · e a entrega continua barrada", code == 2, f"exit={code}")

# H · com tudo concluído mas a demanda ainda aberta, a entrega não sai
roda(demanda.cmd_requisito_estado, demanda=dem2, requisito="REQ-001", estado="cumprido",
     evidencia="arte confere com o pedido", motivo=None)
roda(demanda.cmd_requisito_estado, demanda=dem2, requisito="REQ-002", estado="cumprido",
     evidencia="parecer em /tmp/parecer.md", motivo=None)
d = modelo.carregar(dem2)
checar("H · jobs e revisão concluídos, demanda ainda não liberada",
       d["status"] != "CONCLUIDA", d["status"])
code, _ = roda(demanda.cmd_entregar, demanda=dem2)
checar("H · especialista + Revisor prontos não substituem o Diretor", code == 2, f"exit={code}")

# J · agora sim: o Diretor fecha, e só então a entrega sai
code, _ = roda(demanda.cmd_concluir, demanda=dem2, motivo="")
checar("J · com tudo em ordem o Diretor fecha", code == 0, f"exit={code}")
code, msg = roda(demanda.cmd_entregar, demanda=dem2)
checar("J · e a entrega é liberada", code == 0, f"exit={code}")
checar("J · a liberação registra os artefatos", "/tmp/peca-ficticia.png" in msg, msg[:160])
checar("J · e fica gravada em disco", bool(modelo.carregar(dem2).get("entregue_em")))

# ============================================================ F3 · CONCLUIDA não se fabrica

d = modelo.carregar(dem)                       # esta ainda tem job aberto
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        demanda._mudar_status(Args(demanda=dem, motivo=""), "CONCLUIDA")
    fabricou, msg = True, buf.getvalue()
except modelo.ErroDeEstado as exc:
    fabricou, msg = False, str(exc)
checar("F3 · CONCLUIDA não pode ser aplicada por fora do gate",
       not fabricou and "não pode ir para CONCLUIDA" in msg, msg[:110])
checar("F3 · e a demanda continua no estado anterior",
       modelo.carregar(dem)["status"] != "CONCLUIDA")

# ============================================================ F2 · C e D
# O motor do art-builder: peça só entra em output/ com inspeção e parecer.

ART = REPO / "agents" / "design-ia" / "engine"
JOBPY = ART / "job.py"


def art(*args):
    r = subprocess.run([sys.executable, str(JOBPY), *args], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


if JOBPY.is_file():
    casa = tempfile.mkdtemp(prefix="squad-nk-art-")
    jdir = pathlib.Path(casa) / "job-teste"
    jdir.mkdir()
    (jdir / "job.json").write_text(json.dumps({
        "job_id": "teste", "client": "cliente-ficticio-teste", "name": "peca de teste",
        "status": "aberto", "cycle": 1, "max_cycles": 3,
        "versions": [{"version": 1, "png": str(jdir / "v1.png"), "em": "2026-01-01T00:00:00"}],
    }, ensure_ascii=False), encoding="utf-8")
    (jdir / "v1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)

    saida_dir = ART / "output" / "cliente-ficticio-teste"
    antes = set(saida_dir.glob("*")) if saida_dir.is_dir() else set()

    code, msg = art("finalize", "--job", str(jdir), "--version", "1", "--status", "aprovada")
    checar("C · finalizar como aprovada sem inspeção é barrado", code != 0, f"exit={code}")
    checar("C · a recusa nomeia a inspeção ausente", "inspecao" in msg.lower(), msg[:120])
    depois = set(saida_dir.glob("*")) if saida_dir.is_dir() else set()
    checar("C · nenhum arquivo novo entrou na área de entrega", antes == depois,
           str(depois - antes))

    code, msg = art("finalize", "--job", str(jdir), "--version", "1", "--status", "aprovada",
                    "--note", "aprovado")
    checar("D · nota_final dizendo 'aprovado' não vale como evidência", code != 0, f"exit={code}")
    depois = set(saida_dir.glob("*")) if saida_dir.is_dir() else set()
    checar("D · e nada foi copiado", antes == depois, str(depois - antes))

    # inspecionada, mas ainda sem parecer do Revisor
    art("inspecionar", "--job", str(jdir), "--version", "1", "--veredito", "ok",
        "--parecer", "abri a prancha: composicao centralizada, hierarquia legivel, "
                     "acabamento limpo, nada cortado nas margens")
    code, msg = art("finalize", "--job", str(jdir), "--version", "1", "--status", "aprovada")
    checar("C · inspecionada mas sem parecer continua barrada", code != 0, f"exit={code}")
    checar("C · a recusa nomeia o parecer ausente", "parecer" in msg.lower(), msg[:120])

    # parecer REPROVADO não libera
    rep = pathlib.Path(casa) / "reprovado.md"
    rep.write_text("# Parecer\n\nREPROVADO. A peca falha no piso de suficiencia.\n", encoding="utf-8")
    art("save-review", "--job", str(jdir), "--version", "1", "--file", str(rep))
    code, msg = art("finalize", "--job", str(jdir), "--version", "1", "--status", "aprovada")
    checar("C · parecer REPROVADO não deixa a peça entrar em output/", code != 0, f"exit={code}")
    depois = set(saida_dir.glob("*")) if saida_dir.is_dir() else set()
    checar("C · e nada foi copiado mesmo assim", antes == depois, str(depois - antes))

    # parecer sem status legível é recusado na origem
    vago = pathlib.Path(casa) / "vago.md"
    vago.write_text("# Parecer\n\nAchei a peca interessante.\n", encoding="utf-8")
    code, msg = art("save-review", "--job", str(jdir), "--version", "1", "--file", str(vago))
    checar("D · parecer sem status legível é recusado", code != 0, f"exit={code}")

    # caminho legítimo: inspeção ok + parecer APROVADO
    ok = pathlib.Path(casa) / "aprovado.md"
    ok.write_text("# Parecer\n\nAPROVADO. Quatro estrelas, sem falha critica.\n", encoding="utf-8")
    art("save-review", "--job", str(jdir), "--version", "1", "--file", str(ok))
    code, msg = art("finalize", "--job", str(jdir), "--version", "1", "--status", "aprovada")
    checar("J · com inspeção e parecer aprovando, a peça é entregue", code == 0, f"{code} {msg[:120]}")
    depois = set(saida_dir.glob("*")) if saida_dir.is_dir() else set()
    checar("J · e o arquivo aparece na área de entrega", len(depois - antes) == 1, str(depois - antes))

    # status que não é entrega não copia nada
    jdir2 = pathlib.Path(casa) / "job-parado"
    shutil.copytree(jdir, jdir2)
    antes2 = set(saida_dir.glob("*"))
    code, _ = art("finalize", "--job", str(jdir2), "--version", "1", "--status", "parada")
    checar("C · status que não é entrega não exige parecer", code == 0, f"exit={code}")
    checar("C · e não copia arquivo para a área de entrega",
           set(saida_dir.glob("*")) == antes2)

    for p in set(saida_dir.glob("*")) - antes:
        p.unlink()
    if saida_dir.is_dir() and not any(saida_dir.iterdir()):
        saida_dir.rmdir()
    shutil.rmtree(casa, ignore_errors=True)
else:
    falhas.append("F2 · job.py do art-builder não encontrado")

# ============================================================ F3 · barreira de turno
# O hook Stop é a trava que a sessão não contorna: demanda executada e não
# liberada não deixa o turno fechar. A assinatura tem de ser estreita, senão o
# hook vira ruído e ensina a ignorá-lo.

import datetime as _dt   # noqa: E402

HOOK = REPO / "scripts" / "hook-stop.py"
AGORA = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
ANTIGO = (_dt.datetime.now().astimezone() - _dt.timedelta(hours=40)).isoformat(timespec="seconds")


def acervo(status, estados_de_job, *, concluida_em=None, quando=AGORA):
    casa = tempfile.mkdtemp(prefix="squad-nk-hook-")
    dd = pathlib.Path(casa) / "diretor" / "demandas" / "DEM-20260101-001"
    dd.mkdir(parents=True)
    (dd / "demanda.json").write_text(json.dumps({
        "id": "DEM-20260101-001", "status": status, "cliente": "cliente-ficticio-teste",
        "descricao": "pedido", "criada_em": quando, "atualizada_em": quando,
        "concluida_em": concluida_em,
        "jobs": [{"id": f"JOB-00{i+1}", "agente": "copywriter", "status": s}
                 for i, s in enumerate(estados_de_job)],
    }, ensure_ascii=False), encoding="utf-8")
    return casa


def hook(casa, *, ativo=False):
    r = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps({"last_assistant_message": "Aqui está a entrega.",
                                         "stop_hook_active": ativo}),
                       capture_output=True, text=True,
                       env=dict(os.environ, SQUAD_DATA_HOME=casa))
    saida = (r.stdout or "").strip()
    if not saida:
        return "PASSOU"
    return ("BLOQUEOU" if json.loads(saida)["hookSpecificOutput"].get("decision") == "block"
            else "PASSOU")


if HOOK.is_file():
    CASOS_HOOK = [
        ("G · turno não fecha com demanda executada e PLANEJADA",
         acervo("PLANEJADA", ["CONCLUIDO"]), "BLOQUEOU"),
        ("G · nem com ela EM_EXECUCAO",
         acervo("EM_EXECUCAO", ["CONCLUIDO", "CONCLUIDO"]), "BLOQUEOU"),
        ("J · demanda CONCLUIDA deixa o turno fechar",
         acervo("CONCLUIDA", ["CONCLUIDO"], concluida_em=AGORA), "PASSOU"),
        ("G · bloqueio declarado é escape legítimo",
         acervo("BLOQUEADA", ["CONCLUIDO"]), "PASSOU"),
        ("G · job ainda pendente é trabalho em curso, não entrega represada",
         acervo("EM_EXECUCAO", ["CONCLUIDO", "PENDENTE"]), "PASSOU"),
        ("G · plano sem job não casa",
         acervo("PLANEJADA", []), "PASSOU"),
        ("G · demanda velha não trava o turno para sempre",
         acervo("PLANEJADA", ["CONCLUIDO"], quando=ANTIGO), "PASSOU"),
        ("G · repositório sem acervo não trava nada",
         tempfile.mkdtemp(prefix="squad-nk-vazio-"), "PASSOU"),
    ]
    for nome, casa, esperado in CASOS_HOOK:
        checar(nome, hook(casa) == esperado, f"veio {hook(casa)}, esperado {esperado}")
        shutil.rmtree(casa, ignore_errors=True)

    casa = acervo("PLANEJADA", ["CONCLUIDO"])
    checar("G · segunda passada do mesmo turno sempre sai",
           hook(casa, ativo=True) == "PASSOU")
    shutil.rmtree(casa, ignore_errors=True)
else:
    falhas.append("F3 · hook-stop.py não encontrado")

shutil.rmtree(TMP, ignore_errors=True)

# ------------------------------------------------------------------ veredito

if falhas:
    print(f"\n{len(falhas)} FALHA(S) em {len(feitos)} checagens")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"\nteste-caminho-de-entrega: {len(feitos)} checagens adversariais "
      "(F1 dependências, F2 entrega visual, F3 fechamento, F7 liberação) · OK")
sys.exit(0)
