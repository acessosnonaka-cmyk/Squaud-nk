#!/usr/bin/env python3
"""Auditoria do Squad: o roster declarado bate com o que existe em disco?

O Diretor precisa saber quem ele pode acionar de verdade. Sem esta conferência,
um agente some do disco, muda de nome ou perde o registro e o Diretor continua
prometendo o trabalho dele — que é a pior falha possível numa orquestração.

Roda com o python do sistema, não escreve nada, não toca em dado de cliente e
não executa ação externa. Saída: 0 quando o Squad está íntegro, 2 quando existe
bloqueio real. Um agente em estado `conceito` é bloqueio declarado, não erro:
ele aparece como tal, e o motor recusa criar job para ele.

    python3 agents/diretor-operacoes/engine/auditoria.py
    python3 agents/diretor-operacoes/engine/auditoria.py --curto
"""
from __future__ import annotations

import argparse
import pathlib
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from engine import modelo, roster                 # type: ignore
else:
    from . import modelo, roster

REPO = roster.REPO
REGISTRY = REPO / "agents" / "diretor-operacoes" / "REGISTRY.md"
SETUP = REPO / "scripts" / "setup.sh"


def frontmatter(caminho: pathlib.Path) -> dict:
    """Cabeçalho YAML do prompt do agente. É ele que define o subagent_type real."""
    linhas = caminho.read_text(encoding="utf-8").split("\n")
    if not linhas or linhas[0].strip() != "---":
        return {}
    dados = {}
    for linha in linhas[1:]:
        if linha.strip() == "---":
            break
        chave, _, valor = linha.partition(":")
        if _ and not chave.startswith(" "):
            dados[chave.strip()] = valor.strip()
    return dados


def auditar_agente(a: dict, registry: str, setup: str) -> tuple[list, list]:
    """Devolve (falhas, notas) de um agente do roster."""
    falhas, notas = [], []
    ident = a.get("id") or "(sem id)"
    for campo in ("id", "nome", "papel", "agente", "emoji"):
        if not a.get(campo):
            falhas.append(f"{ident}: campo '{campo}' ausente no squad.yaml")
    if not a.get("capabilities"):
        falhas.append(f"{ident}: nenhuma capability declarada")

    if a.get("agente") == "conceito":
        if a.get("prompt") or a.get("subagent_type"):
            falhas.append(f"{ident}: é conceito, mas declara prompt ou subagent_type")
        if ident in modelo.agentes_acionaveis():
            falhas.append(f"{ident}: é conceito e ainda assim aparece como acionável")
        notas.append(f"{ident}: conceito — papel definido, implementação ausente")
        return falhas, notas

    prompt = a.get("prompt")
    sub = a.get("subagent_type")
    if not prompt:
        falhas.append(f"{ident}: agente formal sem prompt declarado")
        return falhas, notas
    caminho = REPO / prompt
    if not caminho.is_file():
        falhas.append(f"{ident}: prompt declarado não existe em disco ({prompt})")
        return falhas, notas

    fm = frontmatter(caminho)
    if not fm.get("name"):
        falhas.append(f"{ident}: prompt sem 'name' no frontmatter — não vira subagente")
    elif fm["name"] != sub:
        falhas.append(f"{ident}: subagent_type '{sub}' != name '{fm['name']}' do prompt")
    if not fm.get("description"):
        falhas.append(f"{ident}: prompt sem 'description' — o Diretor não sabe quando usar")

    texto = caminho.read_text(encoding="utf-8")
    if "EXECUTION_MODE" not in texto:
        falhas.append(f"{ident}: prompt não declara EXECUTION_MODE = SILENT")

    for campo in ("skills", "motores"):
        for alvo in a.get(campo) or []:
            if not (REPO / alvo).exists():
                falhas.append(f"{ident}: {campo[:-1]} declarado não existe ({alvo})")

    if a.get("papel") == "especialista":
        if sub not in modelo.agentes_acionaveis():
            falhas.append(f"{ident}: formal, mas o motor não o considera acionável")
        if sub and sub not in registry:
            falhas.append(f"{ident}: ausente no REGISTRY.md — o Diretor não sabe rotear para ele")
    if prompt not in setup:
        falhas.append(f"{ident}: scripts/setup.sh não liga o prompt em ~/.claude/agents")
    return falhas, notas


def auditar() -> tuple[list, list, list]:
    agentes = roster.agentes()
    registry = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
    setup = SETUP.read_text(encoding="utf-8") if SETUP.is_file() else ""
    falhas, notas, linhas = [], [], []

    if not registry:
        falhas.append("REGISTRY.md ausente: ninguém define o roteamento por capability")
    if len(agentes) != 7:
        falhas.append(f"roster tem {len(agentes)} agentes; o Squad são 7")

    vistos, donos = set(), {}
    for a in agentes:
        ident = a.get("id") or "(sem id)"
        if ident in vistos:
            falhas.append(f"{ident}: id duplicado no roster")
        vistos.add(ident)
        for c in a.get("capabilities") or []:
            if c in donos:
                falhas.append(f"capability '{c}' com dois donos: {donos[c]} e {ident}")
            donos[c] = ident

        f, n = auditar_agente(a, registry, setup)
        falhas += f
        notas += n
        estado = "BLOQUEIO" if n else ("FALHA" if f else "OK")
        estado = "FALHA" if f else estado
        alvo = a.get("subagent_type") or "—"
        linhas.append(f"  {a.get('emoji','?')} {ident:<20} {estado:<9} {alvo}")
    return falhas, notas, linhas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="auditoria", description="Auditoria do roster do Squad NK")
    ap.add_argument("--curto", action="store_true", help="só o veredito")
    a = ap.parse_args(argv)

    falhas, notas, linhas = auditar()
    if not a.curto:
        print(f"\nAUDITORIA DO SQUAD NK · {roster.ARQUIVO.name} ({len(linhas)} agentes)")
        print("\n".join(linhas))
        if falhas:
            print("\nFALHAS DE INTEGRAÇÃO")
            for f in falhas:
                print(f"  ✗ {f}")
        if notas:
            print("\nBLOQUEIOS DECLARADOS")
            for n in notas:
                print(f"  ⏸ {n}")
    if falhas:
        print("\nBLOQUEIO ENCONTRADO")
        return 2
    if notas:
        print("\nBLOQUEIO ENCONTRADO: " + "; ".join(notas))
        return 2
    print("\nSQUAD NK VALIDADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
