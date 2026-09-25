#!/usr/bin/env python3
"""Captura a pagina inteira, nas duas larguras, e assina o que foi capturado.

Por que existe: o Revisor aprovou uma LP sem nunca ter visto a LP. Ele leu o
HTML, leu o JSON do QA, leu a descricao do LP Builder -- e deu parecer sobre
uma pagina que tinha tarja de debug amarela sobre o H1. Parecer e opiniao
sobre a peca, nao a peca (CLAUDE.md, regra 11).

O manifesto amarra a captura a UMA versao do arquivo: `pagina_sha256` e o hash
do HTML que estava no disco na hora. Mudou uma virgula depois disso, o parecer
que veio da captura anterior nao vale mais -- e o gate consegue provar isso em
vez de confiar na palavra de quem revisou.

Captura pagina INTEIRA, nao a primeira dobra: o rodape quebrado no celular
nunca apareceu numa captura de dobra.

Uso:
    render.py --pagina <index.html|url> [--out <dir>]
    render.py verificar --manifesto <render.json>
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys

VIEWS = (("desktop", 1440, 900), ("mobile", 390, 844))
MANIFESTO = "render.json"


def _libs_chromium() -> None:
    """Mesma injecao de libnss3/libnspr4 do lp_qa.py: Chromium headless nao sobe
    sem elas em imagem enxuta de Debian, e o repositorio carrega uma copia."""
    aqui = pathlib.Path(__file__).resolve()
    candidatos = [aqui.parent / "runtime" / "lib"]
    if len(aqui.parents) > 3:
        candidatos.append(aqui.parents[3] / "shared" / "runtime" / "lib")
    candidatos.append(pathlib.Path.home() / ".claude" / "art-builder" / "runtime" / "lib")
    for d in candidatos:
        if (d / "libnspr4.so").exists():
            anterior = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{d}:{anterior}" if anterior else str(d)
            return


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


async def _capturar(url: str, out: pathlib.Path) -> list:
    from playwright.async_api import async_playwright
    out.mkdir(parents=True, exist_ok=True)
    capturas = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for nome, w, h in VIEWS:
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.goto(url, wait_until="load")
            # lazy nunca carrega em captura de pagina inteira sem isto
            await pg.evaluate(
                "document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
            await pg.wait_for_timeout(2200)
            altura = await pg.evaluate("document.body.scrollHeight")
            arq = out / f"{nome}.png"
            await pg.screenshot(path=str(arq), full_page=True)
            capturas.append({"nome": nome, "arquivo": str(arq), "largura": w,
                             "altura_total": altura, "sha256": sha(arq),
                             "bytes": arq.stat().st_size})
            await pg.close()
        await b.close()
    return capturas


def cmd_render(a) -> int:
    alvo = a.pagina
    if "://" in alvo:
        url, pagina_sha, pagina_ref = alvo, None, alvo
    else:
        p = pathlib.Path(alvo).expanduser().resolve()
        if not p.is_file():
            print(f"ERRO: {p} nao existe", file=sys.stderr)
            return 2
        url, pagina_sha, pagina_ref = p.as_uri(), sha(p), str(p)

    out = pathlib.Path(a.out).expanduser() if a.out else \
        (pathlib.Path(pagina_ref).parent / "render" if pagina_sha else pathlib.Path("render"))
    _libs_chromium()
    try:
        capturas = asyncio.run(_capturar(url, out))
    except Exception as e:
        print("BLOQUEADO: a captura nao rodou. Sem captura nao ha revisao visual, e sem "
              "revisao visual a LP nao sai.\n"
              f"  motivo: {type(e).__name__}: {str(e)[:200]}\n"
              "  instale o runtime: bash scripts/setup.sh", file=sys.stderr)
        return 3

    man = {"pagina": pagina_ref, "pagina_sha256": pagina_sha, "capturas": capturas,
           "gerado_em": dt.datetime.now().isoformat(timespec="seconds")}
    (out / MANIFESTO).write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in capturas:
        print(f"CAPTURA  {c['nome']:<8} {c['largura']}px  altura {c['altura_total']}px  "
              f"{c['bytes'] // 1024} KB  {c['arquivo']}")
    print(f"MANIFESTO {out / MANIFESTO}")
    print("\nAgora ABRA os dois PNG. Parecer sem os dois abertos e parecer sobre o HTML.")
    return 0


def verificar(manifesto: pathlib.Path) -> list:
    """Problemas do manifesto, do ponto de vista de quem vai confiar nele."""
    if not manifesto.is_file():
        return [f"{manifesto} nao existe: a pagina nunca foi capturada"]
    try:
        man = json.loads(manifesto.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{manifesto} ilegivel: {e}"]
    problemas = []
    nomes = {c.get("nome") for c in man.get("capturas", [])}
    for exigida, _w, _h in VIEWS:
        if exigida not in nomes:
            problemas.append(f"falta a captura {exigida}: a LP tem de ser vista nas duas larguras")
    for c in man.get("capturas", []):
        arq = pathlib.Path(c.get("arquivo", ""))
        if not arq.is_file():
            problemas.append(f"captura {c.get('nome')} sumiu do disco: {arq}")
        elif sha(arq) != c.get("sha256"):
            problemas.append(f"captura {c.get('nome')} mudou depois do manifesto: "
                             "nao e mais a imagem que o parecer viu")
    pg = pathlib.Path(man.get("pagina") or "")
    if man.get("pagina_sha256") and pg.is_file() and sha(pg) != man["pagina_sha256"]:
        problemas.append("a pagina mudou depois da captura: o parecer olhou outra versao. "
                         "Rode render.py de novo e revise a atual")
    return problemas


def cmd_verificar(a) -> int:
    problemas = verificar(pathlib.Path(a.manifesto).expanduser())
    if problemas:
        print(f"RENDER: NAO CONFERE — {len(problemas)} problema(s)")
        for p in problemas:
            print(f"  - {p}")
        return 2
    print("RENDER: confere — as capturas existem e sao da versao atual da pagina.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("capturar", help="captura desktop + mobile, pagina inteira")
    r.add_argument("--pagina", required=True)
    r.add_argument("--out")
    r.set_defaults(fn=cmd_render)
    v = sub.add_parser("verificar", help="o manifesto ainda vale para a pagina de hoje?")
    v.add_argument("--manifesto", required=True)
    v.set_defaults(fn=cmd_verificar)
    # sem subcomando: --pagina direto captura, que e o uso de todo dia
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        sys.argv.insert(1, "capturar")
    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
