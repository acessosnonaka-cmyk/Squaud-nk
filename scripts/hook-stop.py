#!/usr/bin/env python3
"""Hook Stop — barra promessa de execução futura e narração de bastidor.

Três rodadas de regra em prosa no CLAUDE.md reduziram o comportamento e não o
eliminaram: em 3 de 5 execuções com corte forçado a sessão ainda fechava com
"quando o Diretor terminar eu trago o resultado". Regra de prompt é estatística;
o portão aqui é determinístico.

O que ele decide, e o que NÃO decide:

  - Não reescreve a resposta. O `Stop` oficial só bloqueia; quem corrige é o
    modelo, com o motivo que este arquivo devolve.
  - Não inventa que um job terminou. O motivo manda declarar estado real, e
    preservar DEMAND_ID/JOB_ID quando existirem.
  - Não bloqueia entrega concluída, pergunta material, pedido de aprovação nem
    bloqueio declarado. Nada disso casa com os sinais abaixo.

O defeito não é uma lista de frases — é semântico: **representar como futura ou
assíncrona uma execução que não continua depois que o turno fecha.** Por isso
cada sinal exige a estrutura inteira (quem entrega + quando entrega), e por isso
a negação desarma o sinal: "não existe aviso depois" é exatamente a frase certa.
"""
from __future__ import annotations

import json
import re
import sys

# ---------------------------------------------------------------- vocabulário

# Quem age: só atores do Squad. "o teste está rodando" não é falso background.
ATOR = r"(?:diretor|copywriter|designer|revisor|gestor de tr[áa]fego|lp builder|legend|especialista|squad|agente|subagente)"

# Entrega feita pelo PRÓPRIO agente, no futuro.
ENTREGA_1P = (r"(?:eu\s+)?(?:vou|irei|vamos)?\s*"
              r"(?:aviso|avisar|avisarei|te\s+aviso|trago|trazer|trarei|volto|voltar|voltarei|"
              r"retorno|retornar|retornarei|informo|informar|informarei|mando|mandar|mandarei|"
              r"sigo|seguir|seguirei|atualizo|atualizar|compartilho|compartilhar)")

# Cláusula temporal apontando para a conclusão de OUTRO trabalho.
QUANDO = (r"(?:quando|assim\s+que|t[ãa]o\s+logo|logo\s+que|depois\s+que|ap[óo]s|ao)\s+"
          r"[^.!?;]{0,70}?"
          r"(?:terminar|acabar|concluir|finalizar|ficar(?:em)?\s+pront|retornar|chegar|sair|"
          r"sa[íi]rem|voltar|responder)")

# Trabalho que seguiria sozinho depois do turno.
ASSINCRONO = (r"(?:em\s+segundo\s+plano|em\s+background|rodando\s+(?:agora|no\s+momento)|"
              r"est[áa]\s+(?:rodando|processando|executando|trabalhando|em\s+execu[çc][ãa]o)|"
              r"est[ãa]o\s+(?:rodando|processando|executando|trabalhando)|ainda\s+est[áa]\s+rodando)")

NOTIFICACAO = (r"(?:voc[êe]\s+(?:vai\s+receber|receber[áa]|ser[áa]\s+notificad)|"
               r"(?:quando|assim\s+que)\s+a\s+notifica[çc][ãa]o\s+\w*\s*(?:chegar|vier)|"
               r"chega(?:r[áa])?\s+uma\s+notifica[çc][ãa]o)")

AGUARDO = (r"(?:estou|fico|vou\s+ficar)\s+(?:aguardando|esperando)|aguardando\s+(?:o\s+)?retorno")

# Negação que desarma: dizer que NÃO existe aviso futuro é o comportamento certo.
NEGACAO = r"(?:n[ãa]o|nunca|jamais|sem|nenhum[a]?|inexiste)"

# Direção invertida: instrução ao gestor não é promessa do agente.
AO_GESTOR = (r"(?:é\s+só|basta|me\s+avise|me\s+chame|se\s+quiser|caso\s+queira|quando\s+voc[êe]|"
             r"se\s+voc[êe]|digite|peça\s+para|pergunte|é\s+só\s+pedir|para\s+retomar)")

# Já aconteceu: passado não promete nada.
PASSADO = r"(?:terminou|terminaram|entregou|concluiu|voltou|retornou|finalizou|acabou|chegou)"

JANELA = 170      # caracteres entre as duas metades de um sinal composto


def _limpa(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip()


def _frases(texto: str) -> list[str]:
    """Quebra em orações. O sinal vive dentro de uma, não espalhado pelo texto."""
    return [f for f in re.split(r"(?<=[.!?;:\n])\s+|\s+—\s+", texto) if f.strip()]


def _desarmado(frase: str, pos: int) -> bool:
    """Negação, instrução ao gestor ou passado antes do trecho: não é promessa."""
    antes = frase[max(0, pos - 80):pos]
    return bool(re.search(NEGACAO, antes, re.I)
                or re.search(AO_GESTOR, antes, re.I)
                or re.search(PASSADO, antes, re.I))


def _par(frase: str, a: str, b: str) -> re.Match | None:
    """Casa duas metades na mesma oração, em qualquer ordem, dentro da janela."""
    for m1 in re.finditer(a, frase, re.I):
        for m2 in re.finditer(b, frase, re.I):
            if abs(m2.start() - m1.start()) <= JANELA:
                inicio = min(m1.start(), m2.start())
                if not _desarmado(frase, inicio):
                    return m1 if m1.start() <= m2.start() else m2
    return None


def achados(texto: str) -> list[str]:
    """Devolve os sinais encontrados. Lista vazia = resposta limpa."""
    achou = []
    tem_ator = bool(re.search(ATOR, texto, re.I))

    for frase in _frases(_limpa(texto)):
        # A · o próprio agente promete entregar quando outro trabalho terminar
        if _par(frase, ENTREGA_1P, QUANDO):
            achou.append(f"promessa de entrega futura: “{frase.strip()[:120]}”")

        # B · alega trabalho correndo sozinho — só vale com ator do Squad no texto
        if tem_ator:
            for m in re.finditer(ASSINCRONO, frase, re.I):
                if not _desarmado(frase, m.start()):
                    achou.append(f"execução apresentada como assíncrona: “{frase.strip()[:120]}”")
                    break

        # C · notificação de conclusão que não existe
        for m in re.finditer(NOTIFICACAO, frase, re.I):
            if not _desarmado(frase, m.start()):
                achou.append(f"notificação futura inexistente: “{frase.strip()[:120]}”")
                break

        # D · fechar o turno dizendo que fica aguardando um especialista
        if tem_ator and re.search(AGUARDO, frase, re.I):
            m = re.search(AGUARDO, frase, re.I)
            alvo = frase[m.end():m.end() + 90]
            if re.search(ATOR, alvo, re.I) and not _desarmado(frase, m.start()):
                achou.append(f"turno fechado em espera de especialista: “{frase.strip()[:120]}”")

    # dedup preservando ordem
    vistos, saida = set(), []
    for a in achou:
        if a not in vistos:
            vistos.add(a)
            saida.append(a)
    return saida


MOTIVO = (
    "A resposta fecha o turno prometendo o que não vai acontecer. Quando este turno "
    "termina, nada continua rodando: não há especialista em segundo plano, não há "
    "notificação de conclusão, e nenhuma mensagem sua chega ao gestor sem ele falar "
    "primeiro (CLAUDE.md, regra 13).\n\n"
    "Sinais encontrados:\n{sinais}\n\n"
    "APAGUE a oração que promete — não basta pôr uma ressalva ao lado dela. "
    "'Aviso quando a resposta chegar, mas sem retorno automático' continua sendo a "
    "mesma promessa, e será barrado de novo.\n\n"
    "No lugar dela, ESTADO REAL em uma linha: o que ficou pronto de fato, onde parou, "
    "o DEMAND_ID e o JOB_ID quando existirem, e o que o gestor digita para retomar. "
    "Não invente que um job terminou, não remova entrega que realmente existe, e não "
    "transforme isto em narração de processo."
)


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except Exception:
        return 0                      # hook ilegível não trava o trabalho

    # Já bloqueamos uma vez neste turno: a segunda passada sai, sempre.
    if entrada.get("stop_hook_active"):
        return 0

    sinais = achados(entrada.get("last_assistant_message") or "")
    if not sinais:
        return 0

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "decision": "block",
        "reason": MOTIVO.format(sinais="\n".join(f"  - {s}" for s in sinais)),
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
