#!/usr/bin/env python3
"""Prancha de inspecao: torna o render final OLHAVEL.

Motivacao real: o pipeline media caixas no DOM e nunca abria a imagem. Defeito
que o olho pega em um segundo -- foto mal enquadrada, bloco solto, acabamento
pobre, peca com cara de molde -- atravessava tudo porque ninguem olhava.

Esta prancha nao julga nada. Ela so coloca o render em cima da mesa, em tamanho
util e com as regioes criticas ampliadas, para que o julgamento de quem olha
tenha do que se agarrar.

    python3 inspecao.py --png v1.png [--out v1.inspecao.png]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from PIL import Image, ImageDraw

LARGURA = 1500
MARGEM = 24
ROTULO = 26


def _fonte():
    from PIL import ImageFont
    for c in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if pathlib.Path(c).is_file():
            return ImageFont.truetype(c, 15)
    return ImageFont.load_default()


def recortes(png: pathlib.Path, rep: dict) -> list:
    """Regioes que merecem ampliacao: cada bloco de texto e os quatro cantos."""
    im = Image.open(png).convert("RGB")
    W, H = im.size
    fora = []

    for t in rep.get("probe", {}).get("text", []):
        b = t.get("box")
        if not b or b[2] <= 0 or b[3] <= 0:
            continue
        folga = max(16, int(b[3] * 0.35))
        cx = (max(0, b[0] - folga), max(0, b[1] - folga),
              min(W, b[0] + b[2] + folga), min(H, b[1] + b[3] + folga))
        if cx[2] > cx[0] and cx[3] > cx[1]:
            fora.append((f"{t.get('el')} · {t.get('px')}px", im.crop(cx)))

    lado = int(min(W, H) * 0.22)
    for nome, cx in (("canto ↖", (0, 0, lado, lado)),
                     ("canto ↗", (W - lado, 0, W, lado)),
                     ("canto ↙", (0, H - lado, lado, H)),
                     ("canto ↘", (W - lado, H - lado, W, H))):
        fora.append((nome, im.crop(cx)))
    return fora


def montar(png: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    rep_p = png.with_suffix(".report.json")
    rep = json.loads(rep_p.read_text(encoding="utf-8")) if rep_p.is_file() else {}

    peca = Image.open(png).convert("RGB")
    alvo_w = LARGURA - 2 * MARGEM
    escala = min(1.0, alvo_w / peca.width)
    peca_v = peca.resize((int(peca.width * escala), int(peca.height * escala)),
                         Image.LANCZOS)

    partes = recortes(png, rep)
    cols, cel = 3, (alvo_w - 2 * MARGEM) // 3
    linhas = (len(partes) + cols - 1) // cols
    alt_grade = linhas * (cel + ROTULO + MARGEM) if partes else 0

    folha = Image.new("RGB",
                      (LARGURA, MARGEM * 3 + ROTULO + peca_v.height + alt_grade),
                      (250, 250, 250))
    d = ImageDraw.Draw(folha)
    f = _fonte()

    d.text((MARGEM, MARGEM // 2), f"{png.name} · {peca.width}x{peca.height}",
           fill=(30, 30, 30), font=f)
    y = MARGEM + ROTULO
    folha.paste(peca_v, (MARGEM, y))
    y += peca_v.height + MARGEM

    for i, (nome, im) in enumerate(partes):
        im = im.copy()
        im.thumbnail((cel, cel), Image.LANCZOS)
        x = MARGEM + (i % cols) * (cel + MARGEM)
        yy = y + (i // cols) * (cel + ROTULO + MARGEM)
        folha.paste(im, (x, yy))
        d.rectangle([x, yy, x + im.width, yy + im.height], outline=(210, 210, 210))
        d.text((x, yy + im.height + 5), nome[:42], fill=(60, 60, 60), font=f)

    folha.save(out, quality=92)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="inspecao",
                                 description="Prancha de inspecao visual do render final")
    ap.add_argument("--png", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    png = pathlib.Path(a.png).expanduser().resolve()
    if not png.is_file():
        print(f"ERRO: {png} nao existe", file=sys.stderr)
        return 2
    out = pathlib.Path(a.out).expanduser() if a.out else png.with_suffix(".inspecao.png")
    print(montar(png, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
