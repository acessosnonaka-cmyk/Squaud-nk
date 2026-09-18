#!/usr/bin/env python3
"""Testes de defeito: peças que DEVEM ser reprovadas.

Provar qualidade com peça boa não prova nada — o que interessa é o que o motor
barra. Cada caso aqui é um defeito que já chegou ao cliente pelo menos uma vez.

    python3 agents/design-ia/testes/teste-defeitos-visuais.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))

from PIL import Image                                      # noqa: E402
import validate                                            # noqa: E402

falhas = []


def checar(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


W, H = 1080, 1350


def peca(tmp, nome, *, scopes=None, texto=None):
    """Monta um PNG + report.json sintéticos e devolve o resultado do validate."""
    png = pathlib.Path(tmp) / f"{nome}.png"
    Image.new("RGB", (W, H), (20, 20, 20)).save(png)
    base_texto = texto if texto is not None else [
        {"el": "headline", "color": "rgb(255,255,255)", "bg": "rgb(20,20,20)",
         "px": 64.0, "weight": "700", "over_image": False, "box": [80, 900, 900, 160]},
    ]
    rep = {
        "expected": [W, H],
        "missing_tokens": [],
        "autofit": {"overflow": [], "scopes": scopes if scopes is not None else
                    [{"scope": "texto", "scale": 1.0,
                      "sizes": [{"el": "headline", "px": 64.0}]}]},
        "probe": {"images": [], "outside": [], "remote": [], "text": base_texto},
    }
    png.with_suffix(".report.json").write_text(json.dumps(rep), encoding="utf-8")
    return validate.validate(str(png))


with tempfile.TemporaryDirectory(prefix="squad-nk-defeito-") as tmp:

    # ---------------------------------------------- 0 · peça sã passa
    r = peca(tmp, "sa")
    checar("0/peca-sa-passa", r["ok"], "; ".join(r["fails"]))

    # ---------------------------------------------- 1 · tipografia espremida
    r = peca(tmp, "espremida",
             scopes=[{"scope": "texto", "scale": 0.61,
                      "sizes": [{"el": "headline", "px": 39.0}]}])
    checar("1/espremida-reprova", not r["ok"])
    checar("1/espremida-diz-por-que",
           any("espremida" in f for f in r["fails"]), "; ".join(r["fails"]))

    # o limiar novo pega o que o antigo (0.75) deixava passar
    r = peca(tmp, "quase",
             scopes=[{"scope": "texto", "scale": 0.78,
                      "sizes": [{"el": "headline", "px": 50.0}]}])
    checar("1b/limiar-novo-pega-0.78", not r["ok"], "0.78 passou")

    # ---------------------------------------------- 2 · texto ilegível
    r = peca(tmp, "minusculo",
             scopes=[{"scope": "texto", "scale": 1.0,
                      "sizes": [{"el": "legenda", "px": 11.0}]}])
    checar("2/ilegivel-reprova", not r["ok"])
    checar("2/ilegivel-e-falha-nao-aviso",
           any("legibilidade" in f for f in r["fails"]),
           "virou aviso em vez de falha: " + "; ".join(r["warns"]))

    # ---------------------------------------------- 3 · blocos colidindo
    colidindo = [
        {"el": "headline", "color": "rgb(255,255,255)", "bg": "rgb(20,20,20)",
         "px": 64.0, "weight": "700", "over_image": False, "box": [80, 900, 900, 200]},
        {"el": "subheadline", "color": "rgb(255,255,255)", "bg": "rgb(20,20,20)",
         "px": 28.0, "weight": "400", "over_image": False, "box": [80, 1020, 900, 120]},
    ]
    r = peca(tmp, "colisao", texto=colidindo)
    checar("3/colisao-reprova", not r["ok"])
    checar("3/colisao-nomeia-os-dois",
           any("headline" in f and "subheadline" in f for f in r["fails"]),
           "; ".join(r["fails"]))

    # encostar de leve não pode reprovar
    quase = [
        {"el": "headline", "color": "rgb(255,255,255)", "bg": "rgb(20,20,20)",
         "px": 64.0, "weight": "700", "over_image": False, "box": [80, 900, 900, 160]},
        {"el": "subheadline", "color": "rgb(255,255,255)", "bg": "rgb(20,20,20)",
         "px": 28.0, "weight": "400", "over_image": False, "box": [80, 1058, 900, 120]},
    ]
    r = peca(tmp, "encosta", texto=quase)
    checar("3b/encostar-de-leve-passa", r["ok"], "; ".join(r["fails"]))

    # ---------------------------------------------- 4 · o que já era pego continua
    r = peca(tmp, "contraste", texto=[
        {"el": "headline", "color": "rgb(40,40,40)", "bg": "rgb(20,20,20)",
         "px": 64.0, "weight": "700", "over_image": False, "box": [80, 900, 900, 160]}])
    checar("4/contraste-continua-pego",
           any("contraste" in f for f in r["fails"]), "; ".join(r["fails"]))

    # ---------------------------------------------- 5 · o check aparece no relatório
    r = peca(tmp, "checks")
    for c in ("collision", "fit_scale", "text_overflow", "contrast", "dimension"):
        checar(f"5/relatorio-tem-{c}", c in r["checks"], str(list(r["checks"])))

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print("\nteste-defeitos-visuais: espremido, ilegível, colisão e contraste · OK")
sys.exit(0)
