#!/usr/bin/env python3
"""Autoconferencia de direcao de arte, antes do handoff para o Revisor.

NAO atribui estrelas, NAO aprova e NAO reprova. Isso e do Revisor de Criacao, sempre.

O que faz: recolhe fatos mensuraveis da peca (quantas familias tipograficas, qual a razao
de escala, quantas camadas ligadas, onde esta o texto em relacao a foto) e devolve as
perguntas que o Designer precisa se fazer olhando a propria peca. As respostas sao dele.

Uso:
    selfcheck.py --job <dir> --version N [--json]
"""
from __future__ import annotations

import argparse
import json
import pathlib

# As perguntas do enunciado. Cada uma vem acompanhada do fato medido que ajuda a responder.
PERGUNTAS = [
    ("dominancia", "Existe um elemento dominante claro?"),
    ("hierarquia", "A hierarquia e evidente a um relance?"),
    ("vozes", "Ha vozes tipograficas demais?"),
    ("competicao", "Fotografia e texto competem?"),
    ("camadas", "Existe camada sem funcao?"),
    ("cta", "O CTA parece componente web quando nao deveria?"),
    ("marca", "A marca esta integrada ou apenas colada?"),
    ("template", "A peca parece excessivamente template?"),
]


def analisar(job_dir: pathlib.Path, version: int) -> dict:
    ad_p = job_dir / "art-direction.json"
    brief_p = job_dir / f"brief.v{version}.json"
    rep_p = job_dir / f"v{version}.report.json"

    ad = json.loads(ad_p.read_text(encoding="utf-8")) if ad_p.is_file() else {}
    brief = json.loads(brief_p.read_text(encoding="utf-8")) if brief_p.is_file() else {}
    rep = json.loads(rep_p.read_text(encoding="utf-8")) if rep_p.is_file() else {}

    res = ad.get("_resolved", {})
    tipo = res.get("typography", {})
    params = res.get("composition_params", {})
    layers = ad.get("layers", [])

    familias = sorted({v["font"] for v in tipo.values()}) if tipo else []
    tamanhos = {k: v["px"] for k, v in tipo.items()}

    # razao entre o maior e o menor corpo realmente usado no conteudo
    usados = [tamanhos.get(k) for k in ("headline", "subheadline", "body", "eyebrow", "caption")
              if tamanhos.get(k) and (brief.get("copy", {}).get(k if k != "body" else "body"))]
    razao = round(max(usados) / min(usados), 2) if len(usados) >= 2 else None

    # camadas que o job declarou mas que saem sem efeito visivel
    lay = brief.get("layout", {})
    inertes = []
    if "scrim" in layers and float(lay.get("scrim", 0) or 0) == 0:
        inertes.append("scrim declarado com intensidade 0")
    if "texture" in layers and float(lay.get("texture", 0) or 0) == 0:
        inertes.append("texture declarada com opacidade 0")
    if "decorative-type" in layers and (float(lay.get("deco_opacity", 0) or 0) == 0
                                        or not lay.get("deco_text")):
        inertes.append("decorative-type declarada sem texto ou sem opacidade")
    if "shapes" in layers and not any(lay.get(k) for k in ("rule_style", "block_style", "frame_w")):
        inertes.append("shapes declarada sem nenhuma forma configurada")

    texto_sobre_foto = bool(lay.get("over_image"))
    contraste = (rep.get("probe", {}) or {}).get("text", [])
    autofit = (rep.get("autofit", {}) or {}).get("scopes", [])
    escala_fit = autofit[0]["scale"] if autofit else None

    fatos = {
        "familias_tipograficas": familias,
        "quantidade_de_familias": len(familias),
        "corpos_px": tamanhos,
        "razao_de_escala_no_conteudo": razao,
        "dominancia_declarada": params.get("dominance"),
        "elemento_dominante_declarado": ad.get("dominant_element"),
        "image_mode": params.get("image_mode"),
        "text_position": params.get("text_position"),
        "brand_position": params.get("brand_position"),
        "cta_style": params.get("cta_style"),
        "camadas_declaradas": layers,
        "camadas_sem_efeito": inertes,
        "texto_sobre_fotografia": texto_sobre_foto,
        "auto_fit_escala": escala_fit,
        "elementos_de_texto_medidos": [t.get("el") for t in contraste],
    }

    # sinalizacoes: apontam para onde olhar, nunca sao veredito
    sinais = []
    if len(familias) > 3:
        sinais.append(f"{len(familias)} familias tipograficas na mesma peca — provavel excesso de vozes")
    elif len(familias) == 1:
        sinais.append("uma unica familia: confira se a hierarquia se sustenta so por corpo e peso")
    if razao is not None and razao < 2.2:
        sinais.append(f"razao de escala {razao}x entre o maior e o menor texto — hierarquia possivelmente rasa")
    if inertes:
        sinais.append("camada(s) declarada(s) sem efeito: " + "; ".join(inertes))
    if params.get("cta_style") in ("button", "pill") and ad.get("visual_tone"):
        sinais.append(f"CTA em '{params['cta_style']}': confira se nao le como botao de site")
    if params.get("brand_position") == "bar":
        sinais.append("marca em barra no rodape: confira se esta integrada ou apenas colada")
    if texto_sobre_foto and params.get("image_mode") in ("full", "background"):
        sinais.append("texto sobre a fotografia: confira area livre, rosto, produto e direcao do olhar")
    if escala_fit is not None and escala_fit < 0.8:
        sinais.append(f"auto-fit encolheu para {escala_fit}: a copy pode estar longa para a composicao")
    if not ad.get("rationale"):
        sinais.append("direcao de arte sem justificativa registrada (campo 'rationale')")

    return {"job": str(job_dir), "version": version, "fatos": fatos,
            "sinalizacoes": sinais,
            "perguntas": [{"chave": k, "pergunta": q} for k, q in PERGUNTAS],
            "aviso": "Autoconferencia NAO aprova nem reprova. Estrelas e status sao do Revisor de Criacao."}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--job", required=True)
    ap.add_argument("--version", type=int, required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    job_dir = pathlib.Path(a.job).expanduser().resolve()
    r = analisar(job_dir, a.version)
    (job_dir / f"selfcheck.v{a.version}.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    f = r["fatos"]
    print("FATOS MEDIDOS")
    print(f"  familias        {f['quantidade_de_familias']}: {', '.join(f['familias_tipograficas'])}")
    print(f"  razao de escala {f['razao_de_escala_no_conteudo']}x")
    print(f"  corpos          " + ", ".join(f"{k}={v}px" for k, v in f["corpos_px"].items()))
    print(f"  composicao      {f['image_mode']} / {f['text_position']} / "
          f"dominancia {f['dominancia_declarada']}")
    print(f"  marca           {f['brand_position']}   CTA {f['cta_style']}")
    print(f"  camadas         {', '.join(f['camadas_declaradas']) or '-'}")
    if f["camadas_sem_efeito"]:
        print(f"  SEM EFEITO      {'; '.join(f['camadas_sem_efeito'])}")

    if r["sinalizacoes"]:
        print("\nONDE OLHAR")
        for s in r["sinalizacoes"]:
            print(f"  - {s}")

    print("\nPERGUNTAS (responda olhando a peca, nao este relatorio)")
    for q in r["perguntas"]:
        print(f"  - {q['pergunta']}")
    print(f"\n{r['aviso']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
