#!/usr/bin/env python3
"""Descoberta e handoff para o Revisor de Criacao.

O Designer NAO sabe revisar. Ele localiza o revisor existente no ambiente e entrega a
peca para ele. Nenhum criterio de revisao e copiado para ca -- este arquivo so acha o
plugin e monta o pacote de handoff.

O caminho e DESCOBERTO, nunca presumido: muda conforme a maquina, a versao e a forma de
instalacao (cache/, marketplaces/, repo de desenvolvimento, instalacao do lado Windows
quando se roda no WSL).

Uso:
    revisor.py locate [--json]
    revisor.py handoff --job <dir-do-job> --version N
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import sys

HOME = pathlib.Path.home()

# Marcadores que provam que um diretorio e mesmo o plugin do revisor.
MARKERS = ("agents/revisor-de-criacao.md", "conhecimento/regras-gerais.md",
           "conhecimento/criterios")


def is_revisor(d: pathlib.Path) -> bool:
    return d.is_dir() and all((d / m).exists() for m in MARKERS)


def candidates() -> list[tuple[str, pathlib.Path]]:
    """Candidatos em ordem de preferencia, com a origem de cada um."""
    out: list[tuple[str, pathlib.Path]] = []

    def add(origin: str, p) -> None:
        if p:
            out.append((origin, pathlib.Path(p)))

    # 1. override explicito, para o usuario apontar uma copia especifica
    add("env:DESIGNER_REVISOR_HOME", os.environ.get("DESIGNER_REVISOR_HOME"))
    # 2. quando o proprio Claude Code ja expos a raiz do plugin
    add("env:CLAUDE_PLUGIN_ROOT", os.environ.get("CLAUDE_PLUGIN_ROOT"))

    # 3. instalacao neste ambiente (Linux/WSL)
    for pat in ("plugins/cache/*/revisor*/*", "plugins/cache/*/revisor*",
                "plugins/marketplaces/*/", "plugins/marketplaces/*/*/"):
        for p in sorted(glob.glob(str(HOME / ".claude" / pat))):
            add("plugin instalado (este ambiente)", p)

    # 4. instalacao do lado Windows, visivel do WSL. Mesmo plugin, outra arvore de config.
    for pat in ("plugins/cache/*/revisor*/*", "plugins/cache/*/revisor*",
                "plugins/marketplaces/*/", "plugins/marketplaces/*/*/"):
        for p in sorted(glob.glob(f"/mnt/c/Users/*/.claude/{pat}")):
            add("plugin instalado (Windows, via /mnt/c)", p)

    # 5. repositorio de desenvolvimento
    for pat in ("projetos/*", "*", "projetos/*/*"):
        for p in sorted(glob.glob(str(HOME / pat))):
            add("repositorio local", p)

    return out


def locate() -> dict:
    seen: set[str] = set()
    for origin, p in candidates():
        try:
            rp = p.resolve()
        except OSError:
            continue
        key = str(rp)
        if key in seen or not is_revisor(rp):
            continue
        seen.add(key)
        version = None
        pj = rp / ".claude-plugin" / "plugin.json"
        if pj.is_file():
            try:
                version = json.loads(pj.read_text(encoding="utf-8", errors="ignore")).get("version")
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "ok": True, "base": str(rp), "origin": origin, "version": version,
            "agent": str(rp / "agents" / "revisor-de-criacao.md"),
            "conhecimento": str(rp / "conhecimento"),
            "skills": sorted(d.name for d in (rp / "skills").iterdir()) if (rp / "skills").is_dir() else [],
        }
    return {
        "ok": False, "base": None,
        "erro": "Revisor de Criacao nao encontrado neste ambiente.",
        "como_resolver": [
            "Instalar o plugin (uma vez, num terminal claude interativo):",
            "  claude plugin marketplace add acessosnonaka-cmyk/revisor-de-arte",
            "  claude plugin install revisor-de-criacao@squad-legend-ai",
            "Ou apontar uma copia existente:",
            "  export DESIGNER_REVISOR_HOME=/caminho/para/revisor-de-criacao",
        ],
    }


HANDOFF = """# Handoff para o Revisor de Criacao

Esta peca foi produzida pelo Designer IA e precisa de revisao **antes da entrega**.

## Regras deste handoff

- O revisor e a autoridade. O Designer nao atribui nota, nao define status e nao discute
  o parecer.
- Revise a peca **como ela esta no arquivo**. Nao edite, nao corrija, nao refaca.
- Aplique a regua que ja e sua (`{conhecimento}`). Nada de criterio novo vindo daqui.

## Base de conhecimento do revisor

    BASE={base}
    origem: {origin}
    agente: {agent}

Leia `{agent}` e siga esse agente. As skills disponiveis na base: {skills}.

## O que foi pedido

Contexto: **{contexto}**
Cliente: **{client}**
Formato: **{formato}** ({w}x{h}px)
Template: `{template}`
Versao: **v{version}**{ciclo}

### Briefing original (o que o Designer deveria entregar)

```json
{brief}
```

### Identidade visual vigente (restricoes que a peca deveria respeitar)

{restricoes}

### Direcao de arte declarada pelo Designer

{direcao}

Isto e contexto da INTENCAO, para voce julgar a execucao. Nao e pedido de aprovacao da
direcao: continue avaliando a peca pela sua propria regua.

## O arquivo a revisar

    {png}

## O que o Designer ja mediu sozinho

Checagem tecnica automatica (dimensao, overflow, contraste, assets, canvas):

```
{validacao}
```

Use isso como ponto de partida, nao como conclusao. O que interessa e o que **voce** ve.

## Formato da resposta

Siga `conhecimento/formato-relatorio.md`. Alem do parecer normal, termine com um bloco
que o Designer consiga ler de volta:

```
DESIGNER-ACOES
- <uma linha por observacao acionavel>
```

Uma linha por problema, objetiva, dizendo **o que** esta errado e **onde**. Se a peca
estiver aprovada sem ressalvas, escreva `DESIGNER-ACOES` seguido de `- nenhuma`.
"""


def cmd_locate(a) -> int:
    r = locate()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif r["ok"]:
        print(f"BASE={r['base']}")
        print(f"origem: {r['origin']}  versao: {r['version']}")
        print(f"skills: {', '.join(r['skills']) or '(nenhuma)'}")
    else:
        print(r["erro"], file=sys.stderr)
        for line in r["como_resolver"]:
            print(line, file=sys.stderr)
    return 0 if r["ok"] else 1


def cmd_handoff(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    r = locate()
    if not r["ok"]:
        print(json.dumps(r, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    brief = json.loads((job_dir / f"brief.v{a.version}.json").read_text(encoding="utf-8"))
    snap_path = job_dir / "brand.snapshot.json"
    snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.is_file() else {}

    restr = snap.get("restrictions") or []
    tone_avoid = (snap.get("tone") or {}).get("avoid") or []
    linhas = [f"- {x}" for x in restr] + [f"- evitar no texto: {x}" for x in tone_avoid]

    val_path = job_dir / f"validate.v{a.version}.txt"
    validacao = val_path.read_text(encoding="utf-8").strip() if val_path.is_file() else "(nao executada)"

    ad_path = job_dir / "art-direction.json"
    direcao = "- (peca sem direcao de arte registrada)"
    if ad_path.is_file():
        ad = json.loads(ad_path.read_text(encoding="utf-8"))
        res = ad.get("_resolved", {})
        tip = res.get("typography", {})
        hier = ", ".join(f"{k} {v['px']}px/{v['weight']}" for k, v in tip.items()
                         if k in ("headline", "subheadline", "body", "eyebrow"))
        direcao = "\n".join([
            f"- **Conceito:** {ad.get('concept', '?')}",
            f"- **Por que:** {ad.get('rationale', '?')}",
            f"- **Tom:** {ad.get('visual_tone', '?')}",
            f"- **Elemento dominante:** {ad.get('dominant_element', '?')}",
            f"- **Papel da marca:** {ad.get('brand_role', '?')}",
            f"- **Papel do CTA:** {ad.get('cta_role', '?')}",
            f"- **Camadas ativas:** {', '.join(ad.get('layers', [])) or '-'}",
            f"- **Hierarquia tipografica:** {hier or '-'}",
        ])

    fmt = job.get("format", {})
    cyc = job.get("cycle", 1)
    ciclo = f" (ciclo {cyc} de {job.get('max_cycles', 3)})" if cyc > 1 else ""

    txt = HANDOFF.format(
        base=r["base"], origin=r["origin"], agent=r["agent"], conhecimento=r["conhecimento"],
        skills=", ".join(r["skills"]) or "(nenhuma)",
        contexto=job.get("contexto", "SOCIAL"),
        client=job.get("client", "?"),
        formato=fmt.get("label", job.get("format_name", "?")),
        w=fmt.get("w", "?"), h=fmt.get("h", "?"),
        template=brief.get("template", "?"), version=a.version, ciclo=ciclo,
        brief=json.dumps({k: v for k, v in brief.items() if k != "assets"},
                         ensure_ascii=False, indent=2),
        restricoes="\n".join(linhas) or "- (nenhuma registrada no brand kit)",
        direcao=direcao,
        png=str(job_dir / f"v{a.version}.png"),
        validacao=validacao,
    )
    out = job_dir / f"handoff.v{a.version}.md"
    out.write_text(txt, encoding="utf-8")
    print(out)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("locate"); p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_locate)
    p = sub.add_parser("handoff"); p.add_argument("--job", required=True)
    p.add_argument("--version", type=int, required=True); p.set_defaults(fn=cmd_handoff)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
