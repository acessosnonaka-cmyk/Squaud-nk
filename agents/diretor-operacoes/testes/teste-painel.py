#!/usr/bin/env python3
"""O painel diz a verdade sobre quem trabalhou — ou nao diz nada.

Tres coisas que se pareciam e agora sao separadas por prova em disco:

  CRIADO     existe job para o especialista. Ninguem foi acionado ainda.
  DISPARADO  a sessao chamou `job iniciar`: o Agent esta rodando agora.
  EXECUTADO  o retorno do Agent esta em handoffs/<JOB>.retorno.json.

E duas que o painel nao consegue fazer, por construcao — que e o ponto:
especialista sem job nao tem linha, e skill nao aparece, porque skill nao cria
job e o painel le job.

    python3 agents/diretor-operacoes/testes/teste-painel.py [-v]
"""
from __future__ import annotations

import io
import os
import pathlib
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

TMP = tempfile.mkdtemp(prefix="squad-nk-painel-")
os.environ["SQUAD_DATA_HOME"] = TMP

from engine import demanda, modelo   # noqa: E402

falhas, feitos = [], []
VERBOSE = "-v" in sys.argv


def checar(nome: str, ok: bool, detalhe: str = "") -> None:
    feitos.append(nome)
    if not ok:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")
    if VERBOSE:
        print(f"  {'ok   ' if ok else 'FALHA'} {nome}")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def roda(fn, **kw):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = fn(Args(**kw))
    except modelo.ErroDeEstado as exc:
        return None, str(exc)
    return code, buf.getvalue()


def _sem_acento(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c))


def nova(titulo: str) -> str:
    _, saida = roda(demanda.cmd_nova, titulo=titulo, cliente="cliente-painel-teste",
                    descricao="quero material de marketing", objetivo="testar o painel",
                    contexto="", prioridade="normal", fonte=None)
    return saida.strip().split()[-1]


def add_job(dem, agente, depende=None):
    return roda(demanda.cmd_job_add, demanda=dem, agente=agente, objetivo="fazer a coisa",
                entrada=None, saida="um artefato", depende=depende, criterio=None,
                restricao=None, fonte=None)


def painel(dem):
    return roda(demanda.cmd_painel, demanda=dem, verificar=False)[1]


# ============================================================ P1 · job criado
dem = nova("Painel diz a verdade")
roda(demanda.cmd_planejar, demanda=dem, plano="copy e arte")
add_job(dem, "copywriter")

texto = painel(dem)
checar("P1 · job criado aparece, mas NAO como trabalhando",
       "COPYWRITER" in texto and "TRABALHANDO" not in texto, texto)
checar("P1 · job criado aparece como NA FILA", "NA FILA" in texto, texto)

# ============================================================ P2 · disparado
roda(demanda.cmd_job_iniciar, demanda=dem, job="JOB-001")
texto = painel(dem)
checar("P2 · job iniciado aparece como TRABALHANDO", "TRABALHANDO" in texto, texto)

# ============================================================ P3 · executado
roda(demanda.cmd_job_concluir, demanda=dem, job="JOB-001", retorno=None,
     status="concluido", resumo="copy escrita", artefato=None, decisao=None,
     observacao=None, proximo=None, pendencia=None)
texto = painel(dem)
checar("P3 · job com retorno em disco aparece como CONCLUIDO",
       "CONCLUÍDO" in texto, texto)

retorno = modelo.dir_demanda(dem) / "handoffs" / "JOB-001.retorno.json"
checar("P3 · a prova do Agent executado e o retorno em disco", retorno.is_file())

# ============================================================ P4 · sem a prova, sem a afirmacao
guardado = retorno.read_text(encoding="utf-8")
retorno.unlink()
d = modelo.carregar(dem)
checar("P4 · sem retorno em disco o job nao conta como EXECUTADO",
       demanda.evidencia_do_job(dem, modelo.achar_job(d, "JOB-001")) != "EXECUTADO")
retorno.write_text(guardado, encoding="utf-8")

# ============================================================ P5 · especialista sem job
texto = painel(dem)
for ausente in ("DESIGNER", "LP BUILDER", "LEGEND IA", "GESTOR DE TRÁFEGO"):
    checar(f"P5 · {ausente} nao aparece: nao tem job", ausente not in texto, texto)

# ============================================================ P6 · skill nao e Agent
# Duas camadas, e a primeira e a mais forte: o motor nao deixa nem criar o job.
code, msg = add_job(dem, "humanizer")
checar("P6 · skill nao recebe job: o motor recusa antes de existir",
       code is None and "nao e acionavel" in _sem_acento(msg), (msg or "")[:120])
checar("P6 · a recusa lista quem e acionavel de verdade",
       "copywriter" in (msg or "") and "gestor-de-trafego" in (msg or ""), (msg or "")[:160])

# Segunda camada: ainda que um job de nao-agente existisse (json editado a mao),
# o painel nao o transforma em linha.
d_forjada = modelo.carregar(dem)
d_forjada["jobs"].append({"id": "JOB-999", "agente": "humanizer", "status": "EM_EXECUCAO",
                          "objetivo": "forjado", "dependencias": [], "tentativas": 1,
                          "resultado": None})
modelo.salvar(d_forjada)
texto = painel(dem)
checar("P6 · job forjado de nao-agente nao vira linha no painel",
       "HUMANIZER" not in texto.upper(), texto)
_, verif = roda(demanda.cmd_painel, demanda=dem, verificar=True)
checar("P6 · e a verificacao declara quem ficou de fora",
       "FORA DO ROSTER" in verif and "humanizer" in verif, verif)
d_forjada = modelo.carregar(dem)
d_forjada["jobs"] = [j for j in d_forjada["jobs"] if j["id"] != "JOB-999"]
modelo.salvar(d_forjada)

# ============================================================ P7 · demanda sem job
vazia = nova("Demanda sem especialista")
texto = painel(vazia)
checar("P7 · demanda sem job nao tem painel", "SEM PAINEL" in texto, texto)
checar("P7 · e diz por que", "simulação" in texto or "simulacao" in texto, texto)

# ============================================================ P8 · o painel fica registrado
d = modelo.carregar(dem)
checar("P8 · painel renderizado fica gravado na demanda",
       len(d.get("paineis", [])) >= 1, str(d.get("paineis"))[:120])
ultimo = d["paineis"][-1]
checar("P8 · o registro guarda o estado por especialista",
       ultimo["agentes"].get("copywriter") == "EXECUTADO", str(ultimo))

# ============================================================ P9 · ordem do roster
dem2 = nova("Ordem do roster")
roda(demanda.cmd_planejar, demanda=dem2, plano="tudo")
for ag in ("revisor-de-criacao", "copywriter", "lp-builder"):
    add_job(dem2, ag)
linhas = [l for l in painel(dem2).splitlines() if l.startswith("║ ") and "SQUAD" not in l]
checar("P9 · as linhas saem na ordem do roster, nao na de criacao",
       "COPYWRITER" in linhas[0] and "LP BUILDER" in linhas[1]
       and "REVISOR" in linhas[2], str(linhas))

# ============================================================ P10 · largura estavel
larguras = {demanda.largura_visual(l) for l in linhas}
checar("P10 · toda linha do painel tem a mesma largura", len(larguras) == 1, str(larguras))

# ============================================================ P11 · painel escrito a mao
# O caso real: o Diretor devolveu tres especialistas em TRABALHANDO com os tres
# jobs ainda PENDENTE. Nao foi mentira — foi a intencao escrita como se ja
# tivesse acontecido. O motor confere e o motor vence.
dem3 = nova("Painel escrito a mao")
roda(demanda.cmd_planejar, demanda=dem3, plano="copy, arte e revisao")
for ag in ("copywriter", "designer", "revisor-de-criacao"):
    add_job(dem3, ag)

FORJADO = """╔══════════════════════════════════════╗
║         ♟️ ATIVANDO SQUAD NK          ║
╠══════════════════════════════════════╣
║ ✍️ COPYWRITER        ● TRABALHANDO... ║
║ 🎨 DESIGNER          ● TRABALHANDO... ║
║ 🔎 REVISOR DE ARTE   ● TRABALHANDO... ║
╚══════════════════════════════════════╝"""

d3 = modelo.carregar(dem3)
div = demanda.conferir_painel(d3, FORJADO)
checar("P11 · painel que diz TRABALHANDO com job PENDENTE nao confere",
       len(div) == 3, str(div))
checar("P11 · a divergencia nomeia o que o estado sustenta",
       all("CRIADO" in x for x in div), str(div))

roda(demanda.cmd_job_iniciar, demanda=dem3, job="JOB-001")
d3 = modelo.carregar(dem3)
div = demanda.conferir_painel(d3, FORJADO)
checar("P11 · disparado um, so os outros dois divergem", len(div) == 2, str(div))

# o painel do motor sempre confere consigo mesmo
linhas_motor, _ = demanda.linhas_do_painel(modelo.carregar(dem3))
checar("P11 · o painel do motor confere consigo mesmo",
       demanda.conferir_painel(modelo.carregar(dem3), "\n".join(linhas_motor)) == [],
       str(demanda.conferir_painel(modelo.carregar(dem3), "\n".join(linhas_motor))))

# painel que ESCONDE quem tem job tambem nao confere
so_um = "║ ✍️ COPYWRITER        ● TRABALHANDO... ║"
div = demanda.conferir_painel(modelo.carregar(dem3), so_um)
checar("P11 · painel que esconde especialista com job nao confere",
       any("ficou de fora" in x for x in div), str(div))

# painel que INVENTA especialista sem job tambem nao
inventado = so_um + "\n║ 🧱 LP BUILDER        ● TRABALHANDO... ║"
div = demanda.conferir_painel(modelo.carregar(dem3), inventado)
checar("P11 · painel que inventa especialista sem job nao confere",
       any("não tem job" in x for x in div), str(div))

# dizer MENOS do que o estado sustenta nao e divergencia: e modestia
menos = """║ ✍️ COPYWRITER        ○ NA FILA       ║
║ 🎨 DESIGNER          ○ NA FILA       ║
║ 🔎 REVISOR DE ARTE   ○ NA FILA       ║"""
checar("P11 · dizer menos do que o estado sustenta nao e divergencia",
       demanda.conferir_painel(modelo.carregar(dem3), menos) == [],
       str(demanda.conferir_painel(modelo.carregar(dem3), menos)))

shutil.rmtree(TMP, ignore_errors=True)

if falhas:
    print(f"\n{len(falhas)} FALHA(S) em {len(feitos)} checagens")
    for f in falhas:
        print(f"  x {f}")
    sys.exit(1)
print(f"\nteste-painel: {len(feitos)} checagens "
      "(criado != disparado != executado, skill nao vira Agent) · OK")
sys.exit(0)
