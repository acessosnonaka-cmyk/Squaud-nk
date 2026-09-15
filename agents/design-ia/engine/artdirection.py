#!/usr/bin/env python3
"""Direcao de arte: da decisao criativa ao briefing tecnico.

O Designer nao escolhe template. Ele toma uma DECISAO DE DIRECAO (art-direction.json) --
conceito, elemento dominante, tipografia, composicao, camadas -- e este modulo a compila
num briefing que o `render.py` sabe executar.

Duas razoes para existir:
  1. a peca passa a ter um porque registrado, legivel depois;
  2. a composicao vira parametro, nao arquivo -- nada de template por nicho ou cliente.

As familias (editorial/promocional/minimal) sobrevivem como PRESETS de parametros: um
ponto de partida que a direcao de arte sobrescreve a vontade.

Uso:
    artdirection.py schema                      esqueleto comentado
    artdirection.py fonts [--personality X]     consulta o pool
    artdirection.py compile --job <dir> --version N
    artdirection.py explain --job <dir>
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
POOL_DIR = ROOT / "fonts" / "pool"
POOL_JSON = ROOT / "fonts" / "pool.json"

# --------------------------------------------------------------------------- presets

# Ponto de partida por familia. Tudo aqui pode ser sobrescrito pela direcao de arte.
PRESETS = {
    "editorial": {
        "image_mode": "split-top", "text_position": "block-bottom",
        "brand_position": "bar", "cta_style": "none", "dominance": "balanced",
        "split_pct": 58, "scrim": 0, "gap_pct": 2.6, "pad_pct": 6.6,
    },
    "promocional": {
        "image_mode": "full", "text_position": "overlay",
        "brand_position": "top", "cta_style": "button", "dominance": "image",
        "scrim": 84, "scrim_from": "bottom", "gap_pct": 2.2, "pad_pct": 6.6,
    },
    "minimal": {
        "image_mode": "none", "text_position": "center",
        "brand_position": "minimal", "cta_style": "text", "dominance": "typography",
        "scrim": 0, "gap_pct": 3.0, "pad_pct": 8.0, "bg_role": "paper",
    },
    # As duas familias abaixo existem para ACERVO LIMITADO: foto que nao tem largura
    # nativa para sangrar a peca (faixa horizontal, frame de video, retrato vertical
    # pequeno). Sem elas, esse material vira descarte e a peca cai no `minimal` -- foi
    # o que produziu um ad set inteiro de cards so tipograficos.
    # Diferente das tres de cima, elas TEM arquivo proprio em templates/: a chave
    # "template" roteia para la. Quem nao declara a chave continua no `composer`.
    "faixa": {
        "template": "faixa",
        "image_mode": "split-top", "text_position": "block-bottom",
        "brand_position": "top", "cta_style": "text", "dominance": "balanced",
        "band_h_pct": 34, "band_y": "topo", "gap_pct": 3.4, "pad_pct": 7.4,
        "bg_role": "paper",
    },
    "retrato": {
        "template": "retrato",
        "image_mode": "split-left", "text_position": "split-right",
        "brand_position": "top", "cta_style": "text", "dominance": "balanced",
        "col_w_pct": 42, "photo_side": "left", "photo_shape": "coluna",
        "pad_pct": 7.0, "bg_role": "paper",
    },
}

# Corpo de cada papel como fracao da ALTURA do formato. Papeis diferentes tem
# multiplicadores diferentes -- nao sao variacoes de uma unica escala.
SCALE = {
    "typography": {"display": .155, "headline": .086, "subheadline": .032,
                   "body": .0205, "caption": .0135, "eyebrow": .0165,
                   "cta": .022, "signature": .019},
    "balanced":   {"display": .130, "headline": .068, "subheadline": .028,
                   "body": .0200, "caption": .0135, "eyebrow": .0155,
                   "cta": .021, "signature": .018},
    "image":      {"display": .105, "headline": .053, "subheadline": .0255,
                   "body": .0190, "caption": .0130, "eyebrow": .0150,
                   "cta": .020, "signature": .017},
}

# Contraste de escala: afasta ou aproxima os extremos da hierarquia.
CONTRAST = {"baixo": 0.85, "medio": 1.0, "alto": 1.18, "extremo": 1.34}

# Defaults tipograficos por papel. A direcao de arte sobrescreve o que quiser.
ROLE_DEFAULTS = {
    "display":     {"weight": 400, "tracking": "-.03em", "leading": ".92", "case": "uppercase", "measure": "100%"},
    "headline":    {"weight": 400, "tracking": "-.02em", "leading": "1.0", "case": "none", "measure": "100%"},
    "subheadline": {"weight": 400, "tracking": "0", "leading": "1.3", "case": "none", "measure": "88%"},
    "body":        {"weight": 400, "tracking": "0", "leading": "1.45", "case": "none", "measure": "86%"},
    "caption":     {"weight": 500, "tracking": ".04em", "leading": "1.35", "case": "none", "measure": "90%"},
    "eyebrow":     {"weight": 700, "tracking": ".18em", "leading": "1.2", "case": "uppercase", "measure": "100%"},
    "cta":         {"weight": 700, "tracking": ".03em", "leading": "1", "case": "none", "measure": "100%"},
    "signature":   {"weight": 600, "tracking": ".06em", "leading": "1", "case": "none", "measure": "100%"},
}

ROLES = list(ROLE_DEFAULTS)

# `dominant_element` e `composition.dominance` usam vocabularios proximos mas nao iguais.
# Sem normalizar, "photography" caia no default silenciosamente e a escala saia errada.
DOMINANCE_ALIASES = {
    "photography": "image", "photo": "image", "foto": "image", "fotografia": "image",
    "image": "image", "imagem": "image",
    "typography": "typography", "type": "typography", "tipografia": "typography",
    "product": "image", "produto": "image", "graphic": "balanced", "grafico": "balanced",
    "balanced": "balanced", "equilibrado": "balanced",
}


def normalize_dominance(v: str) -> str:
    key = (v or "balanced").strip().lower()
    if key not in DOMINANCE_ALIASES:
        raise SystemExit(f"ERRO: dominancia desconhecida '{v}'. "
                         f"Use uma de: {sorted(set(DOMINANCE_ALIASES))}")
    return DOMINANCE_ALIASES[key]

SCHEMA = """{
  "concept": "a ideia da peca em uma frase",
  "rationale": "por que esta direcao e nao outra (curto)",
  "visual_tone": "ex: sobrio e artesanal / clinico e acolhedor",
  "dominant_element": "photography | typography | product | graphic",

  "typographic_direction": {
    "fonts": { "display": "<chave do pool>", "body": "<chave do pool>" },
    "font_source": "brand | pool",
    "scale_contrast": "baixo | medio | alto | extremo",
    "roles": {
      "headline": { "font": "display", "weight": 700, "case": "none",
                    "tracking": "-.02em", "leading": "1.02", "measure": "94%",
                    "size_mult": 1.0, "color_role": "ink" }
    },
    "emphasis_rationale": "por que ha (ou nao ha) enfase na headline"
  },

  "composition": {
    "family": "editorial | promocional | minimal | faixa | retrato",
    "image_mode": "full | background | bleed | split-top | split-bottom | split-left | split-right | inset | none",
    "text_position": "overlay | edge-top | block-top | block-bottom | split-left | split-right | floating | center",
    "alignment": "left | center | right",
    "dominance": "image | typography | balanced",
    "brand_position": "top | bottom | bar | integrated | minimal",
    "cta_style": "button | pill | text | underline | none",
    "params": { "split_pct": 58, "pad_pct": 6.6, "gap_pct": 2.6, "photo_pos": "center" }
  },

  "layers": ["photography", "scrim", "shapes", "texture", "decorative-type",
             "primary-type", "secondary-type", "cta", "brand-signature"],

  "photo_treatment": { "saturate": 100, "contrast": 100, "brightness": 100, "sepia": 0,
                       "reading": "onde esta o assunto, area livre, onde o texto pode entrar" },

  "brand_role": "como a marca participa da peca",
  "cta_role": "qual acao a peca pede, ou por que nao pede nenhuma",

  "copy": {
    "eyebrow": "", "headline": "", "subheadline": "", "body": "", "caption": "", "cta": "",
    "headline_parts": [
      { "text": "trecho secundario", "role": "lead" },
      { "text": "trecho dominante", "role": "strong accent" }
    ]
  },

  "assets": { "photo": "arquivo.jpg" },
  "logos": { "logo": "reverse" },

  "creative_decisions": ["decisoes relevantes que um humano precisaria entender depois"]
}"""


def load_pool() -> dict:
    return json.loads(POOL_JSON.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- tipografia

def resolve_fonts(ad: dict, brand: dict) -> tuple[list[dict], dict, list[str]]:
    """Decide as familias da peca.

    Tipografia oficial do cliente tem prioridade absoluta. O pool so entra quando o
    cliente nao tem tipografia confirmada -- e, nesse caso, e decisao criativa DO JOB,
    registrada como tal. Nunca vira identidade do cliente.
    """
    notas: list[str] = []
    td = ad.get("typographic_direction", {})
    official = bool((brand.get("typography") or {}).get("official")) or bool(brand.get("fonts"))

    pedido = td.get("fonts") or {}
    forcar_pool = td.get("font_source") == "pool"

    if official and not forcar_pool:
        fonts = list(brand.get("fonts", []))
        fam = {"display": (brand.get("type") or {}).get("display", "Brand Display"),
               "body": (brand.get("type") or {}).get("text", "Brand Text")}
        notas.append("tipografia oficial do cliente (brand kit) — prioridade sobre o pool")
        return fonts, fam, notas

    pool = load_pool()["families"]
    fonts, fam = [], {}
    for papel, chave in (("display", pedido.get("display")), ("body", pedido.get("body")),
                         ("alt", pedido.get("alt"))):
        if not chave:
            continue
        if chave not in pool:
            raise SystemExit(f"ERRO: fonte '{chave}' nao esta no pool. "
                             f"Veja: artdirection.py fonts")
        meta = pool[chave]
        familia = f"Pool {chave}"
        fonts.append({"family": familia, "file": str(POOL_DIR / meta["file"]),
                      "weight": meta["weights"]})
        fam[papel] = familia
        notas.append(f"{papel}: '{chave}' ({meta['class']}, {meta['license']}) — "
                     f"escolha criativa deste job, NAO e identidade do cliente")

    if not fonts:
        raise SystemExit("ERRO: sem tipografia. O cliente nao tem fontes no brand kit e a "
                         "direcao de arte nao escolheu nenhuma do pool.")
    fam.setdefault("body", fam.get("display"))
    fam.setdefault("display", fam.get("body"))
    return fonts, fam, notas


def build_type_vars(ad: dict, fmt_h: int, fam: dict) -> tuple[str, dict]:
    """Gera as variaveis CSS de cada papel tipografico."""
    td = ad.get("typographic_direction", {})
    comp = ad.get("composition", {})
    dom = normalize_dominance(comp.get("dominance", "balanced"))
    scale = SCALE[dom]
    k = CONTRAST.get(td.get("scale_contrast", "medio"), 1.0)
    roles_cfg = td.get("roles", {})

    # o contraste afasta os extremos: amplia o topo da hierarquia, encolhe a base
    def contrast_factor(role: str) -> float:
        if role in ("display", "headline"):
            return k
        if role in ("body", "caption"):
            return 1 / (1 + (k - 1) * 0.55)
        return 1.0

    out, resumo = [], {}
    for role in ROLES:
        d = dict(ROLE_DEFAULTS[role])
        cfg = roles_cfg.get(role, {})
        d.update({kk: vv for kk, vv in cfg.items() if vv is not None})

        px = fmt_h * scale[role] * contrast_factor(role) * float(cfg.get("size_mult", 1.0))
        px = round(px, 1)

        fonte = fam.get(cfg.get("font", "display" if role in ("display", "headline") else "body"),
                        fam.get("body"))
        short = {"display": "display", "headline": "headline", "subheadline": "sub",
                 "body": "body", "caption": "caption", "eyebrow": "eyebrow",
                 "cta": "cta", "signature": "sig"}[role]

        out.append(f"--font-{short}:'{fonte}';")
        out.append(f"--s-{short}:{px}px;")
        out.append(f"--w-{short}:{d['weight']};")
        out.append(f"--t-{short}:{d['tracking']};")
        out.append(f"--l-{short}:{d['leading']};")
        out.append(f"--m-{short}:{d['measure']};")
        out.append(f"--c-case-{short}:{d['case']};")
        resumo[role] = {"px": px, "weight": d["weight"], "case": d["case"],
                        "tracking": d["tracking"], "leading": d["leading"],
                        "measure": d["measure"], "font": fonte}

    # enfase dentro da headline
    hl = resumo["headline"]
    emf = td.get("emphasis", {})
    out.append(f"--e-lead:{round(hl['px'] * float(emf.get('lead_mult', .46)), 1)}px;")
    out.append(f"--e-lead-w:{emf.get('lead_weight', 500)};")
    out.append(f"--e-lead-t:{emf.get('lead_tracking', '.14em')};")
    out.append(f"--e-strong-w:{emf.get('strong_weight', 800)};")
    out.append(f"--font-lead:'{fam.get(emf.get('lead_font', 'body'), fam.get('body'))}';")
    out.append(f"--font-alt:'{fam.get(emf.get('alt_font', 'display'), fam.get('display'))}';")
    out.append(f"--font-display:'{fam.get('display')}';")
    return "".join(out), resumo


def build_headline(ad: dict) -> tuple[str, bool]:
    """Monta a headline, com enfase semantica quando o job pedir.

    Sem `headline_parts`, a headline sai como texto simples -- que e o caso normal.
    Enfase so quando ha motivo de comunicacao, nunca por enfeite.
    """
    copy = ad.get("copy", {})
    parts = copy.get("headline_parts")
    if not parts:
        return html.escape(copy.get("headline", "")), False

    frag = []
    for p in parts:
        texto = html.escape(p.get("text", ""))
        papel = (p.get("role") or "").strip()
        classes = " ".join(c for c in papel.split() if c in ("lead", "strong", "accent", "alt"))
        frag.append(f'<span class="{classes}">{texto}</span>' if classes else texto)
        if p.get("break_after"):
            frag.append("<br>")
    # 'lead' ja e bloco; os demais fluem separados por espaco
    montado = ""
    for i, f in enumerate(frag):
        if i and not f.startswith("<br>") and not frag[i - 1].endswith("<br>"):
            montado += " "
        montado += f
    return montado, True


# --------------------------------------------------------------------------- compile

def compile_ad(job_dir: pathlib.Path, version: int) -> dict:
    ad_path = job_dir / "art-direction.json"
    if not ad_path.is_file():
        raise SystemExit(f"ERRO: {ad_path} nao existe. Escreva a direcao de arte antes "
                         f"(veja: artdirection.py schema)")
    ad = json.loads(ad_path.read_text(encoding="utf-8"))
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

    snap = job_dir / "brand.snapshot.json"
    brand = json.loads(snap.read_text(encoding="utf-8")) if snap.is_file() else {}

    comp = dict(ad.get("composition", {}))
    preset = dict(PRESETS.get(comp.get("family", "editorial"), PRESETS["editorial"]))
    # Familia com arquivo proprio de template roda nele; as demais seguem no sistema
    # de composicao. Preset sem a chave "template" mantem exatamente o que havia antes.
    template = preset.pop("template", "composer")
    params = dict(preset)
    for kk in ("image_mode", "text_position", "brand_position", "cta_style", "dominance"):
        if comp.get(kk):
            params[kk] = comp[kk]
    params["align"] = comp.get("alignment", "left")
    params["items"] = {"left": "flex-start", "center": "center", "right": "flex-end"}[params["align"]]
    params.update(comp.get("params", {}))

    fmt = json.loads((ROOT / "formats.json").read_text(encoding="utf-8"))["formats"]
    fname = job.get("format_name") or "instagram-feed"
    f = fmt.get(fname) or next((v for v in fmt.values() if fname in v.get("aliases", [])), None)
    if f is None:
        raise SystemExit(f"ERRO: formato desconhecido '{fname}'")

    fonts, fam, notas = resolve_fonts(ad, brand)
    type_vars, resumo = build_type_vars(ad, int(f["h"]), fam)
    headline_html, tem_enfase = build_headline(ad)

    layers = ad.get("layers", [])
    tr = ad.get("photo_treatment", {})
    copy = ad.get("copy", {})

    layout = dict(params)
    layout["type_vars"] = type_vars
    layout["treat_saturate"] = tr.get("saturate", 100)
    layout["treat_contrast"] = tr.get("contrast", 100)
    layout["treat_brightness"] = tr.get("brightness", 100)
    layout["treat_sepia"] = tr.get("sepia", 0)
    if "texture" not in layers:
        layout["texture"] = 0
    if "decorative-type" not in layers:
        layout["deco_opacity"] = 0
        layout["deco_text"] = ""
    if "scrim" not in layers:
        layout["scrim"] = 0
    # texto sobre foto precisa ser medido contra a foto, nao contra a cor do bloco
    sobre_foto = params.get("text_position") in ("overlay", "edge-top", "center") and \
        params.get("image_mode") not in ("none",)
    layout["over_image"] = "data-over-image" if sobre_foto else ""
    layout["sig_over_image"] = "data-over-image" if params.get("brand_position") == "top" else ""

    brief = {
        "client": job["client"],
        "name": job.get("name", "peca"),
        "template": template,
        "format": fname,
        "fonts": fonts,
        # Papeis tipograficos resolvidos, no formato do brand kit. As familias que
        # consomem `type_vars` nao precisam disto, mas `faixa` e `retrato` tem defaults
        # proprios e leem --font-display/--font-text direto: sem este mapa elas caem no
        # sans-serif generico e a peca perde a tipografia inteira, calada.
        "type": {"display": fam.get("display"), "text": fam.get("body")},
        "layout": layout,
        # Repassa TODA chave de copy escrita pelo autor, nao uma lista branca.
        # A lista branca descartava em silencio qualquer token que a familia usasse
        # e que nao estivesse previsto aqui (ex.: `support` nas familias faixa/retrato):
        # o texto sumia da peca e o validate passava, porque token vazio e legitimo.
        # `headline_parts` fica de fora: e insumo para montar a headline, nao token.
        "copy": {
            # base historica: estas seis sempre existiram no brief, mesmo vazias.
            # Mantidas para nao quebrar template que conte com a chave presente.
            "eyebrow": "", "subheadline": "", "body": "", "caption": "", "cta": "",
            # e entao TODA chave escrita pelo autor, sem lista branca.
            **{k: v for k, v in copy.items() if k != "headline_parts"},
            "headline": headline_html,
        },
        "assets": ad.get("assets", {}),
        "logos": ad.get("logos", {}),
    }
    dest = job_dir / f"brief.v{version}.json"
    dest.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # a compilacao devolve para o art-direction o que foi de fato resolvido
    ad.setdefault("_resolved", {})
    ad["_resolved"] = {
        "version": version,
        "composition_params": params,
        "typography": resumo,
        "font_notes": notas,
        "headline_com_enfase": tem_enfase,
        "layers_ativas": layers,
        "brief": str(dest),
    }
    ad_path.write_text(json.dumps(ad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"brief": str(dest), "params": params, "typography": resumo, "font_notes": notas}


# --------------------------------------------------------------------------- cli

def cmd_schema(_a) -> int:
    print(SCHEMA)
    return 0


def cmd_fonts(a) -> int:
    pool = load_pool()
    fams = pool["families"]
    if a.personality:
        fams = {k: v for k, v in fams.items() if a.personality.lower() in
                [p.lower() for p in v["personality"]]}
    if a.klass:
        fams = {k: v for k, v in fams.items() if a.klass.lower() in v["class"].lower()}
    if a.json:
        print(json.dumps(fams, ensure_ascii=False, indent=2))
        return 0
    print(f"{'chave':18} {'classe':22} {'pesos':10} personalidade")
    for k, v in fams.items():
        print(f"{k:18} {v['class']:22} {v['weights']:10} {', '.join(v['personality'])}")
    if not a.personality and not a.klass:
        print("\nOrientacao de par:")
        for g in pool["pairing_guidance"]:
            print(f"  - {g}")
    return 0


def cmd_compile(a) -> int:
    r = compile_ad(pathlib.Path(a.job).expanduser().resolve(), a.version)
    print(r["brief"])
    print("composicao: " + ", ".join(f"{k}={v}" for k, v in r["params"].items()
                                     if k in ("image_mode", "text_position", "dominance",
                                              "brand_position", "cta_style", "align")),
          file=sys.stderr)
    print("hierarquia: " + ", ".join(f"{k}={v['px']}px/{v['weight']}"
                                     for k, v in r["typography"].items()
                                     if k in ("headline", "subheadline", "body", "eyebrow")),
          file=sys.stderr)
    for n in r["font_notes"]:
        print(f"fonte: {n}", file=sys.stderr)
    return 0


def cmd_explain(a) -> int:
    ad = json.loads((pathlib.Path(a.job).expanduser().resolve() /
                     "art-direction.json").read_text(encoding="utf-8"))
    print(f"CONCEITO      {ad.get('concept', '?')}")
    print(f"POR QUE       {ad.get('rationale', '?')}")
    print(f"TOM           {ad.get('visual_tone', '?')}")
    print(f"DOMINANTE     {ad.get('dominant_element', '?')}")
    print(f"MARCA         {ad.get('brand_role', '?')}")
    print(f"CTA           {ad.get('cta_role', '?')}")
    print(f"CAMADAS       {', '.join(ad.get('layers', []))}")
    res = ad.get("_resolved", {})
    if res:
        print("\nCOMPOSICAO")
        for k, v in res.get("composition_params", {}).items():
            if k not in ("type_vars",):
                print(f"  {k:16} {v}")
        print("\nHIERARQUIA TIPOGRAFICA")
        for k, v in res.get("typography", {}).items():
            print(f"  {k:12} {v['px']:>6}px  peso {v['weight']:<4} {v['case']:<10} "
                  f"tracking {v['tracking']:<7} leading {v['leading']:<5} {v['font']}")
        print("\nFONTES")
        for n in res.get("font_notes", []):
            print(f"  - {n}")
    if ad.get("creative_decisions"):
        print("\nDECISOES CRIATIVAS")
        for d in ad["creative_decisions"]:
            print(f"  - {d}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)
    p = sub.add_parser("fonts"); p.add_argument("--personality"); p.add_argument("--klass")
    p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_fonts)
    p = sub.add_parser("compile"); p.add_argument("--job", required=True)
    p.add_argument("--version", type=int, default=1); p.set_defaults(fn=cmd_compile)
    p = sub.add_parser("explain"); p.add_argument("--job", required=True); p.set_defaults(fn=cmd_explain)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
