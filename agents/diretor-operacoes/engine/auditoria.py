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
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
PROJETO_AGENTES = REPO / ".claude" / "agents"
PROJETO_SKILLS = REPO / ".claude" / "skills"
CLAUDE_MD = REPO / "CLAUDE.md"
DIRETOR = REPO / "agents" / "diretor-operacoes" / "agents" / "diretor-de-operacoes.md"
LEIAME = REPO / "README.md"

# Fonte canônica do painel: o CLAUDE.md, porque é o único arquivo que o Claude
# Code carrega sozinho em qualquer sessão. As outras duas cópias existem por
# motivo de plataforma (prompt do subagente, documentação) e são conferidas
# contra esta. Divergir é falha, não detalhe de redação.
PAINEL_CANONICO = """```
╔══════════════════════════════════════╗
║         ♟️ ATIVANDO SQUAD NK          ║
╠══════════════════════════════════════╣
║ ✍️ COPYWRITER        ● TRABALHANDO... ║
║ 🎨 DESIGNER          ● TRABALHANDO... ║
║ 🔎 REVISOR DE ARTE   ● TRABALHANDO... ║
╚══════════════════════════════════════╝
```"""


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


def chega_pelo_projeto(sub: str, prompt: str) -> bool:
    """O agente está em `.claude/agents/` e aponta para o prompt declarado?

    Este é o único caminho que funciona em clone novo sem instalação prévia: o
    Claude Code lê `.claude/agents/` do projeto e segue symlink. Os outros dois
    (symlink do setup.sh em ~/.claude, plugin do marketplace) dependem de um
    passo manual que não acontece num container Web novo.
    """
    if not sub:
        return False
    arquivo = PROJETO_AGENTES / f"{sub}.md"
    if not arquivo.is_file():                 # is_file() já segue o symlink
        return False
    try:
        return arquivo.resolve() == (REPO / prompt).resolve()
    except OSError:
        return False


def como_se_instala(prompt: str, setup: str, marketplace: str, sub: str = "") -> str:
    """Por onde o prompt chega ao Claude Code, em ordem de portabilidade.

    `projeto` é o que vale num clone novo. `symlink` e `plugin` continuam
    legítimos e seguem valendo na máquina de quem rodou o setup, mas nenhum dos
    dois sozinho faz o Squad existir numa sessão Web recém-aberta.
    """
    if chega_pelo_projeto(sub, prompt):
        return "projeto"
    if prompt in setup:
        return "symlink"
    base = pathlib.PurePosixPath(prompt).parent.parent          # agents/<x>/agents/y.md -> agents/<x>
    if (REPO / base / ".claude-plugin" / "plugin.json").is_file() and str(base) in marketplace:
        return "plugin"
    return ""


def auditar_agente(a: dict, registry: str, setup: str, marketplace: str) -> tuple[list, list]:
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

    # Skill que o agente carrega só serve se o Claude Code enxergar. Mesmo
    # raciocínio do prompt: em clone novo, quem entrega isso é `.claude/skills/`.
    for alvo in a.get("skills") or []:
        nome = pathlib.PurePosixPath(alvo).name
        atalho = PROJETO_SKILLS / nome
        if not atalho.exists():
            falhas.append(f"{ident}: skill '{nome}' não chega ao Claude Code "
                          f"— ausente em .claude/skills/")
        elif atalho.resolve() != (REPO / alvo).resolve():
            falhas.append(f"{ident}: .claude/skills/{nome} aponta para outro lugar que não {alvo}")

    if not chega_pelo_projeto(sub, prompt):
        falhas.append(f"{ident}: ausente em .claude/agents/ — não existe em clone novo, "
                      "só na máquina de quem rodou o setup.sh")

    if a.get("papel") == "especialista":
        if sub not in modelo.agentes_acionaveis():
            falhas.append(f"{ident}: formal, mas o motor não o considera acionável")
        if sub and sub not in registry:
            falhas.append(f"{ident}: ausente no REGISTRY.md — o Diretor não sabe rotear para ele")
    if not como_se_instala(prompt, setup, marketplace, sub):
        falhas.append(f"{ident}: não chega ao Claude Code — nem symlink no setup.sh, "
                      "nem plugin declarado no marketplace")
    return falhas, notas


def auditar_painel() -> list:
    """O template do painel é o mesmo nos três lugares onde ele precisa existir?

    Não dá para ter uma cópia só: o CLAUDE.md é o que o Claude Code carrega
    sozinho, o prompt do Diretor é o que vale quando o subagente roda, e o README
    é o que o humano lê. O que dá para garantir é que as três digam a mesma coisa.
    """
    falhas = []
    if not CLAUDE_MD.is_file():
        return ["CLAUDE.md ausente: a regra global de roteamento não existe"]

    claude_md = CLAUDE_MD.read_text(encoding="utf-8")
    if PAINEL_CANONICO not in claude_md:
        falhas.append("CLAUDE.md não contém o template do painel na forma canônica "
                      "— é ele que o Claude Code carrega sozinho")
    for termo, motivo in (
        ("Agent(subagent_type: \"diretor-de-operacoes\")",
         "não manda acionar o Diretor"),
        ("● TRABALHANDO...", "não declara o status de trabalho"),
        ("⚠ BLOQUEADO", "não declara o status de bloqueio"),
    ):
        if termo not in claude_md:
            falhas.append(f"CLAUDE.md {motivo} ({termo})")

    for arquivo, rotulo in ((DIRETOR, "prompt do Diretor"), (LEIAME, "README.md")):
        if not arquivo.is_file():
            falhas.append(f"{rotulo} ausente: não dá para conferir o painel")
            continue
        if PAINEL_CANONICO not in arquivo.read_text(encoding="utf-8"):
            falhas.append(f"{rotulo}: template do painel diverge do CLAUDE.md "
                          "— duas verdades sobre a mesma interface")
    return falhas


def auditar() -> tuple[list, list, list]:
    agentes = roster.agentes()
    registry = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
    setup = SETUP.read_text(encoding="utf-8") if SETUP.is_file() else ""
    marketplace = MARKETPLACE.read_text(encoding="utf-8") if MARKETPLACE.is_file() else ""
    falhas, notas, linhas = [], [], []

    if not registry:
        falhas.append("REGISTRY.md ausente: ninguém define o roteamento por capability")
    falhas += auditar_painel()
    if not (REPO / ".claude" / "settings.json").is_file():
        falhas.append(".claude/settings.json ausente: o hook PreToolUse não é registrado "
                      "pelo projeto e o portão fica sem o contorno de shell")
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

        f, n = auditar_agente(a, registry, setup, marketplace)
        falhas += f
        notas += n
        estado = "FALHA" if f else ("BLOQUEIO" if n else "OK")
        alvo = a.get("subagent_type") or "—"
        via = (como_se_instala(a.get("prompt") or "", setup, marketplace,
                               a.get("subagent_type") or "") if a.get("prompt") else "")
        linhas.append(f"  {a.get('emoji','?')} {ident:<20} {estado:<9} {alvo:<22} {via}")
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
