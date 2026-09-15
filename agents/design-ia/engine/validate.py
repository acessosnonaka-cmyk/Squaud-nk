#!/usr/bin/env python3
"""Validacao tecnica da peca renderizada.

Trabalha sobre o PNG e sobre o relatorio medido no navegador (<peca>.report.json),
produzido pelo render.py. Mede, nao estima.

Uso:
    python3 validate.py --png <arquivo.png> [--json]

Saida: relatorio com FAIL (bloqueia entrega) e WARN (decisao do Claude).
Codigo de saida 0 = sem FAIL.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

# Contraste minimo, criterio WCAG AA. "Texto grande" = 24px normal ou 18.66px em negrito
# (14pt bold); nele bastam 3.0:1. Texto corrido exige 4.5:1. Peca grafica nao e pagina
# web, mas abaixo desses pisos a leitura em feed sofre de fato.
MIN_CONTRAST_LARGE = 3.0
MIN_CONTRAST_BODY = 4.5
LARGE_PX = 24.0
LARGE_PX_BOLD = 18.66
BOLD_WEIGHT = 700
MIN_LEGIBLE_PX = 16.0


def is_large_text(px: float, weight) -> bool:
    try:
        w = int(float(weight))
    except (TypeError, ValueError):
        w = 400
    return px >= (LARGE_PX_BOLD if w >= BOLD_WEIGHT else LARGE_PX)


def srgb_to_lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = (srgb_to_lin(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def parse_css_color(s: str):
    m = re.findall(r"[\d.]+", s or "")
    if len(m) >= 3:
        return [float(m[0]), float(m[1]), float(m[2])], (float(m[3]) if len(m) > 3 else 1.0)
    return None, None


def sample_bg(png: pathlib.Path, box) -> list | None:
    """Cor media sob a caixa de texto -- usada quando o texto esta sobre foto."""
    try:
        from PIL import Image
    except ImportError:
        return None
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return None
    with Image.open(png) as im:
        im = im.convert("RGB")
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(im.width, int(x + w)), min(im.height, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return None
        # reduzir a 1px = media dos pixels da caixa, sem varrer a imagem
        return list(im.crop((x0, y0, x1, y1)).resize((1, 1)).getpixel((0, 0)))


def validate(png_path: str) -> dict:
    png = pathlib.Path(png_path).expanduser().resolve()
    fails: list[str] = []
    warns: list[str] = []
    checks: dict = {}

    # 1. arquivo PNG valido
    if not png.is_file():
        return {"png": str(png), "ok": False, "fails": ["PNG inexistente"], "warns": [], "checks": {}}
    try:
        from PIL import Image
        with Image.open(png) as im:
            im.verify()
        with Image.open(png) as im:
            size, mode = im.size, im.mode
        checks["png"] = {"ok": True, "size": list(size), "mode": mode}
    except Exception as e:  # arquivo truncado ou corrompido
        return {"png": str(png), "ok": False, "fails": [f"PNG invalido: {e}"], "warns": [], "checks": {}}

    rep_path = png.with_suffix(".report.json")
    if not rep_path.is_file():
        warns.append("relatorio do render ausente; checks de layout nao executados")
        return {"png": str(png), "ok": not fails, "fails": fails, "warns": warns, "checks": checks}
    rep = json.loads(rep_path.read_text(encoding="utf-8"))

    # 2. dimensao exata
    expected = rep.get("expected")
    if expected and list(size) != list(expected):
        fails.append(f"dimensao {size} difere do formato esperado {tuple(expected)}")
    checks["dimension"] = {"ok": not expected or list(size) == list(expected),
                           "got": list(size), "expected": expected}

    # 3. tokens do template sem valor
    if rep.get("missing_tokens"):
        fails.append("tokens sem valor no template: " + ", ".join(rep["missing_tokens"]))
    checks["tokens"] = {"ok": not rep.get("missing_tokens"), "missing": rep.get("missing_tokens", [])}

    # 4. texto sem overflow + piso de legibilidade
    fit = rep.get("autofit", {})
    if fit.get("overflow"):
        fails.append("texto estourou o bloco mesmo no tamanho minimo: " + ", ".join(fit["overflow"]))
    small = [i for s in fit.get("scopes", []) for i in s.get("sizes", []) if i["px"] < MIN_LEGIBLE_PX]
    if small:
        warns.append("texto abaixo do piso de legibilidade: "
                     + ", ".join(f"{i['el']}={i['px']}px" for i in small))
    shrunk = [s for s in fit.get("scopes", []) if s.get("scale", 1) < 0.75]
    if shrunk:
        warns.append("auto-fit encolheu demais (" +
                     ", ".join(f"{s['scope']}={s['scale']}" for s in shrunk) +
                     "): copy provavelmente longa para o template")
    checks["text_overflow"] = {"ok": not fit.get("overflow"), "scopes": fit.get("scopes", [])}

    probe = rep.get("probe", {})

    # 5. assets e logo carregados
    broken = [i for i in probe.get("images", []) if not i.get("ok")]
    if broken:
        fails.append(f"{len(broken)} imagem(ns) nao carregaram")
    logos = [i for i in probe.get("images", []) if i.get("role") == "logo"]
    if logos and not all(i.get("ok") for i in logos):
        fails.append("logo nao carregou")
    checks["assets"] = {"ok": not broken, "total": len(probe.get("images", [])),
                        "broken": len(broken), "logo_presente": bool(logos)}

    # 6. nada fora do canvas
    outside = probe.get("outside", [])
    if outside:
        fails.append("elemento fora do canvas: " + ", ".join(o["el"] or "?" for o in outside))
    checks["inside_canvas"] = {"ok": not outside, "outside": outside}

    # 7. nenhuma dependencia remota no render final
    remote = probe.get("remote", []) + [i for i in probe.get("images", []) if i.get("remote")]
    if remote:
        fails.append(f"{len(remote)} dependencia(s) remota(s) no HTML final")
    checks["offline"] = {"ok": not remote, "remote": probe.get("remote", [])[:5]}

    # 8. contraste minimo
    cres = []
    for t in probe.get("text", []):
        fg, _ = parse_css_color(t.get("color"))
        bg, alpha = parse_css_color(t.get("bg"))
        if t.get("over_image") or bg is None or (alpha is not None and alpha < 0.9):
            bg = sample_bg(png, t.get("box", [0, 0, 0, 0])) or bg
        if fg is None or bg is None:
            continue
        ratio = round(contrast(fg, bg), 2)
        large = is_large_text(t.get("px", 0), t.get("weight"))
        need = MIN_CONTRAST_LARGE if large else MIN_CONTRAST_BODY
        cres.append({"el": t["el"], "ratio": ratio, "need": need,
                     "px": t.get("px"), "weight": t.get("weight"), "large": large})
        if ratio < need:
            fails.append(f"contraste insuficiente em '{t['el']}': {ratio}:1 (minimo {need}:1)")
    checks["contrast"] = {"ok": all(c["ratio"] >= c["need"] for c in cres), "items": cres}

    return {"png": str(png), "ok": not fails, "fails": fails, "warns": warns, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description="Valida uma peca renderizada.")
    ap.add_argument("--png", required=True)
    ap.add_argument("--json", action="store_true", help="saida JSON completa")
    a = ap.parse_args()
    r = validate(a.png)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        # "checagem" e nao "aprovado": status e estrelas sao do Revisor de Criacao,
        # nunca desta checagem tecnica
        print(("CHECAGEM OK" if r["ok"] else "CHECAGEM FALHOU") + f" — {r['png']}")
        for c, v in r["checks"].items():
            print(f"  [{'ok' if v.get('ok') else 'XX'}] {c}")
        for f in r["fails"]:
            print(f"  FAIL: {f}")
        for w in r["warns"]:
            print(f"  WARN: {w}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
