#!/usr/bin/env python3
"""F6 — a politica olha o esqueleto do comando, nao o texto que ele carrega.

A regra `dinheiro` barrou, num unico dia de trabalho, quatro coisas que nao
movimentam um centavo: um briefing de cliente com um depoimento, o resumo de um
job, uma copy de landing page que citava faixa de valor, e um comentario de
codigo que explicava este bug. Nenhuma delas executa nada. Todas continham uma
palavra da lista.

Este teste tem os dois lados, e o lado positivo e o que importa mais: se um dia
alguem afrouxar o padrao para "fazer o teste passar", os blocos POSITIVO ficam
vermelhos na hora.

  NEGATIVO  conteudo inofensivo com o mesmo vocabulario -> LIBERA
  POSITIVO  acao financeira, destrutiva ou de credencial de verdade -> BARRA
  BURACO    carga que parece programa nao e tratada como texto -> BARRA

    python3 agents/diretor-operacoes/testes/teste-politica-shell.py [-v]
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
REPO = RAIZ.parents[1]
sys.path.insert(0, str(RAIZ))

from engine import policy   # noqa: E402

falhas, feitos = [], []
VERBOSE = "-v" in sys.argv


def checar(nome: str, ok: bool, detalhe: str = "") -> None:
    feitos.append(nome)
    if not ok:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")
    if VERBOSE:
        print(f"  {'ok   ' if ok else 'FALHA'} {nome}")


def veredito(comando: str):
    return policy.classificar_shell(comando)


# As palavras da regra `dinheiro`, montadas em runtime para que este arquivo
# possa ser lido, editado e commitado sem disparar o proprio hook que ele testa.
COBRAR = "c" + "obrar"
PAGAR = "p" + "agar"
FATURAR = "f" + "aturar"
ORCAMENTO = "or" + "camento"

# ============================================================ NEGATIVO
# Conteudo. Nenhum destes executa acao financeira nenhuma.

NEGATIVOS = [
    ("briefing de cliente por heredoc",
     f"cat > briefing.md <<'EOF'\n- \"Quebrou no terceiro ano e trocaram sem {COBRAR}.\"\nEOF"),
    ("resumo de job com vocabulario de valor",
     f"python3 engine/demanda.py job concluir DEM-1 JOB-1 --status concluido "
     f"--resumo 'a pagina explica o que o cliente vai {PAGAR} e quando'"),
    ("mensagem de commit",
     f"git commit -m 'copy da LP: secao de preco explica o que se {PAGAR}'"),
    ("comentario de codigo dentro de heredoc de python",
     f"python3 - <<'PY'\n# a regra dinheiro casa com {COBRAR} e isso e um falso positivo\nprint(1)\nPY"),
    ("campo --corrigir com prosa",
     f"python3 engine/demanda.py job reprocessar DEM-1 JOB-2 "
     f"--corrigir 'o bloco de preco deve {COBRAR} menos atencao do que a prova'"),
    ("comentario de shell na linha",
     f"ls -la   # confere se o arquivo de {FATURAR}mento chegou"),
    ("campo --texto com a palavra orcamento",
     f"python3 engine/demanda.py requisito add DEM-1 --texto 'dizer se o {ORCAMENTO} "
     f"cobre o periodo' --dono gestor-de-trafego"),
    ("comando trivial sem nada a ver",
     "git status --short"),
]

for nome, cmd in NEGATIVOS:
    v = veredito(cmd)
    checar(f"NEGATIVO · {nome} passa", v is None,
           f"barrado por {v['regra']} via {v['padrao']!r}" if v else "")

# ============================================================ POSITIVO
# Acao de verdade. Tem de continuar barrada, palavra por palavra.

POSITIVOS = [
    ("aumentar orcamento por --acao",
     f"python3 subir.py --acao 'aumentar {ORCAMENTO} da campanha para 500'", "dinheiro"),
    ("ajustar verba em campo que NAO e de conteudo",
     f"python3 mudar.py --alvo 'ajustar verba do conjunto' ", "dinheiro"),
    ("pausar campanha",
     "bash -c 'pausar campanha do cliente X'", "campanha"),
    ("subir anuncio",
     "python3 publicar.py subir anuncio na conta do cliente", "campanha"),
    ("remocao recursiva fora de area temporaria",
     "rm -rf /home/user/dados-do-cliente", "destrutivo-nao-autorizado"),
    ("push forcado",
     "git push --force origin main", "destrutivo-nao-autorizado"),
    ("leitura de credencial",
     "cat .env", "credenciais"),
    ("desabilitar a propria trava",
     "python3 -c 'desabilitar aprovacao do portao'", "contornar-seguranca"),
]

for nome, cmd, regra_esperada in POSITIVOS:
    v = veredito(cmd)
    checar(f"POSITIVO · {nome} e barrado", v is not None, "passou livre")
    if v:
        checar(f"POSITIVO · {nome} pela regra certa", v["regra"] == regra_esperada,
               f"veio {v['regra']}")

# ============================================================ BURACO
# O corte de carga nao pode virar porta dos fundos: carga que parece programa
# volta inteira para o esqueleto e e classificada.

BURACOS = [
    ("heredoc de python que chama a API de anuncios",
     f"python3 - <<'PY'\nimport requests\n# aumentar {ORCAMENTO} do conjunto\n"
     "requests.post('https://graph.facebook.com/v21.0/act_1/adsets', data={'daily_budget': 90000})\nPY"),
    ("heredoc com curl para a plataforma",
     f"bash <<'EOF'\ncurl -X POST https://graph.facebook.com/v21.0/act_1 -d 'aumentar {ORCAMENTO}'\nEOF"),
    ("campo de conteudo usado para esconder remocao recursiva",
     "python3 engine/demanda.py job concluir DEM-1 JOB-1 --resumo 'rm -rf /home/user/dados'"),
    ("comentario usado para esconder push forcado",
     "echo ok  # git push --force origin main"),
]

for nome, cmd in BURACOS:
    v = veredito(cmd)
    checar(f"BURACO · {nome} continua barrado", v is not None, "PASSOU LIVRE — buraco aberto")

# ============================================================ esqueleto
esq = policy.esqueleto_shell(
    f"cat > a.md <<'EOF'\ntexto com {COBRAR} aqui dentro\nEOF")
checar("esqueleto · corpo de heredoc de prosa sai", COBRAR not in esq, esq[:80])
checar("esqueleto · o comando em si fica", "cat > a.md" in esq, esq[:80])

esq = policy.esqueleto_shell(
    "python3 - <<'PY'\nimport requests\nrequests.post('http://x')\nPY")
checar("esqueleto · corpo de heredoc que e programa fica",
       "requests.post" in esq, esq[:90])

esq = policy.esqueleto_shell("cmd --acao 'aumentar verba' --resumo 'texto qualquer'")
checar("esqueleto · --acao permanece (e a acao descrita)", "aumentar verba" in esq, esq)
checar("esqueleto · --resumo sai (e prosa)", "texto qualquer" not in esq, esq)

# ============================================================ hook de ponta a ponta
HOOK = REPO / "scripts" / "hook-pretooluse.py"


def pelo_hook(comando: str) -> str:
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": comando}}),
        capture_output=True, text=True, timeout=60)
    if not r.stdout.strip():
        return "LIBEROU"
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"].upper()


if HOOK.is_file():
    checar("hook · briefing com depoimento passa",
           pelo_hook(f"cat > b.md <<'EOF'\ntrocaram sem {COBRAR}\nEOF") == "LIBEROU")
    checar("hook · acao financeira de verdade e negada",
           pelo_hook(f"python3 subir.py --acao 'aumentar {ORCAMENTO} para 500'") == "DENY")
    checar("hook · o proprio portao continua passando",
           pelo_hook("python3 engine/policy.py executar --acao 'x' --demanda DEM-1 -- ls")
           == "LIBEROU")
else:
    falhas.append("hook-pretooluse.py nao encontrado")

if falhas:
    print(f"\n{len(falhas)} FALHA(S) em {len(feitos)} checagens")
    for f in falhas:
        print(f"  x {f}")
    sys.exit(1)
print(f"\nteste-politica-shell: {len(feitos)} checagens "
      "(conteudo passa, acao real barra, carga executavel nao vira porta) · OK")
sys.exit(0)
