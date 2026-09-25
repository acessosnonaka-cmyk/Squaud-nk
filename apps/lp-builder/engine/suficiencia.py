#!/usr/bin/env python3
"""Piso de suficiencia da Landing Page: o portao que o lp-qa nao e.

Por que existe: a LP da Academia Mergulho passou no lp-qa com tudo verde --
5 secoes, zero problema de contraste, zero overflow, 165 KB, 4 CTAs -- e era
uma pagina de academia sem uma unica fotografia, com tarja de debug amarela
sobre a primeira dobra. O QA mede engenharia. Nada media se a pagina presta.

A divisao e deliberada e o pedido do gestor e explicito: lp_qa.py continua
sendo engenharia e NAO vira critico de arte. Este arquivo e o outro lado.

Duas naturezas de checagem aqui, e elas nao se substituem:

  MECANICO   o que da para provar lendo o arquivo: marca de debug na pagina
             candidata, imagem realmente referenciada, direcao mobile propria.
             Barra sozinho.
  RESPONDIDO as perguntas que so quem dirigiu a pagina pode responder. O motor
             nao julga se a resposta e boa -- exige que ela exista, seja
             especifica o bastante para alguem discordar, e nao seja a legenda
             do arranjo padrao. Mesma logica do piso do Designer.

Uso:
    suficiencia.py schema
    suficiencia.py checar --pagina <index.html> --respostas <suficiencia.json>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
REFERENCIAS = RAIZ.parent / "referencias"

# --------------------------------------------------------------- mecanico

# Marca de ferramenta interna. Nenhuma delas pode existir na versao candidata a
# entrega: a tarja de spec da Mergulho estava no canto superior esquerdo, sobre
# o H1, na mesma cor do CTA -- e foi assim que o gestor recebeu a pagina.
MARCAS_DE_DEBUG = (
    (r'data-slots\s*=\s*["\']spec', "atributo data-slots=spec liga as tarjas de especificacao"),
    (r'\bIMG-\d{2}\b',              "rotulo de slot de imagem (IMG-01) visivel na pagina"),
    (r'class=["\'][^"\']*\b(debug|spec-|placeholder|lorem)\b', "classe de debug/placeholder"),
    (r'\bLOREM IPSUM\b',            "texto de preenchimento"),
    (r'<!--\s*TODO',                "TODO deixado no arquivo"),
    (r'\bFIXME\b',                  "FIXME deixado no arquivo"),
    (r'outline\s*:\s*\d+px\s+solid\s+(red|magenta|lime)', "grade de diagnostico"),
)

RE_IMAGEM = (r'<img\b', r'<picture\b', r'background-image\s*:\s*url\(', r'<source\b[^>]*type=["\']image')


def checar_mecanico(html: str) -> tuple[list, dict]:
    falhas, medidas = [], {}

    achadas = [msg for pad, msg in MARCAS_DE_DEBUG if re.search(pad, html, re.I)]
    medidas["marcas_de_debug"] = len(achadas)
    for msg in achadas:
        falhas.append(f"ACABAMENTO: {msg}. Versao candidata a entrega nao carrega "
                      "ferramenta interna visivel")

    n_img = sum(len(re.findall(p, html, re.I)) for p in RE_IMAGEM)
    medidas["imagens_referenciadas"] = n_img
    if n_img == 0:
        falhas.append("ASSETS: a pagina nao referencia nenhuma imagem. Isso pode estar certo, "
                      "e entao a resposta de 'assets' precisa provar que o acervo foi "
                      "procurado e nao existe -- com o estado de evidencia da fonte, nao "
                      "com uma frase")

    # Direcao mobile propria: nao basta encolher. Procuramos regra de midia que
    # mude layout, nao so tamanho de fonte.
    medias = re.findall(r'@media[^{]*\(max-width[^{]*\{', html, re.I)
    medidas["regras_de_midia"] = len(medias)
    if len(medias) < 2:
        falhas.append("MOBILE: menos de duas regras de midia. Mobile com direcao propria "
                      "muda composicao, ordem ou escala -- desktop espremido nao conta")
    return falhas, medidas


# --------------------------------------------------------------- respondido

PERGUNTAS = {
    "especificidade": "o que nesta pagina pertence a ESTE cliente e nao sobreviveria a troca de logo",
    "conceito":       "a ideia que organiza a experiencia, alem da sequencia de componentes",
    "primeira_dobra": "o que a primeira dobra entrega em poucos segundos: quem e, o que oferece, por que importa, por que acreditar, o que fazer",
    "direcao_de_arte": "a decisao de direcao -- tipografia, escala, composicao, espaco, fotografia -- alem de preencher os slots",
    "assets":         "qual foi o melhor material disponivel e o que foi feito com ele; se nao ha material, qual busca provou isso",
    "narrativa":      "a progressao entre as secoes: por que esta ordem e nao outra",
    "prova":          "que evidencia verificavel sustenta o que a pagina promete",
    "conversao":      "por que este CTA, nesta posicao, com esta objecao tratada antes",
}

VAZIO = ("", "-", "n/a", "na", "nao se aplica", "nenhum", "nenhuma", "ok", "sim", "nao")

# Vocabulario de quem descreve o layout padrao em vez de nomear uma decisao.
# Mesmo mecanismo do piso do Designer, calibrado para pagina.
SLOTS_PADRAO = ("hero", "primeira secao", "secao de beneficios", "rodape", "cabecalho",
                "headline", "subtitulo", "subheadline", "botao", "cta no topo", "menu",
                "card", "lista de itens", "depoimentos", "formulario", "banner",
                "acima da dobra", "abaixo", "centralizad", "alinhad")
OPERACOES = ("recorte", "sangria", "escala forcada", "sobrepo", "grid quebrado", "negativ",
             "diagonal", "tipografia como", "numero como", "respiro", "assimetr",
             "fotografia de", "foto real", "close", "plano aberto", "contraste de escala",
             "corte na palavra", "linha que atravessa", "cor como codigo", "editorial",
             "sequencia", "progressao", "ritmo entre", "quebra de", "ancorad")


def _so_descreve_o_padrao(valor: str) -> bool:
    v = valor.lower()
    return any(s in v for s in SLOTS_PADRAO) and not any(o in v for o in OPERACOES)


def checar_respostas(resp: dict) -> list:
    if not isinstance(resp, dict):
        return ["o arquivo de suficiencia nao e um objeto JSON"]
    falhas = []
    for campo, pergunta in PERGUNTAS.items():
        valor = str(resp.get(campo, "") or "").strip()
        if valor.lower().rstrip(".") in VAZIO:
            falhas.append(f"{campo.upper()}: nao respondido -- {pergunta}")
        elif len(valor) < 40:
            falhas.append(f"{campo.upper()}: resposta curta demais para ser verificavel "
                          f"({len(valor)} caracteres) -- {pergunta}")
        elif campo in ("conceito", "direcao_de_arte") and _so_descreve_o_padrao(valor):
            falhas.append(
                f"{campo.upper()}: isso descreve ONDE os blocos ficaram, nao uma decisao. "
                "Dizer que tem hero, secao de beneficios e rodape e a legenda do arranjo "
                "padrao -- e exatamente o que este piso existe para rejeitar. Nomeie o que "
                "acontece com a PAGINA: recorte, escala forcada, sobreposicao, grid quebrado, "
                "assimetria, progressao, tipografia como imagem, cor como codigo")
    return falhas


def referencias_disponiveis() -> list:
    if not REFERENCIAS.is_dir():
        return []
    return sorted(p.name for p in REFERENCIAS.iterdir()
                  if p.suffix.lower() in (".html", ".png", ".jpg", ".jpeg", ".webp", ".pdf"))


# --------------------------------------------------------------- cli

def cmd_schema(_a) -> int:
    print(json.dumps({k: f"<{v}>" for k, v in PERGUNTAS.items()}, ensure_ascii=False, indent=2))
    return 0


def cmd_checar(a) -> int:
    pagina = pathlib.Path(a.pagina).expanduser()
    if not pagina.is_file():
        print(f"ERRO: {pagina} nao existe", file=sys.stderr)
        return 2
    html = pagina.read_text(encoding="utf-8", errors="replace")

    falhas_m, medidas = checar_mecanico(html)

    resp_p = pathlib.Path(a.respostas).expanduser()
    if not resp_p.is_file():
        print(f"ERRO: {resp_p} nao existe. O piso de suficiencia da LP exige as respostas "
              "antes de a pagina ser considerada pronta (veja: suficiencia.py schema).",
              file=sys.stderr)
        return 2
    try:
        resp = json.loads(resp_p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERRO: {resp_p} ilegivel: {e}", file=sys.stderr)
        return 2
    falhas_r = checar_respostas(resp)

    print(f"MEDIDO  imagens={medidas['imagens_referenciadas']}  "
          f"regras_de_midia={medidas['regras_de_midia']}  "
          f"marcas_de_debug={medidas['marcas_de_debug']}")
    refs = referencias_disponiveis()
    print(f"REGUA   referencias aprovadas disponiveis: "
          f"{len(refs)}{' — ' + ', '.join(refs[:4]) if refs else ' (nenhuma; ver referencias/README.md)'}")

    falhas = falhas_m + falhas_r
    if falhas:
        print(f"\nPISO DA LP: NAO PASSOU — {len(falhas)} pendencia(s)\n")
        for f in falhas:
            print(f"  - {f}")
        print("\nNao ha resposta certa, ha resposta concreta. Se a pagina realmente nao tem o "
              "que responder, ela ainda nao esta pronta para ir ao Revisor: mude a pagina, "
              "nao o texto.")
        return 2
    print("\nPISO DA LP: PASSOU — a pagina pode seguir para o Revisor abrir o render.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("schema", help="as perguntas do piso, para preencher")
    s.set_defaults(fn=cmd_schema)
    c = sub.add_parser("checar", help="roda o piso na pagina renderizada")
    c.add_argument("--pagina", required=True)
    c.add_argument("--respostas", required=True)
    c.set_defaults(fn=cmd_checar)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
