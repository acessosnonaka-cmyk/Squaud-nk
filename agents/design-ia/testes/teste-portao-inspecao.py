#!/usr/bin/env python3
"""O portão que impede a peça de seguir sem alguém ter olhado para ela.

Nenhum programa obriga um agente a olhar. O que dá para travar é o handoff sem
o registro do que foi visto — e exigir observação concreta, porque parecer
genérico é o mesmo que não ter olhado.

    python3 agents/design-ia/testes/teste-portao-inspecao.py
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import types

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "engine"))

from PIL import Image                                       # noqa: E402
import job as J                                             # noqa: E402

falhas = []


def checar(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")


def rodar(fn, **kw):
    """Chama um cmd_* e devolve (rc, stderr)."""
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        rc = fn(types.SimpleNamespace(**kw))
    return rc, err.getvalue()


PARECER = ("Peca 1080x1350: foto a esquerda, headline em duas linhas sem estouro, "
           "CTA com respiro e assinatura no rodape. Cantos limpos.")

with tempfile.TemporaryDirectory() as tmp:
    jd = pathlib.Path(tmp) / "job-teste"
    jd.mkdir()
    (jd / "job.json").write_text(json.dumps({
        "id": "job-teste", "client": "teste", "format_name": "instagram-feed",
        "status": "rendered", "versions": [], "log": [],
    }), encoding="utf-8")
    Image.new("RGB", (1080, 1350), (20, 20, 20)).save(jd / "v1.png")
    (jd / "brief.v1.json").write_text(json.dumps({
        "objetivo": "teste", "formato": "instagram-feed", "copy": {},
    }), encoding="utf-8")

    # -------------------------------------- 1 · handoff sem inspeção nenhuma
    rc, err = rodar(J.cmd_review, job=str(jd), version=1)
    checar("1/review-sem-inspecao-recusa", rc != 0)
    checar("1/review-diz-o-que-fazer", "inspecionar" in err, err.strip()[:90])

    # -------------------------------------- 2 · parecer que não diz nada
    for vazio in ("", "ok", "tudo certo", "aprovado, pode seguir"):
        rc, err = rodar(J.cmd_inspecionar, job=str(jd), version=1,
                        veredito="ok", parecer=vazio)
        checar(f"2/parecer[{vazio or 'branco'}]-recusa", rc != 0)
    checar("2/nao-gravou-nada", not (jd / "inspecao.v1.json").is_file())

    # -------------------------------------- 3 · versão que não existe
    rc, _ = rodar(J.cmd_inspecionar, job=str(jd), version=9,
                  veredito="ok", parecer=PARECER)
    checar("3/versao-inexistente-recusa", rc != 0)

    # -------------------------------------- 4 · inspeção que pede correção
    rc, _ = rodar(J.cmd_inspecionar, job=str(jd), version=1, veredito="corrigir",
                  parecer="A headline encosta na borda direita e o eyebrow ficou pequeno demais.")
    checar("4/corrigir-grava", rc == 0)
    rc, err = rodar(J.cmd_review, job=str(jd), version=1)
    checar("4/review-apos-corrigir-recusa", rc != 0)
    checar("4/review-manda-renderizar-de-novo", "nova versao" in err, err.strip()[:90])

    # -------------------------------------- 5 · inspeção de verdade libera
    rc, _ = rodar(J.cmd_inspecionar, job=str(jd), version=1,
                  veredito="ok", parecer=PARECER)
    checar("5/ok-grava", rc == 0)
    reg = json.loads((jd / "inspecao.v1.json").read_text(encoding="utf-8"))
    checar("5/registra-o-parecer", reg["parecer"] == PARECER)
    checar("5/registra-o-veredito", reg["veredito"] == "ok")
    rc, err = rodar(J.cmd_review, job=str(jd), version=1)
    #   O portao parou de barrar. O handoff em si depende do Revisor instalado,
    #   que nao e o que este teste prova -- o que se prova aqui e que a recusa
    #   nao vem mais da inspecao.
    checar("5/portao-liberou", "nao foi inspecionada" not in err and "terminou em" not in err,
           err.strip()[:90])

    # -------------------------------------- 6 · a prancha é gerada no render
    fonte = (RAIZ / "engine" / "job.py").read_text(encoding="utf-8")
    checar("6/render-gera-prancha", "inspecao" in fonte and "inspecao_prancha" in fonte)

if falhas:
    print(f"\n{len(falhas)} FALHA(S)")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print("\nteste-portao-inspecao: sem inspeção, parecer vazio, veredito corrigir · OK")
sys.exit(0)
