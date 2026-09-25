#!/usr/bin/env python3
"""Testes adversariais da rodada P0 — as invariantes que a produção real furou.

Cada bloco reproduz um furo que aconteceu de verdade, não um caso hipotético:

  A  SOURCE OF TRUTH   "não existe fotografia própria" entrou como FATO sem ninguém
                       ter aberto as pastas MERGULHO e MERGULHO FIT do Drive. A LP foi
                       construída correta sobre uma premissa falsa.
  B  LANDING PAGE      a página passou o lp_qa com tudo verde e saiu com tarja amarela
                       de debug sobre o H1, sem uma única fotografia. Ninguém abriu a
                       página — o Revisor deu parecer lendo o HTML.
  C  CONSULTA          o Gestor de Tráfego nunca fez uma chamada ao Meta, porque não tem
                       o conector. Ele analisava o resumo do briefing achando que
                       analisava a conta.

Roda inteiro em diretório temporário: nenhum dado de cliente, nenhum conector, nenhum
especialista acionado.

    python3 agents/diretor-operacoes/testes/teste-competencia-producao.py [-v]
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

RAIZ = pathlib.Path(__file__).resolve().parents[1]
REPO = RAIZ.parents[1]
sys.path.insert(0, str(RAIZ))

TMP = tempfile.mkdtemp(prefix="squad-nk-p0-")
os.environ["SQUAD_DATA_HOME"] = TMP

from engine import demanda, modelo   # noqa: E402

import importlib.util as _iu         # noqa: E402


def _carregar(nome, arquivo):
    spec = _iu.spec_from_file_location(nome, REPO / "apps" / "lp-builder" / "engine" / arquivo)
    m = _iu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


suficiencia = _carregar("lp_suficiencia_teste", "suficiencia.py")
render = _carregar("lp_render_teste", "render.py")

falhas, feitos = [], []
VERBOSO = "-v" in sys.argv


def checar(nome: str, condicao: bool, detalhe: str = "") -> None:
    feitos.append(nome)
    if not condicao:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")
    if VERBOSO:
        print(f"  {'ok  ' if condicao else 'FALHA'} {nome}")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def roda(fn, **kw):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = fn(Args(**kw))
    except modelo.ErroDeEstado as exc:
        return None, str(exc)
    return code, buf.getvalue()


def nova_demanda(titulo: str, descricao: str, cliente="cliente-ficticio-p0") -> str:
    _, saida = roda(demanda.cmd_nova, titulo=titulo, cliente=cliente, descricao=descricao,
                    objetivo="prova de invariante", contexto="", prioridade="normal", fonte=None)
    return saida.strip().split()[-1]


def add_fonte(cliente, **kw):
    base = dict(cliente=cliente, classe="fato", titulo="t", resumo="r", ref=None, link=None,
                fonte_externa=None, demanda=None, estado=None, busca=None, verificado_em=None)
    base.update(kw)
    return roda(demanda.cmd_cliente_fonte_add, **base)


# ============================================================ A · SOURCE OF TRUTH
# A afirmação que destruiu a LP: ausência declarada como fato, sem busca nenhuma.

CLI_A = "cliente-sot-p0"

code, msg = add_fonte(CLI_A, titulo="Acervo fotográfico",
                      resumo="Não existe fotografia própria da academia.", estado="ENCONTRADO")
checar("A1 · ausência marcada ENCONTRADO é recusada", code is None, f"exit={code}")
checar("A1 · a recusa explica que ausência exige busca",
       "busca" in (msg or "").lower(), (msg or "")[:120])

code, msg = add_fonte(CLI_A, titulo="Acervo fotográfico",
                      resumo="Não há fotografia própria.", estado="NAO_ENCONTRADO_APOS_BUSCA")
checar("A2 · NAO_ENCONTRADO_APOS_BUSCA sem --busca é recusado", code is None, f"exit={code}")

code, msg = add_fonte(CLI_A, titulo="Acervo fotográfico", classe="fato",
                      resumo="Não há fotografia própria da unidade.",
                      estado="NAO_ENCONTRADO_APOS_BUSCA",
                      busca="Drive do cliente, busca por 'foto', 'jpg', 'acervo' e varredura das "
                            "pastas MERGULHO e MERGULHO FIT: 0 imagem, 2 documentos abertos.")
checar("A3 · ausência com busca descrita é aceita", code == 0, f"exit={code}")

code, msg = add_fonte(CLI_A, titulo="Tabela de preços 2026", classe="fato",
                      resumo="Mensalidade de R$ 149 no plano anual.", estado="NAO_VERIFICADO")
checar("A4 · fonte NAO_VERIFICADO é aceita (não é mentira, é lacuna)", code == 0, f"exit={code}")

ctx = modelo.contexto_cliente(CLI_A)
canon = " ".join(str(x) for x in ctx.get("fontes_canonicas", []))
nao_est = " ".join(str(x) for x in ctx.get("nao_estabelecido", []))
checar("A5 · ausência verificada viaja como Source of Truth, marcada",
       "ausência verificada" in canon, canon[:160])
checar("A6 · fonte não verificada NÃO viaja como fato",
       "149" not in canon, canon[:160])
checar("A7 · fonte não verificada viaja no bloco NÃO ESTABELECIDO",
       "149" in nao_est, nao_est[:160])

dem_a = nova_demanda("Briefing carrega a lacuna", "quero a LP", cliente=CLI_A)
roda(demanda.cmd_planejar, demanda=dem_a, plano="lp")
roda(demanda.cmd_job_add, demanda=dem_a, agente="lp-builder", objetivo="construir a página",
     entrada=None, saida="index.html publicado", depende=None, criterio=None, restricao=None,
     fonte=None)
_, brief = roda(demanda.cmd_briefing, demanda=dem_a, job="JOB-001", json=False)
checar("A8 · o briefing do especialista imprime o bloco NÃO ESTABELECIDO",
       "NÃO ESTABELECIDO" in brief.upper(), brief[-400:])


# ============================================================ B · LANDING PAGE
# B1..B3 o piso. B4 a captura assinada. B5..B9 o gate.

PAG_RUIM = """<!doctype html><html><head><style>
@media (max-width:768px){h1{font-size:32px}}
</style></head><body data-slots="spec">
<div class="slot" data-id="IMG-01">IMG-01</div><h1>Academia</h1>
<a href="https://wa.me/x">Quero treinar</a></body></html>"""

falhas_m, medidas = suficiencia.checar_mecanico(PAG_RUIM)
texto_m = " ".join(falhas_m)
checar("B1 · o piso vê a tarja de debug", "data-slots=spec" in texto_m, texto_m[:120])
checar("B1 · o piso vê o rótulo de slot de imagem", "IMG-01" in texto_m, texto_m[:120])
checar("B1 · o piso vê que não há imagem", medidas["imagens_referenciadas"] == 0)
checar("B1 · o piso vê mobile sem direção própria", "MOBILE" in texto_m, texto_m[:200])

TEMPLATE = {
    "especificidade": "A página tem o nome e o endereço do cliente no rodapé, como toda página.",
    "conceito": "Hero no topo, seção de benefícios no meio, depoimentos e rodapé, tudo centralizado.",
    "primeira_dobra": "Headline com o nome, subtítulo e botão de WhatsApp acima da dobra da página.",
    "direcao_de_arte": "Cabeçalho fixo, hero com headline grande, cards nos benefícios e botão no topo.",
    "assets": "Não há material disponível para usar nesta página, então ficou sem fotografia.",
    "narrativa": "ok",
    "prova": "-",
    "conversao": "CTA de WhatsApp no topo e no rodapé da página, como sempre se faz.",
}
fr = " ".join(suficiencia.checar_respostas(TEMPLATE))
checar("B2 · conceito que só descreve o arranjo padrão é recusado", "CONCEITO" in fr, fr[:140])
checar("B2 · direção de arte que só lista blocos é recusada", "DIRECAO_DE_ARTE" in fr, fr[:140])
checar("B2 · resposta vazia é recusada", "NARRATIVA" in fr and "PROVA" in fr, fr[:200])

BOM = json.loads((REPO / "agents/diretor-operacoes/testes/fixtures/lp-suficiencia-ok.json")
                 .read_text(encoding="utf-8")) if (
    REPO / "agents/diretor-operacoes/testes/fixtures/lp-suficiencia-ok.json").is_file() else {
    "especificidade": "As três fotografias são do salão de peso livre, da turma de funcional das 6h "
                      "e da área de cardio DESTA unidade, com o piso e os equipamentos que o aluno "
                      "vai encontrar; trocar o logo derruba a página inteira.",
    "conceito": "Horário como argumento: a página abre pela restrição real do aluno, com a "
                "fotografia em sangria disputando espaço com a tipografia em escala forçada, antes "
                "de qualquer lista de modalidade.",
    "primeira_dobra": "Quem é, onde fica, o que oferece, o horário que resolve a objeção, a foto "
                      "própria que prova que o lugar existe e o CTA de aula experimental sem rolagem.",
    "direcao_de_arte": "Grid de duas colunas com a fotografia em sangria e recorte deslocado, "
                       "headline com entrelinha 0.92 e tracking negativo funcionando como imagem, "
                       "verde-sinal como código em uma palavra só, tira de fotos sem respiro.",
    "assets": "Três fotografias próprias da unidade encontradas na pasta do Drive; a de peso livre "
              "virou a abertura em sangria por ter profundidade, as outras duas entraram em recorte "
              "vertical na tira.",
    "narrativa": "Parte da objeção que mais mata matrícula — horário —, vai para a prova visual de "
                 "que o lugar existe, depois para o depoimento de resultado, e só então repete o CTA.",
    "prova": "Depoimento nominal com data de início, fotografias próprias datadas da unidade e "
             "endereço verificável; nada de número de aluno que a academia não comprova.",
    "conversao": "WhatsApp é o único canal respondido no mesmo dia, então o CTA é aula experimental "
                 "— compromisso baixo — ao lado da headline, repetido em faixa presa ao rodapé no "
                 "celular, depois de a objeção de resultado ter sido tratada.",
}
checar("B3 · respostas concretas passam o piso (o piso é passável)",
       suficiencia.checar_respostas(BOM) == [], str(suficiencia.checar_respostas(BOM))[:200])

# B4 · a captura é assinada contra o arquivo
LPD = pathlib.Path(TMP) / "lp"
LPD.mkdir(parents=True, exist_ok=True)
pagina = LPD / "index.html"
pagina.write_text("""<!doctype html><html><head><style>
.a{display:grid}
@media (max-width:900px){.a{grid-template-columns:1fr}}
@media (max-width:560px){.a{gap:0}}
</style></head><body><img src="f.jpg" alt="f"><h1>ok</h1></body></html>""", encoding="utf-8")
cap = LPD / "render"
cap.mkdir(exist_ok=True)
for nome in ("desktop", "mobile"):
    (cap / f"{nome}.png").write_bytes(b"PNG-falso-de-teste-" + nome.encode())
man = cap / "render.json"


def escrever_manifesto(paginas_sha):
    man.write_text(json.dumps({
        "pagina": str(pagina), "pagina_sha256": paginas_sha,
        "capturas": [{"nome": n, "arquivo": str(cap / f"{n}.png"),
                      "largura": 1440 if n == "desktop" else 390, "altura_total": 1000,
                      "sha256": render.sha(cap / f"{n}.png"), "bytes": 20}
                     for n in ("desktop", "mobile")],
        "gerado_em": "2026-09-25T00:00:00"}, ensure_ascii=False), encoding="utf-8")


escrever_manifesto(render.sha(pagina))
checar("B4 · manifesto fresco confere", render.verificar(man) == [], str(render.verificar(man)))

escrever_manifesto("0" * 64)
pb = " ".join(render.verificar(man))
checar("B4 · página alterada depois da captura invalida o parecer",
       "mudou depois da captura" in pb, pb[:140])

escrever_manifesto(render.sha(pagina))
(cap / "mobile.png").unlink()
pb = " ".join(render.verificar(man))
checar("B4 · captura que sumiu do disco é detectada", "sumiu do disco" in pb, pb[:140])
(cap / "mobile.png").write_bytes(b"PNG-falso-de-teste-mobile")
escrever_manifesto(render.sha(pagina))

man_so_desktop = cap / "so-desktop.json"
man_so_desktop.write_text(json.dumps({
    "pagina": str(pagina), "pagina_sha256": render.sha(pagina),
    "capturas": [{"nome": "desktop", "arquivo": str(cap / "desktop.png"), "largura": 1440,
                  "altura_total": 1000, "sha256": render.sha(cap / "desktop.png"), "bytes": 20}],
}), encoding="utf-8")
pb = " ".join(render.verificar(man_so_desktop))
checar("B4 · faltando a captura mobile o manifesto não vale",
       "falta a captura mobile" in pb, pb[:140])

# B5..B9 · o gate
suf = LPD / "suficiencia.json"
suf.write_text(json.dumps(BOM, ensure_ascii=False), encoding="utf-8")


def demanda_lp(titulo, artefatos, com_revisor=False, revisor_arts=None, revisor_resumo="ok"):
    dem = nova_demanda(titulo, "quero uma landing page de conversão")
    roda(demanda.cmd_planejar, demanda=dem, plano="lp e revisão")
    roda(demanda.cmd_job_add, demanda=dem, agente="lp-builder", objetivo="construir a página",
         entrada=None, saida=None, depende=None, criterio=None, restricao=None, fonte=None)
    if com_revisor:
        roda(demanda.cmd_job_add, demanda=dem, agente="revisor-de-criacao",
             objetivo="revisar a página", entrada=None, saida=None, depende=["JOB-001"],
             criterio=None, restricao=None, fonte=None)
    roda(demanda.cmd_job_iniciar, demanda=dem, job="JOB-001")
    roda(demanda.cmd_job_concluir, demanda=dem, job="JOB-001", retorno=None, status="concluido",
         resumo="página construída", artefato=artefatos, decisao=None, observacao=None,
         proximo=None, pendencia=None)
    if com_revisor:
        roda(demanda.cmd_job_iniciar, demanda=dem, job="JOB-002")
        roda(demanda.cmd_job_concluir, demanda=dem, job="JOB-002", retorno=None,
             status="concluido", resumo=revisor_resumo, artefato=revisor_arts, decisao=None,
             observacao=None, proximo=None, pendencia=None)
    return dem


TODOS = [str(pagina), str(suf), str(man)]

t = " ".join(demanda._revisoes_faltando(modelo.carregar(demanda_lp("LP sem revisor", TODOS))))
checar("B5 · página sem job de Revisor ligado a ela trava o gate",
       "revisão obrigatória ausente" in t, t[:160])

t = " ".join(demanda._piso_lp_faltando(modelo.carregar(
    demanda_lp("LP sem suficiencia", [str(pagina), str(man)], com_revisor=True,
               revisor_arts=[str(cap / "desktop.png")]))))
checar("B6 · página sem suficiencia.json trava o gate", "sem suficiencia.json" in t, t[:160])

t = " ".join(demanda._piso_lp_faltando(modelo.carregar(
    demanda_lp("LP sem render", [str(pagina), str(suf)], com_revisor=True,
               revisor_arts=[str(cap / "desktop.png")]))))
checar("B7 · página sem render.json trava o gate", "sem render.json" in t, t[:160])

t = " ".join(demanda._piso_lp_faltando(modelo.carregar(
    demanda_lp("LP com parecer cego", TODOS, com_revisor=True, revisor_arts=["parecer.md"],
               revisor_resumo="li o HTML e o relatório do QA, aprovado"))))
checar("B8 · parecer que não nomeia a captura é recusado",
       "sem citar a captura" in t, t[:200])

pag_fantasma = str(LPD / "nao-existe.html")
t = " ".join(demanda._piso_lp_faltando(modelo.carregar(
    demanda_lp("LP fantasma", [pag_fantasma, str(suf), str(man)], com_revisor=True,
               revisor_arts=[str(cap / "desktop.png")]))))
checar("B9 · página declarada que não está no disco trava o gate",
       "não está no disco" in t, t[:160])

dem_ok = demanda_lp("LP completa", TODOS, com_revisor=True,
                    revisor_arts=[str(cap / "desktop.png"), str(cap / "mobile.png")],
                    revisor_resumo="abri desktop.png e mobile.png; composição e acabamento ok")
t = demanda._piso_lp_faltando(modelo.carregar(dem_ok)) + \
    demanda._revisoes_faltando(modelo.carregar(dem_ok))
checar("B10 · com piso, captura fresca e parecer que cita o render, o gate não trava por LP",
       t == [], str(t)[:300])

pagina.write_text(pagina.read_text(encoding="utf-8") + "<!-- mexeram depois -->", encoding="utf-8")
t = " ".join(demanda._piso_lp_faltando(modelo.carregar(dem_ok)))
checar("B11 · mexer na página depois do parecer volta a travar o gate",
       "mudou depois da captura" in t, t[:200])


# ============================================================ C · CONSULTA
CLI_C = "cliente-trafego-p0"
dem_c = nova_demanda("Relatório do mês", "quero o relatório de performance do mês", cliente=CLI_C)
roda(demanda.cmd_planejar, demanda=dem_c, plano="gestor analisa")
roda(demanda.cmd_job_add, demanda=dem_c, agente="gestor-de-trafego", objetivo="analisar a conta",
     entrada=None, saida=None, depende=None, criterio=None, restricao=None, fonte=None)


def abrir_consulta(**kw):
    base = dict(demanda=dem_c, job="JOB-001", fonte="meta_ads", pergunta=None, corte=None,
                hipotese=None)
    base.update(kw)
    return roda(demanda.cmd_consulta_abrir, **base)


code, msg = abrir_consulta(pergunta="quero ver os anúncios", corte="nível ad, 30 dias")
checar("C1 · pergunta que só nomeia a tabela é recusada", code is None, f"exit={code}")
checar("C1 · a recusa ensina a diferença", "não é pergunta" in (msg or ""), (msg or "")[:120])

code, msg = abrir_consulta(pergunta="a queda de CPL está concentrada em algum ad set ou é geral",
                           corte=None)
checar("C2 · consulta sem --corte é recusada", code is None, f"exit={code}")

code, msg = abrir_consulta(fonte="instagram_orgânico",
                           pergunta="a queda de CPL está concentrada em algum ad set ou é geral",
                           corte="nível adset, 60 dias")
checar("C3 · fonte fora da lista é recusada", code is None, f"exit={code}")

code, saida = abrir_consulta(
    pergunta="a queda de CPL de setembro está concentrada em algum ad set ou é geral",
    corte="nível adset, últimos 60 dias, quebra semanal, campos spend/impressions/ctr/"
          "frequency/results/cpl",
    hipotese="fadiga de criativo no conjunto de maior gasto — derruba se frequency estável")
checar("C4 · consulta bem formada é aberta", code == 0, f"exit={code}")
checar("C4 · a consulta recebe id", "CONSULTA-001" in saida, saida[:120])

roda(demanda.cmd_job_iniciar, demanda=dem_c, job="JOB-001")
roda(demanda.cmd_job_concluir, demanda=dem_c, job="JOB-001", retorno=None, status="concluido",
     resumo="relatório escrito", artefato=None, decisao=None, observacao=None, proximo=None,
     pendencia=None)
t = " ".join(demanda.avaliar_gate(modelo.carregar(dem_c)))
checar("C5 · consulta PENDENTE trava o gate", "CONSULTA-001" in t and "não recebeu" in t, t[:200])

code, msg = roda(demanda.cmd_consulta_responder, demanda=dem_c, consulta="CONSULTA-001",
                 arquivo=str(LPD / "nao-existe.json"), observacao=None, sem_dado=False)
checar("C6 · responder com arquivo que não existe é recusado", code is None, f"exit={code}")

code, msg = roda(demanda.cmd_consulta_responder, demanda=dem_c, consulta="CONSULTA-001",
                 arquivo=None, observacao="não deu", sem_dado=True)
checar("C7 · --sem-dado sem justificativa real é recusado", code is None, f"exit={code}")
checar("C7 · a recusa distingue 'não deu' de 'não tentei'",
       "não tentei" in (msg or ""), (msg or "")[:160])

bruto = LPD / "meta-adset-60d.json"
bruto.write_text('{"adsets": []}', encoding="utf-8")
code, saida = roda(demanda.cmd_consulta_responder, demanda=dem_c, consulta="CONSULTA-001",
                   arquivo=str(bruto), observacao="", sem_dado=False)
checar("C8 · responder com dado bruto em disco é aceito", code == 0, f"exit={code}")
t = " ".join(demanda.avaliar_gate(modelo.carregar(dem_c)))
checar("C8 · com a consulta respondida o gate não trava mais por ela",
       "CONSULTA-001" not in t, t[:200])

# lacuna declarada: fonte sem conector
code, _ = abrir_consulta(
    fonte="ga4", pergunta="quantos visitantes da LP chegaram ao clique de WhatsApp",
    corte="evento click_whatsapp, 30 dias, por origem/mídia")
checar("C9 · consulta a fonte sem conector é aberta normalmente", code == 0, f"exit={code}")
code, saida = roda(
    demanda.cmd_consulta_responder, demanda=dem_c, consulta="CONSULTA-002", arquivo=None,
    observacao="Não há conector de GA4 nesta sessão (docs/conectores.md §2) e a propriedade "
               "não foi compartilhada; o evento click_whatsapp também não aparece instrumentado.",
    sem_dado=True)
checar("C10 · --sem-dado com o que foi tentado é aceito", code == 0, f"exit={code}")
checar("C10 · o retorno diz que a lacuna viaja declarada",
       "DECLARADA" in saida.upper(), saida[:160])
t = " ".join(demanda.avaliar_gate(modelo.carregar(dem_c)))
checar("C11 · SEM_DADO não trava o gate", "CONSULTA-002" not in t, t[:200])
saida_gate = demanda.formatar_gate(modelo.carregar(dem_c), [])
checar("C11 · mas a lacuna aparece no gate, nomeada",
       "LACUNA DECLARADA" in saida_gate and "CONSULTA-002" in saida_gate, saida_gate[-400:])

shutil.rmtree(TMP, ignore_errors=True)

if falhas:
    print(f"\n{len(falhas)} FALHA(S) em {len(feitos)} checagens")
    for f in falhas:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"\nteste-competencia-producao: {len(feitos)} checagens adversariais "
      "(A Source of Truth, B piso e captura da LP, C consulta de dado) · OK")
sys.exit(0)
