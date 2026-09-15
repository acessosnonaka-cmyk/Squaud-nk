#!/usr/bin/env python3
"""Motor de render do Designer IA: brand kit + briefing + template -> PNG.

Generico por construcao. Nada aqui conhece cliente, cor, fonte, texto ou layout:
  - identidade  vem de clients/<slug>/brand.json
  - dimensoes   vem de formats.json
  - composicao  vem de templates/<familia>.html
  - conteudo    vem do briefing

Uso:
    python3 render.py --brief <brief.json> [--out <arquivo.png>]

O briefing e a unica entrada obrigatoria; ele aponta para cliente, template e formato.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
FONTS = ROOT / "fonts"
CLIENTS = ROOT / "clients"
OUTPUT = ROOT / "output"

MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
}

# Piso de legibilidade: abaixo disto o auto-fit para de encolher e reporta o estouro
# em vez de entregar texto ilegivel.
MIN_SCALE = 0.55

# {{token}} ou {{token=valor padrao}}
TOKEN_RE = re.compile(r"\{\{(\w+)(?:=([^}]*))?\}\}")


class RenderError(Exception):
    pass


# --------------------------------------------------------------------------- ambiente

def chromium_env() -> dict:
    """Ambiente do processo do Chromium.

    Neste host faltam libnss3/libnspr4 no sistema. As libs vivem em runtime/lib/ e sao
    injetadas SO no processo do browser -- nao exigem root, nao alteram o sistema e nao
    dependem de o usuario exportar nada. Se um dia forem instaladas via apt, este
    caminho extra passa a ser inofensivo.
    """
    env = dict(os.environ)
    libdir = ROOT / "runtime" / "lib"
    if libdir.is_dir():
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{libdir}:{prev}" if prev else str(libdir)
    return env


# --------------------------------------------------------------------------- assets

def data_uri(path: pathlib.Path) -> str:
    """Embute o arquivo no HTML.

    Todo asset vira data URI: o HTML final nao faz nenhuma requisicao externa, entao o
    render funciona offline e o resultado e reproduzivel.
    """
    p = pathlib.Path(path).expanduser()
    if not p.is_file():
        raise RenderError(f"asset nao encontrado: {p}")
    mime = MIME.get(p.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def resolve(path: str, *bases: pathlib.Path) -> pathlib.Path:
    """Resolve um caminho: absoluto, ou relativo a uma das bases, na ordem dada."""
    p = pathlib.Path(path).expanduser()
    if p.is_absolute():
        return p
    for b in bases:
        cand = (b / p)
        if cand.exists():
            return cand.resolve()
    return (bases[0] / p).resolve() if bases else p.resolve()


# --------------------------------------------------------------------------- brand

def build_font_face(brand: dict, client_dir: pathlib.Path, extra: list | None = None) -> str:
    """Fontes da peca: as do brand kit mais as que a direcao de arte escolheu do pool.

    `extra` permite ao job trazer familias que nao pertencem a identidade do cliente --
    decisao criativa daquela peca, registrada em art-direction.json.
    """
    css = []
    for f in list(brand.get("fonts", [])) + list(extra or []):
        p = resolve(f["file"], client_dir / "fonts", client_dir, FONTS / "pool", FONTS, ROOT)
        css.append(
            "@font-face{font-family:'%s';src:url('%s') format('woff2');"
            "font-weight:%s;font-style:%s;font-display:block;}"
            % (f["family"], data_uri(p), f.get("weight", "400"), f.get("style", "normal"))
        )
    t = brand.get("type", {})
    css.append(":root{--font-display:'%s';--font-text:'%s';}"
               % (t.get("display", "sans-serif"), t.get("text", "sans-serif")))
    return "".join(css)


def build_palette(brand: dict) -> str:
    return "".join(f"--c-{k}:{v};" for k, v in brand.get("palette", {}).items())


def load_brand(slug: str) -> tuple[dict, pathlib.Path]:
    d = CLIENTS / slug
    f = d / "brand.json"
    if not f.is_file():
        raise RenderError(
            f"brand kit inexistente para '{slug}'. Crie com: "
            f"python3 {ROOT/'brand.py'} init --slug {slug} --name '<Nome>'")
    return json.loads(f.read_text(encoding="utf-8")), d


def load_format(spec) -> dict:
    """Aceita nome, alias ou objeto inline {w,h,scale}."""
    if isinstance(spec, dict):
        return {"w": int(spec["w"]), "h": int(spec["h"]),
                "scale": float(spec.get("scale", 1)), "label": spec.get("label", "custom"),
                "safe": spec.get("safe", {})}
    data = json.loads((ROOT / "formats.json").read_text(encoding="utf-8"))["formats"]
    if spec in data:
        f = data[spec]
    else:
        f = next((v for v in data.values() if spec in v.get("aliases", [])), None)
        if f is None:
            raise RenderError(f"formato desconhecido: '{spec}'. Disponiveis: {list(data)}")
    return {"w": int(f["w"]), "h": int(f["h"]), "scale": float(f.get("scale", 1)),
            "label": f.get("label", spec), "safe": f.get("safe", {})}


# --------------------------------------------------------------------------- auto-fit

# Roda no browser depois das fontes carregarem. Cada escopo (data-fit-scope) encolhe
# proporcionalmente os filhos marcados com data-fit ate o conteudo caber, por busca
# binaria. Substitui o <br> manual do prototipo.
AUTOFIT_JS = r"""
(minScale) => {
  const report = { scopes: [], overflow: [] };
  const scopes = document.querySelectorAll('[data-fit-scope]');

  for (const scope of scopes) {
    const items = [...scope.querySelectorAll('[data-fit]')];
    if (!items.length) continue;

    const base = items.map(el => parseFloat(getComputedStyle(el).fontSize));
    const floor = items.map(el => parseFloat(el.dataset.fitMin || '0'));

    const apply = (s) => items.forEach((el, i) => {
      el.style.fontSize = Math.max(base[i] * s, floor[i]) + 'px';
    });

    const fits = () => {
      if (scope.scrollHeight > scope.clientHeight + 1) return false;
      // palavra longa estourando a caixa na horizontal
      if (!items.every(el => el.scrollWidth <= el.clientWidth + 1)) return false;
      // Com justify-content:center o conteudo transborda para os DOIS lados e o
      // scrollHeight nao acusa. Comparar as caixas resolve -- mas contra a AREA DE
      // CONTEUDO, descontando o padding: e nele que mora a faixa reservada para a
      // assinatura ancorada, e um item ali ja colide.
      const s = scope.getBoundingClientRect();
      const cs = getComputedStyle(scope);
      const top = s.top + parseFloat(cs.paddingTop || 0);
      const bottom = s.bottom - parseFloat(cs.paddingBottom || 0);
      return items.every(el => {
        const r = el.getBoundingClientRect();
        return r.top >= top - 1 && r.bottom <= bottom + 1;
      });
    };

    apply(1);
    let scale = 1;
    if (!fits()) {
      let lo = minScale, hi = 1, best = minScale;
      for (let i = 0; i < 22 && hi - lo > 0.002; i++) {
        const mid = (lo + hi) / 2;
        apply(mid);
        if (fits()) { best = mid; lo = mid; } else { hi = mid; }
      }
      scale = best;
      apply(scale);
    }

    const ok = fits();
    report.scopes.push({
      scope: scope.dataset.fitScope,
      scale: +scale.toFixed(4),
      fits: ok,
      sizes: items.map((el, i) => ({
        el: el.dataset.fit,
        px: +parseFloat(getComputedStyle(el).fontSize).toFixed(1),
        min: floor[i] || null,
      })),
    });
    if (!ok) report.overflow.push(scope.dataset.fitScope);
  }
  return report;
};
"""

# Relatorio do DOM depois do fit: alimenta o validate.py com fatos medidos, nao estimados.
PROBE_JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const vh = document.documentElement.clientHeight;
  const out = { viewport: { w: vw, h: vh }, images: [], outside: [], remote: [], text: [] };

  for (const img of document.images) {
    const r = img.getBoundingClientRect();
    out.images.push({
      role: img.dataset.role || null,
      ok: img.complete && img.naturalWidth > 0,
      natural: [img.naturalWidth, img.naturalHeight],
      box: [Math.round(r.width), Math.round(r.height)],
      remote: !/^data:/.test(img.currentSrc || img.src || ''),
    });
  }

  // qualquer elemento marcado que escape do canvas
  for (const el of document.querySelectorAll('[data-fit],[data-role]')) {
    const r = el.getBoundingClientRect();
    if (r.left < -1 || r.top < -1 || r.right > vw + 1 || r.bottom > vh + 1) {
      out.outside.push({
        el: el.dataset.fit || el.dataset.role,
        box: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)],
      });
    }
  }

  // dependencia remota residual (o render final precisa ser 100% embutido)
  for (const n of document.querySelectorAll('img,link,script,source')) {
    const u = n.currentSrc || n.src || n.href || '';
    if (/^(https?:)?\/\//.test(u)) out.remote.push(u.slice(0, 120));
  }

  // amostra de cor para o check de contraste: texto marcado + fundo efetivo
  for (const el of document.querySelectorAll('[data-fit]')) {
    const cs = getComputedStyle(el);
    let bg = 'rgba(0, 0, 0, 0)', p = el;
    while (p && bg === 'rgba(0, 0, 0, 0)') { bg = getComputedStyle(p).backgroundColor; p = p.parentElement; }
    const r = el.getBoundingClientRect();
    out.text.push({
      el: el.dataset.fit,
      color: cs.color,
      bg,
      px: +parseFloat(cs.fontSize).toFixed(1),
      weight: cs.fontWeight,
      over_image: !!el.closest('[data-over-image]'),
      box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
    });
  }
  return out;
};
"""


# --------------------------------------------------------------------------- render

def build_html(brief: dict) -> tuple[str, dict, dict, pathlib.Path]:
    brand, client_dir = load_brand(brief["client"])
    fmt = load_format(brief["format"])

    tpl_name = brief["template"]
    tpl_path = TEMPLATES / (tpl_name if tpl_name.endswith(".html") else f"{tpl_name}.html")
    if not tpl_path.is_file():
        avail = sorted(p.stem for p in TEMPLATES.glob("*.html"))
        raise RenderError(f"template inexistente: '{tpl_name}'. Disponiveis: {avail}")
    tpl = tpl_path.read_text(encoding="utf-8")

    inst = brand.get("institutional", {})
    # quando o job traz fontes proprias, o brand kit deixa de ditar os nomes de familia:
    # quem manda sao os papeis resolvidos pela direcao de arte (`brief["type"]`).
    # Zerar o mapa aqui, como se fazia antes, so funcionava para as familias que
    # consomem `type_vars`; `faixa` e `retrato` leem --font-display/--font-text direto
    # e ficavam em sans-serif generico sem nada acusar. Brief sem `type` (caminho V2.1,
    # briefing tecnico pronto) mantem o comportamento antigo.
    brand_para_fontes = (brand if not brief.get("fonts")
                         else {**brand, "type": brief.get("type") or {}})
    tokens: dict = {
        "font_face": build_font_face(brand_para_fontes, client_dir, brief.get("fonts")),
        "palette": build_palette(brand),
        "format_w": fmt["w"], "format_h": fmt["h"],
        "brand_name": brand.get("name", ""),
    }
    # dados institucionais viram tokens inst_* (handle, site, phone, city, ...)
    tokens.update({f"inst_{k}": v for k, v in inst.items() if isinstance(v, (str, int, float))})
    tokens.update(brief.get("layout", {}))
    tokens.update(brief.get("copy", {}))

    # assets do briefing (fotos, selos): caminho absoluto ou relativo ao cliente
    for key, path in brief.get("assets", {}).items():
        tokens[key] = data_uri(resolve(path, client_dir / "assets", client_dir, ROOT))

    # logos por papel declarado no brand kit (primary, reverse, symbol, ...)
    for key, role in brief.get("logos", {}).items():
        logos = brand.get("logos", {})
        if role not in logos:
            raise RenderError(
                f"brand kit de '{brief['client']}' nao tem logo no papel '{role}'. "
                f"Papeis disponiveis: {sorted(logos)}")
        tokens[key] = data_uri(resolve(logos[role], client_dir / "assets", client_dir, ROOT))

    # {{token}} obrigatorio; {{token=padrao}} cai no padrao quando o briefing nao informa.
    # O padrao existe para o template poder ter opcionais sem quebrar o JS que os consome.
    def sub(m):
        key, default = m.group(1), m.group(2)
        if key in tokens and str(tokens[key]) != "":
            return str(tokens[key])
        return default if default is not None else ""

    html = TOKEN_RE.sub(sub, tpl)

    missing = sorted({m.group(1) for m in TOKEN_RE.finditer(tpl)
                      if m.group(2) is None and m.group(1) not in tokens})
    return html, fmt, {"missing_tokens": missing, "brand": brand}, client_dir


def render(brief_path: str, out_path: str | None = None) -> dict:
    brief = json.loads(pathlib.Path(brief_path).expanduser().read_text(encoding="utf-8"))
    html, fmt, meta, _ = build_html(brief)

    if out_path:
        out = pathlib.Path(out_path).expanduser().resolve()
    else:
        out = (OUTPUT / brief["client"] / f"{brief.get('name', 'peca')}.png").resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    debug_html = out.with_suffix(".html")
    debug_html.write_text(html, encoding="utf-8")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RenderError("playwright nao instalado: pip3 install playwright") from e

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            env=chromium_env(),
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--force-color-profile=srgb", "--font-render-hinting=none"],
        )
        page = browser.new_page(viewport={"width": fmt["w"], "height": fmt["h"]},
                                device_scale_factor=fmt["scale"])
        page.goto(debug_html.as_uri())
        page.wait_for_load_state("load")
        page.evaluate("document.fonts.ready")
        fit = page.evaluate(AUTOFIT_JS, MIN_SCALE)
        probe = page.evaluate(PROBE_JS)
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": fmt["w"], "height": fmt["h"]})
        browser.close()

    report = {
        "png": str(out),
        "html": str(debug_html),
        "client": brief["client"],
        "template": brief["template"],
        "format": fmt,
        "expected": [int(fmt["w"] * fmt["scale"]), int(fmt["h"] * fmt["scale"])],
        "missing_tokens": meta["missing_tokens"],
        "autofit": fit,
        "probe": probe,
    }
    (out.with_suffix(".report.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Renderiza uma peca a partir de um briefing.")
    ap.add_argument("--brief", required=True, help="briefing JSON")
    ap.add_argument("--out", help="PNG de saida (default: output/<cliente>/<nome>.png)")
    a = ap.parse_args()
    try:
        r = render(a.brief, a.out)
    except RenderError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    if r["missing_tokens"]:
        print("AVISO tokens sem valor: " + ", ".join(r["missing_tokens"]), file=sys.stderr)
    for s in r["autofit"]["scopes"]:
        if s["scale"] < 1:
            det = ", ".join("{}={}px".format(i["el"], i["px"]) for i in s["sizes"])
            print(f"auto-fit '{s['scope']}': escala {s['scale']} ({det})", file=sys.stderr)
    print(r["png"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
