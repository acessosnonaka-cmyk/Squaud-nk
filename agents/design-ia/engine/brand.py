#!/usr/bin/env python3
"""Brand kits do Designer IA: criar, inspecionar, validar e derivar de material existente.

Um brand kit e DADO. Nenhuma regra de cliente vive no motor -- vive aqui, em
clients/<slug>/brand.json, e e reutilizada em todas as pecas seguintes.

Principio: nunca inventar. O que nao foi confirmado fica em provenance.unknown e
aparece no `validate` como pendencia, para o Claude perguntar ao usuario.

Uso:
    brand.py list
    brand.py init    --slug <slug> --name "<Nome>"
    brand.py show    --slug <slug>
    brand.py validate --slug <slug>
    brand.py derive  --slug <slug> --from <dir> [--write]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
CLIENTS = ROOT / "clients"

SCHEMA = 1

# Campos que uma peca costuma precisar. Ausencia nao e erro: e pendencia a confirmar.
EXPECTED = ["palette", "fonts", "type", "logos", "tone", "institutional",
            "visual_preferences", "restrictions", "references"]

# Opcionais: a ausencia nao e pendencia. Servem quando o cliente TEM uma regra
# confirmada; sem eles, a decisao e por job.
OPTIONAL = ["typography", "visual_language"]


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def skeleton(slug: str, name: str) -> dict:
    return {
        "schema": SCHEMA,
        "slug": slug,
        "name": name,
        "palette": {},
        "fonts": [],
        "type": {"display": "", "text": ""},
        # V2.2, opcionais: so preencher com o que for CONFIRMADO. Ausentes, o Designer
        # decide por job e registra a decisao em art-direction.json -- o que nao vira
        # regra permanente do cliente.
        "typography": {"official": False, "roles": {}},
        "visual_language": {"preferred_compositions": [], "avoid": [],
                            "density": "", "corner_style": "", "image_treatment": ""},
        "logos": {},
        "tone": {"voice": "", "prefer": [], "avoid": []},
        "institutional": {},
        "visual_preferences": {"photo_style": "", "layout": "", "notes": []},
        "restrictions": [],
        "references": [],
        "provenance": {
            "created_at": now(),
            "updated_at": now(),
            "sources": [],
            "confirmed_by_user": False,
            "unknown": [],
        },
    }


def path_of(slug: str) -> pathlib.Path:
    return CLIENTS / slug / "brand.json"


def load(slug: str) -> dict:
    p = path_of(slug)
    if not p.is_file():
        raise SystemExit(f"ERRO: brand kit inexistente para '{slug}' ({p})")
    return json.loads(p.read_text(encoding="utf-8"))


def save(slug: str, data: dict) -> pathlib.Path:
    data.setdefault("provenance", {})["updated_at"] = now()
    p = path_of(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    for sub in ("assets", "fonts", "references"):
        (p.parent / sub).mkdir(exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


# --------------------------------------------------------------------------- comandos

def cmd_list(_a) -> int:
    if not CLIENTS.is_dir() or not any(CLIENTS.iterdir()):
        print("nenhum cliente cadastrado")
        return 0
    for d in sorted(CLIENTS.iterdir()):
        if (d / "brand.json").is_file():
            b = json.loads((d / "brand.json").read_text(encoding="utf-8"))
            prov = b.get("provenance", {})
            flag = "confirmado" if prov.get("confirmed_by_user") else "NAO confirmado"
            print(f"{d.name:22} {b.get('name',''):28} {flag}  (atualizado {prov.get('updated_at','?')})")
    return 0


def cmd_init(a) -> int:
    p = path_of(a.slug)
    if p.is_file() and not a.force:
        print(f"ja existe: {p} (use --force para sobrescrever)", file=sys.stderr)
        return 1
    data = skeleton(a.slug, a.name)
    data["provenance"]["unknown"] = list(EXPECTED)
    print(save(a.slug, data))
    return 0


def cmd_show(a) -> int:
    print(json.dumps(load(a.slug), ensure_ascii=False, indent=2))
    return 0


def cmd_validate(a) -> int:
    b = load(a.slug)
    base = path_of(a.slug).parent
    problems, pending = [], []

    if not b.get("name"):
        problems.append("name vazio")
    if not b.get("palette"):
        pending.append("palette")
    if not b.get("fonts"):
        pending.append("fonts")
    if not b.get("logos"):
        pending.append("logos")

    for f in b.get("fonts", []):
        fp = pathlib.Path(f["file"]).expanduser()
        cands = [fp] if fp.is_absolute() else [base / "fonts" / f["file"], base / f["file"],
                                               ROOT / "fonts" / f["file"], ROOT / f["file"]]
        if not any(c.is_file() for c in cands):
            problems.append(f"arquivo de fonte ausente: {f['file']}")

    for role, path in b.get("logos", {}).items():
        lp = pathlib.Path(path).expanduser()
        cands = [lp] if lp.is_absolute() else [base / "assets" / path, base / path]
        if not any(c.is_file() for c in cands):
            problems.append(f"logo '{role}' ausente: {path}")

    for k, v in b.get("palette", {}).items():
        if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", str(v)):
            problems.append(f"cor invalida em palette.{k}: {v}")

    for k in EXPECTED:
        v = b.get(k)
        if not v and k not in pending:
            pending.append(k)

    if not b.get("provenance", {}).get("confirmed_by_user"):
        pending.append("confirmacao do usuario (provenance.confirmed_by_user)")

    ausentes_opcionais = [k for k in OPTIONAL if not b.get(k)]

    print(json.dumps({"slug": a.slug, "ok": not problems,
                      "problems": problems, "pending": pending,
                      "opcionais_ausentes": ausentes_opcionais,
                      "nota": "opcionais ausentes nao sao pendencia: o Designer decide "
                              "por job e registra em art-direction.json"},
                     ensure_ascii=False, indent=2))
    return 0 if not problems else 1


# --------------------------------------------------------------------------- derive

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
CSSVAR = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", re.I)
GFONT = re.compile(r"fonts\.googleapis\.com/css2\?([^\"'>\s]+)")
FAMILY = re.compile(r"family=([A-Za-z0-9+]+)")
IMG = re.compile(r"\.(png|jpe?g|webp|svg)$", re.I)

# at-rules de CSS e chaves de JSON-LD parecem @handle mas nao sao. Sem isto o derive
# "descobre" um perfil que nao existe -- exatamente o tipo de dado inventado a evitar.
AT_NOISE = {"@media", "@font-face", "@supports", "@import", "@keyframes", "@charset",
            "@page", "@namespace", "@layer", "@container", "@property",
            "@context", "@type", "@id", "@graph"}

SOCIAL = re.compile(r"instagram\.com/([A-Za-z][A-Za-z0-9_.]{2,29})")
# "@nome" so vale se nao houver texto colado antes (senao e o final de um e-mail)
# e se nao terminar em dominio (.com, .br).
HANDLE = re.compile(r"(?<![A-Za-z0-9._-])(@[A-Za-z][A-Za-z0-9_.]{3,})(?![A-Za-z0-9._-])")


def cmd_derive(a) -> int:
    """Le um diretorio de material do cliente e PROPOE um brand kit.

    Nao inventa: so reporta o que encontrou, com a origem de cada achado. Sem --write
    nada e persistido; com --write, grava e marca confirmed_by_user=False, de modo que
    o validate continue cobrando confirmacao humana.
    """
    src = pathlib.Path(a.source).expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"ERRO: diretorio inexistente: {src}")

    found: dict = {"palette": {}, "font_families": [], "logos": {}, "photos": [],
                   "institutional": {}, "sources": []}
    counts: collections.Counter = collections.Counter()

    for f in sorted(src.rglob("*")):
        if not f.is_file() or f.stat().st_size > 4_000_000:
            continue
        rel = str(f.relative_to(src))
        if f.suffix.lower() in (".css", ".html", ".htm", ".svg"):
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for name, hexv in CSSVAR.findall(txt):
                found["palette"].setdefault(name.lower(), hexv.upper())
                found["sources"].append(f"{rel}: --{name}={hexv}")
            counts.update(h.upper() for h in HEX.findall(txt))
            for q in GFONT.findall(txt):
                for fam in FAMILY.findall(q):
                    fam = fam.replace("+", " ")
                    if fam not in found["font_families"]:
                        found["font_families"].append(fam)
                        found["sources"].append(f"{rel}: google font {fam}")
            # handle: a URL do perfil e inequivoca; "@palavra" solto em HTML pega
            # at-rule de CSS, sufixo de e-mail e eixo de fonte variavel.
            for m in SOCIAL.findall(txt):
                found["institutional"].setdefault("handle", "@" + m)
                found["sources"].append(f"{rel}: perfil instagram.com/{m}")
            for m in HANDLE.findall(txt):
                if m.lower() not in AT_NOISE:
                    found["institutional"].setdefault("handle", m)

            for pat, key in ((r"https?://[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s\"'<>]*)?", "site"),
                             (r"\(?\d{2}\)? ?9?\d{4}-\d{4}", "phone")):
                for m in re.findall(pat, txt):
                    found["institutional"].setdefault(key, m)
        elif IMG.search(f.name):
            if "logo" in f.name.lower():
                found["logos"][f.stem] = str(f)
                found["sources"].append(f"{rel}: possivel logo")
            else:
                found["photos"].append(str(f))

    found["palette_frequent"] = [c for c, _ in counts.most_common(8)]
    found["photos"] = found["photos"][:40]

    print(json.dumps({"source": str(src), "found": found,
                      "aviso": "PROPOSTA. Confirme com o usuario antes de tratar como identidade."},
                     ensure_ascii=False, indent=2))

    if a.write:
        p = path_of(a.slug)
        b = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else skeleton(a.slug, a.slug)
        b["palette"].update({k: v for k, v in found["palette"].items() if k not in b["palette"]})
        for k, v in found["institutional"].items():
            b.setdefault("institutional", {}).setdefault(k, v)
        prov = b.setdefault("provenance", {})
        prov.setdefault("sources", []).append({"dir": str(src), "at": now(),
                                               "evidence": found["sources"][:40]})
        prov["confirmed_by_user"] = False
        print("gravado: " + str(save(a.slug, b)), file=sys.stderr)
    return 0


def cmd_import_asset(a) -> int:
    """Copia um arquivo para dentro do cliente, tornando o kit autossuficiente."""
    src = pathlib.Path(a.file).expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"ERRO: arquivo inexistente: {src}")
    dest_dir = CLIENTS / a.slug / a.kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (a.rename or src.name)
    shutil.copy2(src, dest)
    print(dest)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(fn=cmd_list)

    p = sub.add_parser("init"); p.add_argument("--slug", required=True)
    p.add_argument("--name", required=True); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("show"); p.add_argument("--slug", required=True); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("validate"); p.add_argument("--slug", required=True); p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("derive"); p.add_argument("--slug", required=True)
    p.add_argument("--from", dest="source", required=True)
    p.add_argument("--write", action="store_true")
    p.set_defaults(fn=cmd_derive)

    p = sub.add_parser("import-asset"); p.add_argument("--slug", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--kind", default="assets", choices=["assets", "fonts", "references"])
    p.add_argument("--rename")
    p.set_defaults(fn=cmd_import_asset)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
