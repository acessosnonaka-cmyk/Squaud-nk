#!/usr/bin/env python3
"""Triagem de risco dos assets de um cliente, antes de usar a foto numa peca.

Motivacao real: uma peca foi reprovada pelo revisor porque a foto escolhida era um frame
de video com legenda gravada de outro conteudo ("julgando os dentes dele"). O arquivo se
chamava `atendimento.jpg` e nada no nome denunciava o problema.

Esta triagem NAO le texto dentro da imagem -- nao ha OCR aqui, de proposito. Ela usa
apenas sinais ja disponiveis (proporcao, resolucao, nome, EXIF) para dizer QUAIS fotos
merecem um olhar mais atento. O olhar continua sendo obrigatorio: risco baixo nao e
atestado de que a foto serve.

Uso:
    assets.py audit --client <slug> [--min-width N] [--json]
    assets.py risks
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
CLIENTS = ROOT / "clients"

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# Proporcoes de tela de celular: quase sempre screenshot ou frame de story/reel.
# 3:4 e 4:5 ficam DE FORA de proposito -- sao proporcoes fotograficas classicas, e
# marca-las transformaria a triagem em ruido.
SCREEN_RATIOS = [
    (9 / 16, "9:16 (tela de celular / story / reel)"),
    (9 / 19.5, "9:19.5 (tela de celular moderna)"),
]

# Resolucoes exatas de telas conhecidas.
SCREEN_SIZES = {
    (720, 1280), (750, 1334), (1080, 1920), (1170, 2532), (1179, 2556),
    (1284, 2778), (828, 1792), (640, 1136), (1125, 2436),
}

NAME_SIGNALS = re.compile(
    r"(screenshot|screen[-_ ]?shot|print|captura|tela|story|stories|reel|reels|frame|"
    r"whatsapp|wa[-_ ]?image|img[-_ ]?\d{4,}|photo[-_ ]?\d{4,}|snap|captura[-_ ]?de[-_ ]?tela)",
    re.I)

# O catalogo de risco que o Designer deve ter em mente ao escolher uma foto.
RISCOS = """ASSET COM TEXTO EMBUTIDO / PRINT / FRAME DE VIDEO

Um asset e INADEQUADO quando o texto dentro da imagem:
  - nao pertence ao briefing atual;
  - e uma legenda (de video, story ou reel);
  - e um CTA de campanha antiga;
  - traz marca ou selo de outra campanha;
  - parece screenshot ou frame de video;
  - prejudica a composicao da peca.

Tambem e inadequado o asset que:
  - tem largura nativa menor que a caixa onde vai ser exibido (amplia e amolece);
  - tem proporcao de tela de celular quando a peca pede fotografia.

O QUE FAZER:
  - Havendo outra imagem valida no acervo: trocar automaticamente e permitido
    (correcao `swap_photo`).
  - NAO havendo alternativa valida: nao inventar imagem, nao gerar imagem, nao
    reaproveitar o asset ruim. Registrar que falta asset adequado e pedir
    intervencao humana (`job.py finalize --status bloqueada-falta-asset`).

LIMITE DESTA TRIAGEM: ela nao le o texto dentro da imagem. Os sinais abaixo apenas
priorizam a suspeita -- a decisao vem de OLHAR a foto, sempre, antes de usar.
"""


def exif_signals(p: pathlib.Path) -> list[str]:
    try:
        from PIL import Image
    except ImportError:
        return []
    out: list[str] = []
    try:
        with Image.open(p) as im:
            ex = im.getexif()
            if not ex:
                # foto de camera quase sempre carrega EXIF; a ausencia sugere captura,
                # recorte ou reexportacao -- sinal fraco, nunca conclusivo
                out.append("sem metadados EXIF (possivel captura ou reexportacao)")
                return out
            make = str(ex.get(271, "") or "")
            model = str(ex.get(272, "") or "")
            software = str(ex.get(305, "") or "")
            if not make and not model:
                out.append("EXIF sem marca/modelo de camera")
            if software and re.search(r"(snapseed|photoshop|canva|capcut|inshot|screenshot)",
                                      software, re.I):
                out.append(f"EXIF Software='{software}'")
    except Exception:
        return []
    return out


def audit_file(p: pathlib.Path, min_width: int | None) -> dict:
    """Avalia um asset em DOIS eixos independentes.

    `risco_conteudo` -- chance de a imagem ser print/frame e trazer texto embutido.
    `resolucao`      -- se a foto aguenta a caixa onde vai ser exibida.

    Separados de proposito: uma foto legitima pode ser pequena, e um print pode ser
    enorme. Misturar os dois produzia "risco alto" em tudo, o que nao ajuda ninguem.
    """
    try:
        from PIL import Image
        with Image.open(p) as im:
            w, h = im.size
    except Exception as e:
        return {"arquivo": p.name, "erro": str(e), "risco_conteudo": "alto",
                "resolucao": "desconhecida", "sinais": ["nao foi possivel abrir a imagem"]}

    sinais: list[str] = []
    ratio = w / h if h else 0
    forte = False

    if (w, h) in SCREEN_SIZES:
        sinais.append(f"dimensao {w}x{h} e resolucao exata de tela de celular")
        forte = True
    else:
        for r, label in SCREEN_RATIOS:
            if abs(ratio - r) < 0.006:
                sinais.append(f"proporcao {label}")
                forte = True
                break

    if NAME_SIGNALS.search(p.stem):
        sinais.append(f"nome do arquivo sugere captura: '{p.name}'")
        forte = True

    # EXIF ausente e sinal fraco: quase todo asset de cliente chega reexportado.
    # Entra como nota, e so agrava quando ja ha outro sinal.
    notas = exif_signals(p)
    risco = "alto" if forte else ("medio" if notas and len(notas) > 1 else "baixo")

    resolucao = "ok"
    if min_width and w < min_width:
        resolucao = "insuficiente" if w < min_width * 0.85 else "limite"
        sinais.append(f"largura nativa {w}px para caixa de {min_width}px ({resolucao})")

    return {"arquivo": p.name, "dimensao": [w, h], "proporcao": round(ratio, 3),
            "risco_conteudo": risco, "resolucao": resolucao,
            "sinais": sinais, "notas": notas}


def cmd_audit(a) -> int:
    d = CLIENTS / a.client / "assets"
    if not d.is_dir():
        print(f"ERRO: {d} nao existe", file=sys.stderr)
        return 2

    # logos nao sao fotografia: nao vao na caixa da foto e seriam reprovados por
    # largura sem que isso queira dizer nada
    brand_path = CLIENTS / a.client / "brand.json"
    logos: set[str] = set()
    if brand_path.is_file():
        try:
            b = json.loads(brand_path.read_text(encoding="utf-8"))
            logos = {pathlib.Path(v).name for v in (b.get("logos") or {}).values()}
        except (json.JSONDecodeError, OSError):
            pass

    itens = [audit_file(p, a.min_width) for p in sorted(d.iterdir())
             if p.suffix.lower() in IMG_EXT and p.name not in logos]

    # candidata valida = sem sinal de print E com resolucao que aguenta a caixa
    validas = [i for i in itens
               if i.get("risco_conteudo") == "baixo" and i.get("resolucao") in ("ok", "limite")]
    res = {
        "cliente": a.client,
        "min_width": a.min_width,
        "logos_ignorados": sorted(logos),
        "itens": itens,
        "candidatas_validas": [i["arquivo"] for i in validas],
        "ha_alternativa_valida": bool(validas),
        "aviso": "Sinais nao substituem olhar a imagem. Risco baixo nao atesta que a foto serve.",
    }

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    print(f"{'arquivo':22} {'dimensao':12} {'print?':7} {'resol.':13} sinais")
    for i in itens:
        dim = "x".join(str(n) for n in i.get("dimensao", ["?", "?"]))
        print(f"{i['arquivo']:22} {dim:12} {i.get('risco_conteudo', '?'):7} "
              f"{i.get('resolucao', '?'):13} {'; '.join(i['sinais']) or '-'}")
    if logos:
        print(f"\nlogos ignorados (nao sao fotografia): {', '.join(sorted(logos))}")
    print(f"candidatas validas: {', '.join(res['candidatas_validas']) or 'NENHUMA'}")
    print(res["aviso"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("audit")
    p.add_argument("--client", required=True)
    p.add_argument("--min-width", type=int, default=1080,
                   help="largura da caixa onde a foto sera exibida (default 1080)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_audit)
    sub.add_parser("risks").set_defaults(fn=lambda _a: (print(RISCOS), 0)[1])
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
