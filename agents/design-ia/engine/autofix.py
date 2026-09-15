#!/usr/bin/env python3
"""Catalogo de correcoes automaticas seguras.

Divisao de responsabilidade:
  - o REVISOR diz o que esta errado (autoridade; criterios sao dele);
  - o CLAUDE le o parecer e escolhe quais correcoes deste catalogo se aplicam (juizo);
  - este arquivo EXECUTA a correcao de forma deterministica, com teto (mecanica).

Nenhum criterio de revisao vive aqui. Cada correcao mexe so em `layout`/`assets` do
briefing -- parametros de composicao. Nenhuma toca em texto, oferta, preco ou dado.

O que NAO e corrigivel automaticamente esta em BLOQUEADAS e sempre volta ao humano.

Uso:
    autofix.py list
    autofix.py apply --job <dir> --from-version N --fix <nome> [--fix <nome> ...]
                     [--set chave=valor] [--reason "<linha do parecer>"]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Motivos que o Designer NUNCA resolve sozinho. Aparecendo qualquer um destes no parecer,
# o ciclo para e o caso vai para o usuario.
BLOQUEADAS = {
    "posicionamento estrategico de marca",
    "promessa comercial",
    "preco",
    "informacao factual",
    "mudanca de oferta",
    "alteracao de tom sensivel",
    "dado nao confirmado",
}


def _num(layout: dict, key: str, default: float) -> float:
    try:
        return float(layout.get(key, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- correcoes
# Cada correcao: (descricao, funcao(brief, arg) -> (mudou?, detalhe)).
# Todas tem teto: aplicar a mesma correcao varias vezes nao degrada a peca indefinidamente.

def fix_text_overflow(brief: dict, arg=None):
    """Abre espaco para o texto: encolhe a area da foto; se nao houver, baixa o corpo base."""
    lay = brief.setdefault("layout", {})
    if "photo_h_pct" in lay or brief.get("template") == "editorial":
        cur = _num(lay, "photo_h_pct", 60)
        new = max(42.0, cur - 6)
        if new == cur:
            return False, "area da foto ja no minimo (42%)"
        lay["photo_h_pct"] = round(new, 1)
        return True, f"photo_h_pct {cur} -> {new} (mais espaco para o texto)"
    cur = _num(lay, "headline_size", 76)
    new = max(40.0, cur - 6)
    if new == cur:
        return False, "headline_size ja no minimo (40px)"
    lay["headline_size"] = round(new, 1)
    return True, f"headline_size {cur} -> {new}"


def fix_contrast_up(brief: dict, arg=None):
    """Aumenta o escurecimento sob o texto sobreposto a foto."""
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "scrim", 82)
    new = min(96.0, cur + 8)
    if new == cur:
        return False, "scrim ja no maximo (96)"
    lay["scrim"] = round(new, 1)
    return True, f"scrim {cur} -> {new} (mais contraste do texto sobre a foto)"


def fix_headline_down(brief: dict, arg=None):
    """Reduz o corpo base da headline. Nao altera o texto."""
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "headline_size", 68)
    new = max(38.0, cur - 8)
    if new == cur:
        return False, "headline_size ja no minimo (38px)"
    lay["headline_size"] = round(new, 1)
    return True, f"headline_size {cur} -> {new}"


def fix_headline_up(brief: dict, arg=None):
    """Aumenta o corpo base da headline quando ficou pequena demais."""
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "headline_size", 68)
    new = min(110.0, cur + 8)
    if new == cur:
        return False, "headline_size ja no maximo (110px)"
    lay["headline_size"] = round(new, 1)
    return True, f"headline_size {cur} -> {new}"


def fix_margins_up(brief: dict, arg=None):
    """Aumenta a margem lateral: afasta o conteudo da borda."""
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "pad_pct", 6.3)
    new = min(12.0, cur + 1.5)
    if new == cur:
        return False, "margem ja no maximo (12%)"
    lay["pad_pct"] = round(new, 2)
    return True, f"pad_pct {cur}% -> {new}%"


def fix_cta_up(brief: dict, arg=None):
    """Aumenta o CTA."""
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "cta_scale", 1)
    new = min(1.6, cur + 0.15)
    if new == cur:
        return False, "cta ja no maximo (1.6x)"
    lay["cta_scale"] = round(new, 2)
    return True, f"cta_scale {cur} -> {new}"


def fix_logo_up(brief: dict, arg=None):
    """Aumenta o logo."""
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "logo_scale", 1)
    new = min(1.8, cur + 0.2)
    if new == cur:
        return False, "logo ja no maximo (1.8x)"
    lay["logo_scale"] = round(new, 2)
    return True, f"logo_scale {cur} -> {new}"


def fix_align(brief: dict, arg=None):
    """Troca o alinhamento do bloco de texto. arg: left|center."""
    val = (arg or "left").strip()
    if val not in ("left", "center"):
        return False, f"alinhamento invalido: {val}"
    lay = brief.setdefault("layout", {})
    if lay.get("align") == val:
        return False, f"alinhamento ja e {val}"
    lay["align"] = val
    return True, f"align -> {val}"


def fix_photo_pos(brief: dict, arg=None):
    """Ajusta o ponto focal do corte. arg: valor CSS object-position, ex: 'center 25%'."""
    if not arg:
        return False, "photo_pos exige --set photo_pos=<valor>"
    lay = brief.setdefault("layout", {})
    old = lay.get("photo_pos", "center")
    if old == arg:
        return False, f"photo_pos ja e {arg}"
    lay["photo_pos"] = arg
    return True, f"photo_pos '{old}' -> '{arg}' (corrige o enquadramento)"


def fix_swap_photo(brief: dict, arg=None):
    """Troca a foto por outra do acervo do cliente. arg: nome do arquivo."""
    if not arg:
        return False, "swap_photo exige --set swap_photo=<arquivo>"
    assets = brief.setdefault("assets", {})
    old = assets.get("photo")
    if old == arg:
        return False, f"foto ja e {arg}"
    assets["photo"] = arg
    return True, f"photo '{old}' -> '{arg}'"


def fix_asset_missing(brief: dict, arg=None):
    """Repoe um asset ausente. arg: chave=arquivo."""
    if not arg or "=" not in arg:
        return False, "asset_missing exige --set asset_missing=<chave>=<arquivo>"
    key, val = arg.split("=", 1)
    brief.setdefault("assets", {})[key.strip()] = val.strip()
    return True, f"asset '{key.strip()}' -> '{val.strip()}'"


def fix_mark_scrim_up(brief: dict, arg=None):
    """Cria/reforca a faixa de leitura sob a assinatura no topo da peca.

    Para quando o logo cai sobre uma regiao clara da fotografia e a marca some.
    """
    lay = brief.setdefault("layout", {})
    cur = _num(lay, "mark_scrim", 0)
    new = min(78.0, (cur if cur else 30.0) + (0 if cur == 0 else 14))
    if new == cur:
        return False, "faixa do topo ja no maximo (78)"
    lay["mark_scrim"] = round(new, 1)
    return True, f"mark_scrim {cur} -> {new} (base de leitura para a assinatura no topo)"


CATALOGO = {
    "text_overflow": ("texto estourando / sem respiro: abre espaco para o bloco de texto", fix_text_overflow),
    "contrast_up": ("contraste baixo do texto sobre foto: aumenta o escurecimento", fix_contrast_up),
    "mark_scrim_up": ("logo/assinatura sem contraste sobre foto clara: cria faixa de leitura no topo", fix_mark_scrim_up),
    "headline_down": ("headline grande/longa demais para o espaco: reduz o corpo base", fix_headline_down),
    "headline_up": ("headline pequena demais: aumenta o corpo base", fix_headline_up),
    "min_size_up": ("texto abaixo do minimo legivel: aumenta o corpo base", fix_headline_up),
    "margins_up": ("conteudo colado na borda: aumenta a margem lateral", fix_margins_up),
    "cta_up": ("CTA pouco legivel ou pouco evidente: aumenta o CTA", fix_cta_up),
    "logo_up": ("logo pequeno demais: aumenta o logo", fix_logo_up),
    "align": ("alinhamento inadequado: troca left/center (--set align=center)", fix_align),
    "photo_pos": ("crop ruim: reposiciona o ponto focal (--set photo_pos='center 25%')", fix_photo_pos),
    "swap_photo": ("crop ruim sem solucao por enquadramento: troca a foto (--set swap_photo=arquivo.jpg)", fix_swap_photo),
    "asset_missing": ("asset ausente: repoe (--set asset_missing=chave=arquivo)", fix_asset_missing),
}


def apply_fixes(job_dir: pathlib.Path, from_version: int, fixes: list[str],
                params: dict, reasons: list[str]) -> dict:
    src = job_dir / f"brief.v{from_version}.json"
    brief = json.loads(src.read_text(encoding="utf-8"))

    applied, skipped, unknown = [], [], []
    for name in fixes:
        if name not in CATALOGO:
            unknown.append(name)
            continue
        desc, fn = CATALOGO[name]
        changed, detail = fn(brief, params.get(name))
        (applied if changed else skipped).append(
            {"fix": name, "efeito": detail, "descricao": desc})

    to_version = from_version + 1
    (job_dir / f"brief.v{to_version}.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changes = {
        "de_versao": from_version, "para_versao": to_version,
        "motivos_do_parecer": reasons,
        "aplicadas": applied, "sem_efeito": skipped, "desconhecidas": unknown,
        "nao_automatizaveis": sorted(BLOQUEADAS),
    }
    (job_dir / f"changes-v{from_version}.json").write_text(
        json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(fn="list")

    p = sub.add_parser("apply")
    p.add_argument("--job", required=True)
    p.add_argument("--from-version", type=int, required=True)
    p.add_argument("--fix", action="append", default=[], help="nome da correcao (repetivel)")
    p.add_argument("--set", action="append", default=[], metavar="chave=valor",
                   help="parametro de uma correcao (repetivel)")
    p.add_argument("--reason", action="append", default=[],
                   help="linha do parecer que motivou a correcao (repetivel)")
    p.set_defaults(fn="apply")

    a = ap.parse_args()

    if a.fn == "list":
        print(f"{'correcao':16} descricao")
        for k, (d, _) in CATALOGO.items():
            print(f"{k:16} {d}")
        print("\nNUNCA automatico (sempre volta ao humano):")
        for b in sorted(BLOQUEADAS):
            print(f"  - {b}")
        return 0

    params: dict = {}
    for s in a.set:
        if "=" not in s:
            print(f"ERRO: --set espera chave=valor, recebi '{s}'", file=sys.stderr)
            return 2
        k, v = s.split("=", 1)
        params[k.strip()] = v.strip()

    if not a.fix:
        print("ERRO: nenhuma correcao indicada (--fix)", file=sys.stderr)
        return 2

    changes = apply_fixes(pathlib.Path(a.job).expanduser().resolve(),
                          a.from_version, a.fix, params, a.reason)
    print(json.dumps(changes, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
