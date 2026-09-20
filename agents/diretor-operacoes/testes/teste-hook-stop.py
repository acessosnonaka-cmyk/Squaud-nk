#!/usr/bin/env python3
"""O portão de saída: promessa de execução futura não fecha turno.

Metade deste arquivo são FALSOS POSITIVOS. Um detector que barra "depois",
"notificação" ou "aguardando" por aparecerem na frase seria pior que o defeito:
travaria entrega boa, pergunta legítima e conteúdo de cliente. Cada caso
negativo aqui é uma frase que TEM as palavras e NÃO pode bloquear.

    python3 agents/diretor-operacoes/testes/teste-hook-stop.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "scripts"))

import importlib.util                                       # noqa: E402
spec = importlib.util.spec_from_file_location("hook_stop", RAIZ / "scripts" / "hook-stop.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

falhas = []


def checar(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


# ============================================================ DEVE BLOQUEAR
# Todas colhidas de execuções reais desta bateria, ou variações diretas delas.
BLOQUEIA = [
    ("promessa-classica",
     "Acionei o Diretor de Operações com a demanda completa. Aviso quando terminar."),
    ("promessa-observada-1",
     "Ele está definindo os ângulos, montando o briefing e acionando o Copywriter — "
     "vou avisar assim que o painel e a entrega (PDF) saírem."),
    ("promessa-observada-2",
     "O Diretor está rodando o fluxo. Quando a execução dele terminar eu trago o resultado."),
    ("promessa-observada-3",
     "Isso está rodando agora; quando terminar, chega uma notificação e eu trago o parecer "
     "com estrelas e status."),
    ("background-explicito",
     "Acionei o Diretor de Operações. Ele está rodando em segundo plano."),
    ("notificacao-ao-gestor",
     "O Designer foi acionado. Você vai receber uma notificação quando a peça ficar pronta."),
    ("aguardando-especialista",
     "Estou aguardando o Revisor de Arte devolver o parecer."),
    ("retorno-futuro",
     "O Copywriter está trabalhando na legenda — retorno assim que ele concluir."),
    ("mando-depois",
     "Mando os 3 criativos assim que o Designer finalizar a V2."),
    ("sigo-depois",
     "O Gestor de Tráfego está processando os dados da conta; sigo quando ele responder."),
]

for nome, texto in BLOQUEIA:
    r = hook.achados(texto)
    checar(f"bloqueia/{nome}", bool(r), f"passou limpo: {texto[:70]}")

# ====================================================== NÃO PODE BLOQUEAR
# Frases legítimas que contêm as MESMAS palavras do detector.
PASSA = [
    # -- entrega concluída
    ("entrega-pronta",
     "Entrega concluída — gate liberado (DEM-20260919-001 → CONCLUÍDA). PDF final em "
     "entregas/camarero-bh/, 10 páginas, fechado pelo motor roteiro_pdf.py."),
    ("entrega-com-depois",
     "Seguem os 3 criativos aprovados. Depois de publicar, acompanhe o CTR nas primeiras 48h."),
    ("passado-terminou",
     "O Revisor terminou a análise e aprovou as três peças."),
    ("passado-retornou",
     "O Copywriter retornou com as 4 variações; o Designer já montou as artes."),

    # -- estado real declarado (o comportamento CERTO da regra 13)
    ("estado-real-negado",
     "Não tenho o resultado nesta resposta. Não há aviso automático que chegue a você quando "
     "terminar; para retomar, é só perguntar de novo."),
    ("estado-real-bloqueio",
     "BLOQUEADO. Demanda DEM-20260919-002, JOB-001 gravado com o briefing completo. "
     "Nenhum roteiro foi escrito. Para retomar: digite continue a demanda DEM-20260919-002."),
    ("estado-real-sem-background",
     "Não existe execução em segundo plano: quando este turno fecha, nada continua rodando."),

    # -- pergunta material / aprovação humana
    ("duvida-material",
     "Preciso confirmar antes de seguir: a campanha é para implante unitário ou protocolo?"),
    ("aprovacao-humana",
     "Esta ação altera o orçamento na conta do cliente e precisa da sua autorização. "
     "Estou aguardando sua confirmação para executar."),
    ("pergunta-com-quando",
     "Me avise quando tiver as fotos institucionais que eu sigo com as peças."),
    ("instrucao-ao-gestor",
     "É só pedir para retomar quando quiser que eu continue a demanda."),

    # -- conteúdo de cliente que usa as mesmas palavras
    ("conteudo-notificacao",
     "Ative a notificação de conclusão no Gerenciador do Meta para acompanhar a entrega."),
    ("conteudo-campanha",
     "A campanha vai terminar em 30 dias; depois disso o criativo precisa ser trocado."),
    ("copy-entregue",
     "CTA sugerido: “Peça seu orçamento e receba a proposta em segundo plano de fundo azul.”"),

    # -- resposta comum, fora do Squad
    ("fora-do-squad",
     "A capital da França é Paris."),
    ("repo-normal",
     "O teste está rodando agora e leva cerca de dois minutos; aviso o resultado no terminal."),
    ("vazio", ""),
]

for nome, texto in PASSA:
    r = hook.achados(texto)
    checar(f"passa/{nome}", not r, f"bloqueou indevidamente: {r[:1] if r else ''}")

# ====================================================== CONTRATO DO HOOK
HK = RAIZ / "scripts" / "hook-stop.py"


def rodar(payload: dict) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(HK)], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


rc, out = rodar({"hook_event_name": "Stop", "stop_hook_active": False,
                 "last_assistant_message": "Aviso quando o Diretor terminar."})
checar("contrato/bloqueia-rc0", rc == 0)
d = json.loads(out) if out else {}
checar("contrato/decision-block",
       d.get("hookSpecificOutput", {}).get("decision") == "block", out[:120])
motivo = d.get("hookSpecificOutput", {}).get("reason", "")
checar("contrato/motivo-manda-estado-real", "ESTADO REAL" in motivo)
checar("contrato/motivo-preserva-ids", "DEMAND_ID" in motivo and "JOB_ID" in motivo)
checar("contrato/motivo-proibe-inventar", "Não invente" in motivo)
# Observado no corte-3 da bateria: a primeira reescrita manteve a promessa e so
# acrescentou uma ressalva ao lado. O motivo tem de mandar remover a oracao.
checar("contrato/motivo-manda-remover", "APAGUE" in motivo)

# Segunda passada no mesmo turno nunca bloqueia — trava de loop.
rc, out = rodar({"hook_event_name": "Stop", "stop_hook_active": True,
                 "last_assistant_message": "Aviso quando o Diretor terminar."})
checar("contrato/loop-stop-hook-active", rc == 0 and out == "", out[:120])

# Resposta limpa passa sem saída.
rc, out = rodar({"hook_event_name": "Stop", "stop_hook_active": False,
                 "last_assistant_message": "Entrega concluída. PDF em entregas/."})
checar("contrato/limpa-passa", rc == 0 and out == "", out[:120])

# Entrada quebrada não trava o trabalho.
p = subprocess.run([sys.executable, str(HK)], input="nao e json", capture_output=True, text=True)
checar("contrato/entrada-invalida-libera", p.returncode == 0 and p.stdout.strip() == "")

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"\nteste-hook-stop: {len(BLOQUEIA)} promessas barradas · {len(PASSA)} frases legítimas "
      f"preservadas · trava de loop e contrato do hook · OK")
sys.exit(0)
