#!/usr/bin/env python3
"""Ciclo de vida de um job do Designer IA: criar -> renderizar -> revisar -> corrigir -> entregar.

Um job e a memoria de uma peca: briefing, versoes, pareceres do revisor, correcoes
aplicadas e status final. Tudo em disco, um diretorio por job -- o handoff com o revisor
e por arquivo, nao por variavel em memoria.

O limite de ciclos e estrutural, nao uma boa intencao: `next-cycle` recusa passar do teto
e `can-continue` da o veredito antes de qualquer render.

Uso:
    job.py new      --client <slug> --name <nome> --brief <arquivo.json> [--contexto ANUNCIO|SOCIAL]
    job.py render   --job <dir> --version N
    job.py review   --job <dir> --version N            (gera o handoff para o revisor)
    job.py save-review --job <dir> --version N --file <md>|--stdin
    job.py can-continue --job <dir>
    job.py next-cycle  --job <dir>
    job.py finalize    --job <dir> --version N --status <aprovada|entregue-com-ressalva|parada>
                       [--note "<motivo>"]
    job.py show     --job <dir>
    job.py list
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
OUTPUT = ROOT / "output"
MAX_CYCLES = 3


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-") or "peca"


# --------------------------------------------------- o veredito vem do parecer

# Status que colocam arquivo na area de entrega. So estes exigem revisao, e so
# estes copiam PNG para output/ -- peca parada ou bloqueada nao e entrega e nao
# tem por que aparecer na pasta de onde se manda ao cliente.
STATUS_DE_ENTREGA = ("aprovada", "entregue-com-ressalva")

# Ordem importa: o mais restritivo vence. Um parecer que diz "reprovado" e cita
# "aprovado" numa frase de contexto continua sendo reprovacao.
VEREDITOS = (
    ("REPROVADO", (r"\breprovad[oa]s?\b",)),
    ("AJUSTES_NECESSARIOS", (r"\bajustes?\s+(?:necessari[oa]s?|obrigatori[oa]s?)\b",
                             r"\brevisar\s+e\s+reenviar\b")),
    ("APROVADO_COM_RESSALVA", (r"\baprovad[oa]s?\s+com\s+ressalvas?\b",)),
    ("APROVADO", (r"\baprovad[oa]s?\b",)),
)


def _sem_acento(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def veredito_do_parecer(texto: str) -> str | None:
    """Le o status no texto que o Revisor escreveu.

    Deliberadamente NAO ha argumento de linha de comando para informar o
    veredito: quem finaliza nao pode ser quem declara que foi aprovado. O
    veredito tem de sair do parecer persistido, que e a palavra da autoridade
    que olhou a peca. Parecer sem status legivel nao serve como evidencia.
    """
    # Só o TEXTO perde acento e caixa. O padrão fica como está: `.upper()` num
    # regex troca \b por \B, que é a negação da fronteira de palavra, e o
    # casamento passa a nunca acontecer.
    t = _sem_acento(texto or "")
    for nome, padroes in VEREDITOS:
        for pad in padroes:
            if re.search(pad, t, re.IGNORECASE):
                return nome
    return None


def revisao_da_versao(job: dict, version: int) -> dict | None:
    for e in job.get("versions", []):
        if e.get("version") == version and e.get("review"):
            return e
    return None


def load_job(job_dir: pathlib.Path) -> dict:
    return json.loads((job_dir / "job.json").read_text(encoding="utf-8"))


def save_job(job_dir: pathlib.Path, job: dict) -> None:
    job["updated_at"] = now_iso()
    (job_dir / "job.json").write_text(
        json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def log(job: dict, event: str, **data) -> None:
    job.setdefault("historico", []).append({"em": now_iso(), "evento": event, **data})


# --------------------------------------------------------------------------- comandos

def cmd_new(a) -> int:
    # Dois pontos de entrada: um briefing tecnico pronto (V2.1) ou uma direcao de arte
    # (V2.2), que e compilada em briefing depois.
    if a.ad:
        ad = json.loads(pathlib.Path(a.ad).expanduser().read_text(encoding="utf-8"))
        brief = {"client": a.client, "name": a.name, "format": a.format,
                 "template": "composer"}
    else:
        ad = None
        brief = json.loads(pathlib.Path(a.brief).expanduser().read_text(encoding="utf-8"))
    client = a.client or brief.get("client")
    if not client:
        print("ERRO: cliente nao informado (--client ou campo 'client' no briefing)", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    job_id = f"{stamp}-{client}-{slugify(a.name or brief.get('name', 'peca'))}"
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True, exist_ok=False)

    brief["client"] = client
    (job_dir / "brief.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if ad is None:
        shutil.copy2(job_dir / "brief.json", job_dir / "brief.v1.json")
    else:
        (job_dir / "art-direction.json").write_text(
            json.dumps(ad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # snapshot da identidade: o parecer do revisor precisa ser lido contra a identidade
    # que valia no momento do render, mesmo que o brand kit mude depois.
    src = ROOT / "clients" / client / "brand.json"
    if src.is_file():
        shutil.copy2(src, job_dir / "brand.snapshot.json")
    else:
        print(f"AVISO: brand kit inexistente para '{client}'", file=sys.stderr)

    job = {
        "job_id": job_id,
        "client": client,
        "name": a.name or brief.get("name", "peca"),
        "contexto": a.contexto,
        "template": brief.get("template"),
        "format_name": brief.get("format") or a.format,
        "art_direction": bool(ad),
        "cycle": 1,
        "max_cycles": MAX_CYCLES,
        "versions": [],
        "status": "aberto",
        "created_at": now_iso(),
        "historico": [],
    }
    log(job, "job criado", brief=str(job_dir / "brief.v1.json"))
    save_job(job_dir, job)
    print(job_dir)
    return 0


def cmd_render(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    v = a.version
    brief_v = job_dir / f"brief.v{v}.json"
    if not brief_v.is_file():
        print(f"ERRO: {brief_v} nao existe", file=sys.stderr)
        return 2

    png = job_dir / f"v{v}.png"
    r = subprocess.run([sys.executable, str(ROOT / "render.py"),
                        "--brief", str(brief_v), "--out", str(png)],
                       capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        return r.returncode

    rep = json.loads((png.with_suffix(".report.json")).read_text(encoding="utf-8"))
    job["format"] = rep.get("format", {})

    val = subprocess.run([sys.executable, str(ROOT / "validate.py"), "--png", str(png)],
                         capture_output=True, text=True)
    (job_dir / f"validate.v{v}.txt").write_text(val.stdout + val.stderr, encoding="utf-8")
    ok = val.returncode == 0

    entry = next((e for e in job["versions"] if e["version"] == v), None)
    if entry is None:
        entry = {"version": v}
        job["versions"].append(entry)
    entry.update({"png": str(png), "brief": str(brief_v), "validado": ok,
                  "autofit": rep.get("autofit", {}).get("scopes", []), "em": now_iso()})

    # Prancha de inspecao: o render fica OLHAVEL antes de qualquer handoff.
    insp = subprocess.run([sys.executable, str(ROOT / "inspecao.py"), "--png", str(png)],
                          capture_output=True, text=True)
    if insp.returncode == 0:
        entry["inspecao_prancha"] = insp.stdout.strip()

    log(job, f"v{v} renderizada", checagem_tecnica="ok" if ok else "falhou")
    save_job(job_dir, job)
    print(png)
    if entry.get("inspecao_prancha"):
        print("PRANCHA DE INSPECAO: " + entry["inspecao_prancha"], file=sys.stderr)
        print("Abra a prancha e rode: job.py inspecionar --job <dir> --version "
              f"{v} --veredito ok|corrigir --parecer \"...\"", file=sys.stderr)
    print(val.stdout.strip(), file=sys.stderr)
    return 0 if ok else 1


def cmd_inspecionar(a) -> int:
    """Registra que o render final foi OLHADO, e o que se viu.

    Nao ha como um programa obrigar alguem a olhar. O que da para fazer e travar
    o handoff sem o registro do que foi visto -- e exigir observacao concreta,
    nao 'ok'. Parecer generico aqui e o mesmo que nao ter olhado.
    """
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    v = a.version
    png = job_dir / f"v{v}.png"
    if not png.is_file():
        print(f"ERRO: v{v} ainda nao foi renderizada", file=sys.stderr)
        return 2
    parecer = (a.parecer or "").strip()
    if len(parecer) < 40:
        print("ERRO: o parecer de inspecao precisa dizer o que voce VIU na peca "
              "(composicao, enquadramento, hierarquia, acabamento). "
              "Minimo de 40 caracteres, e 'ok' nao conta.", file=sys.stderr)
        return 2
    destino = job_dir / f"inspecao.v{v}.json"
    destino.write_text(json.dumps({
        "version": v, "veredito": a.veredito, "parecer": parecer,
        "prancha": str(job_dir / f"v{v}.inspecao.png"), "em": now_iso(),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(job, f"v{v} inspecionada", veredito=a.veredito)
    save_job(job_dir, job)
    print(destino)
    return 0


def cmd_review(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)

    # Trava: o Revisor nao recebe peca que o proprio Designer nao olhou.
    insp_p = job_dir / f"inspecao.v{a.version}.json"
    if not insp_p.is_file():
        print(f"ERRO: v{a.version} nao foi inspecionada. Abra "
              f"v{a.version}.inspecao.png, olhe a peca e rode "
              "'job.py inspecionar' antes do handoff.", file=sys.stderr)
        return 2
    insp = json.loads(insp_p.read_text(encoding="utf-8"))
    if insp.get("veredito") != "ok":
        print(f"ERRO: a inspecao de v{a.version} terminou em "
              f"'{insp.get('veredito')}'. Corrija e renderize uma nova versao "
              "antes de acionar o Revisor.", file=sys.stderr)
        return 2

    r = subprocess.run([sys.executable, str(ROOT / "revisor.py"), "handoff",
                        "--job", str(job_dir), "--version", str(a.version)],
                       capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        log(job, "revisor indisponivel")
        save_job(job_dir, job)
        return r.returncode
    log(job, f"handoff v{a.version} gerado")
    save_job(job_dir, job)
    print(r.stdout.strip())
    return 0


def cmd_save_review(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    txt = sys.stdin.read() if a.stdin else pathlib.Path(a.file).expanduser().read_text(encoding="utf-8")

    veredito = veredito_do_parecer(txt)
    if veredito is None:
        print("ERRO: nao consegui ler o status neste parecer. O Revisor precisa dizer, "
              "em palavras, se a peca esta APROVADA, APROVADA COM RESSALVA, se pede "
              "AJUSTES NECESSARIOS ou se esta REPROVADA. Sem status legivel o parecer "
              "nao vale como evidencia para finalizar.", file=sys.stderr)
        return 2

    dest = job_dir / f"review-v{a.version}.md"
    dest.write_text(txt, encoding="utf-8")

    entry = next((e for e in job["versions"] if e["version"] == a.version), None)
    if entry is not None:
        entry["review"] = str(dest)
        entry["review_veredito"] = veredito
        entry["review_em"] = now_iso()
    log(job, f"parecer v{a.version} recebido", arquivo=str(dest), veredito=veredito)
    save_job(job_dir, job)
    print(f"{dest}\nveredito: {veredito}")
    return 0


def cmd_can_continue(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    cycle, mx = job.get("cycle", 1), job.get("max_cycles", MAX_CYCLES)
    if job.get("status") not in ("aberto", "em-correcao"):
        print(f"NAO: job encerrado com status '{job.get('status')}'")
        return 1
    if cycle >= mx:
        print(f"NAO: teto de {mx} ciclos atingido (ciclo atual {cycle})")
        return 1
    print(f"SIM: ciclo {cycle} de {mx}")
    return 0


def cmd_next_cycle(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    cycle, mx = job.get("cycle", 1), job.get("max_cycles", MAX_CYCLES)
    if cycle >= mx:
        print(f"ERRO: teto de {mx} ciclos atingido. Entregue a melhor versao ou leve ao usuario.",
              file=sys.stderr)
        return 1
    job["cycle"] = cycle + 1
    job["status"] = "em-correcao"
    log(job, f"ciclo {cycle} -> {cycle + 1}")
    save_job(job_dir, job)
    print(job["cycle"])
    return 0


def _barreira_de_entrega(job_dir: pathlib.Path, job: dict, version: int) -> list:
    """O que falta para esta versao poder entrar na area de entrega.

    Reproduzido antes desta trava: `review` recusava a peca nao inspecionada e
    `finalize --status aprovada` passava mesmo assim, copiando o PNG para
    output/. O portao estava no caminho do handoff e faltava no caminho da
    saida, que e justamente o que chega ao cliente.

    Nada aqui aceita como prova: texto de conversa, argumento de linha de
    comando, `--note`, afirmacao do Designer ou a mera existencia do arquivo.
    So estado persistido.
    """
    falta = []

    insp_p = job_dir / f"inspecao.v{version}.json"
    if not insp_p.is_file():
        falta.append(f"v{version} nao tem inspecao registrada — abra v{version}.inspecao.png "
                     f"e rode 'job.py inspecionar'")
    else:
        try:
            insp = json.loads(insp_p.read_text(encoding="utf-8"))
        except Exception as e:
            falta.append(f"inspecao.v{version}.json ilegivel ({e})")
            insp = {}
        # Ausencia de veredito nao e aprovacao tacita: arquivo de inspecao sem o
        # campo nao prova que alguem olhou e achou bom.
        if insp.get("veredito") != "ok":
            falta.append(f"a inspecao de v{version} esta em "
                         f"'{insp.get('veredito') or '(sem veredito)'}', nao em 'ok'")

    entry = revisao_da_versao(job, version)
    if entry is None:
        falta.append(f"v{version} nao tem parecer do Revisor persistido — rode "
                     f"'job.py review' e depois 'job.py save-review'")
    else:
        review_p = pathlib.Path(entry["review"])
        if not review_p.is_file():
            falta.append(f"o parecer registrado nao existe em disco: {review_p}")
        veredito = entry.get("review_veredito")
        if not veredito:
            falta.append(f"o parecer de v{version} foi salvo sem status legivel — "
                         "regrave com 'job.py save-review'")
        elif veredito in ("REPROVADO", "AJUSTES_NECESSARIOS"):
            falta.append(f"o Revisor devolveu {veredito} para v{version}: peca reprovada "
                         "nao entra na area de entrega")
    return falta


def cmd_finalize(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    src = job_dir / f"v{a.version}.png"
    if not src.is_file():
        print(f"ERRO: {src} nao existe", file=sys.stderr)
        return 2

    entrega = a.status in STATUS_DE_ENTREGA
    if entrega:
        falta = _barreira_de_entrega(job_dir, job, a.version)
        if falta:
            print(f"ERRO: v{a.version} nao pode ser finalizada como '{a.status}'. "
                  f"{len(falta)} condicao(oes) aberta(s):", file=sys.stderr)
            for x in falta:
                print(f"  - {x}", file=sys.stderr)
            print("Nenhum arquivo foi copiado para a area de entrega. Para encerrar o job "
                  "sem entregar, use --status parada ou bloqueada-decisao-humana.",
                  file=sys.stderr)
            return 2

    dest = None
    if entrega:
        dest_dir = OUTPUT / job["client"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{slugify(job['name'])}.png"
        shutil.copy2(src, dest)

    job["status"] = a.status
    job["final_version"] = a.version
    job["final_png"] = str(dest) if dest else None
    job["nota_final"] = a.note
    log(job, "finalizado", status=a.status, versao=a.version,
        entregue=str(dest) if dest else "(nao entregue)", nota=a.note)
    save_job(job_dir, job)
    print(dest if dest else f"{job['status']} — nada copiado para a area de entrega")
    return 0


def cmd_show(a) -> int:
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)

    print(f"JOB {job['job_id']}")
    print(f"  cliente {job['client']} · template {job.get('template')} · "
          f"formato {job.get('format_name')} · contexto {job.get('contexto')}")
    print(f"  status  {job['status']} · ciclo {job.get('cycle')} de {job.get('max_cycles')}")
    if job.get("final_png"):
        print(f"  entregue: {job['final_png']} (v{job.get('final_version')})")
    if job.get("nota_final"):
        print(f"  nota: {job['nota_final']}")

    print("\n  versoes:")
    for e in job.get("versions", []):
        v = e["version"]
        print(f"    v{v}  validacao {'ok' if e.get('validado') else 'REPROVADA'}"
              f"  parecer {'sim' if e.get('review') else 'nao'}")
        ch = job_dir / f"changes-v{v}.json"
        if ch.is_file():
            c = json.loads(ch.read_text(encoding="utf-8"))
            for f in c.get("aplicadas", []):
                print(f"        corrigido: {f['fix']} — {f['efeito']}")
            for f in c.get("sem_efeito", []):
                print(f"        sem efeito: {f['fix']} — {f['efeito']}")

    if job.get("notas"):
        print("\n  notas:")
        for n in job["notas"]:
            print(f"    [{n['tipo']}] {n['texto']}")

    print("\n  historico:")
    for h in job.get("historico", []):
        extra = " ".join(f"{k}={v}" for k, v in h.items() if k not in ("em", "evento"))
        print(f"    {h['em']}  {h['evento']}  {extra}".rstrip())

    print("\n  arquivos:")
    for f in sorted(job_dir.iterdir()):
        print(f"    {f.name}")
    return 0


def cmd_note(a) -> int:
    """Anota no job algo que afetou a execucao -- inclusive limitacao do ambiente.

    Serve para o registro nao mentir por omissao: se o Designer nao conseguiu abrir a
    imagem, isso fica escrito no job, nao some.
    """
    job_dir = pathlib.Path(a.job).expanduser().resolve()
    job = load_job(job_dir)
    job.setdefault("notas", []).append({"em": now_iso(), "tipo": a.kind, "texto": a.text})
    log(job, a.kind, texto=a.text)
    save_job(job_dir, job)
    print(f"{a.kind} registrada")
    return 0


def cmd_list(_a) -> int:
    if not JOBS.is_dir():
        print("nenhum job")
        return 0
    for d in sorted(JOBS.iterdir(), reverse=True):
        if (d / "job.json").is_file():
            j = load_job(d)
            print(f"{j['job_id']:52} {j['status']:24} ciclo {j.get('cycle')}/{j.get('max_cycles')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new")
    p.add_argument("--client"); p.add_argument("--name")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--brief", help="briefing tecnico pronto")
    g.add_argument("--ad", help="direcao de arte (compilada depois por artdirection.py)")
    p.add_argument("--format", default="instagram-feed")
    p.add_argument("--contexto", default="SOCIAL", choices=["SOCIAL", "ANUNCIO"])
    p.set_defaults(fn=cmd_new)

    for name, fn in (("render", cmd_render), ("review", cmd_review)):
        p = sub.add_parser(name); p.add_argument("--job", required=True)
        p.add_argument("--version", type=int, required=True); p.set_defaults(fn=fn)

    p = sub.add_parser("inspecionar", help="registra o que voce viu no render final")
    p.add_argument("--job", required=True)
    p.add_argument("--version", type=int, required=True)
    p.add_argument("--veredito", required=True, choices=["ok", "corrigir"])
    p.add_argument("--parecer", required=True,
                   help="o que voce VIU: composicao, enquadramento, hierarquia, acabamento")
    p.set_defaults(fn=cmd_inspecionar)

    p = sub.add_parser("save-review"); p.add_argument("--job", required=True)
    p.add_argument("--version", type=int, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file"); g.add_argument("--stdin", action="store_true")
    p.set_defaults(fn=cmd_save_review)

    for name, fn in (("can-continue", cmd_can_continue), ("next-cycle", cmd_next_cycle),
                     ("show", cmd_show)):
        p = sub.add_parser(name); p.add_argument("--job", required=True); p.set_defaults(fn=fn)

    p = sub.add_parser("finalize"); p.add_argument("--job", required=True)
    p.add_argument("--version", type=int, required=True)
    p.add_argument("--status", required=True,
                   choices=["aprovada", "entregue-com-ressalva", "parada",
                            "bloqueada-falta-asset", "bloqueada-decisao-humana"])
    p.add_argument("--note", default=""); p.set_defaults(fn=cmd_finalize)

    p = sub.add_parser("note"); p.add_argument("--job", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--kind", default="nota",
                   choices=["nota", "limitacao-tecnica", "bloqueio"])
    p.set_defaults(fn=cmd_note)

    sub.add_parser("list").set_defaults(fn=cmd_list)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
