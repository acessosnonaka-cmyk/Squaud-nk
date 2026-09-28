#!/usr/bin/env python3
"""O nome digitado nao e a identidade do cliente. O CLIENT_ID e.

O furo apareceu em producao: a mesma conta entrou numa demanda como
`clinica-vitta` e noutra como `clinica-aurora`, e o motor tratou as duas como
clientes diferentes porque `slug()` nao sabe que sao a mesma coisa. Duas
memorias, duas Source of Truth, e ninguem avisado.

O que este teste garante, nos dois sentidos:

  MESMO      dois apelidos do mesmo cliente chegam ao mesmo CLIENT_ID
  DIFERENTE  nomes parecidos continuam sendo clientes diferentes
  HISTORICO  demanda aberta sob o nome antigo continua alcancavel
  NADA PERDIDO  fusao nao apaga: anexa, concatena e fica registrada

    python3 agents/diretor-operacoes/testes/teste-identidade-cliente.py [-v]
"""
from __future__ import annotations

import io
import os
import pathlib
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

TMP = tempfile.mkdtemp(prefix="squad-nk-identidade-")
os.environ["SQUAD_DATA_HOME"] = TMP

from engine import demanda, modelo   # noqa: E402

falhas, feitos = [], []
VERBOSE = "-v" in sys.argv


def checar(nome: str, ok: bool, detalhe: str = "") -> None:
    feitos.append(nome)
    if not ok:
        falhas.append(f"{nome}{' · ' + detalhe if detalhe else ''}")
    if VERBOSE:
        print(f"  {'ok   ' if ok else 'FALHA'} {nome}")


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


def nova(cliente: str, titulo: str) -> str:
    _, saida = roda(demanda.cmd_nova, cliente=cliente, titulo=titulo,
                    descricao="pedido do gestor", objetivo="obj", contexto="",
                    prioridade="normal", fonte=None)
    return saida.strip().split()[-1]


def fonte(cliente, titulo, resumo, estado="ENCONTRADO", busca=None):
    return roda(demanda.cmd_cliente_fonte_add, cliente=cliente, classe="fato",
                titulo=titulo, resumo=resumo, ref=None, link=None, fonte_externa=None,
                demanda=None, estado=estado, busca=busca, verificado_em=None)


# ============================================================ I1 · cliente novo
sid = modelo.canonico("Clínica Vitta", criar=True)
checar("I1 · cliente novo ganha CLIENT_ID a partir do nome",
       sid == "clinica-vitta", sid)
checar("I1 · acento nao cria cliente novo",
       modelo.canonico("Clinica Vitta") == sid, modelo.canonico("Clinica Vitta"))
checar("I1 · caixa e espaco nao criam cliente novo",
       modelo.canonico("CLÍNICA   VITTA") == sid)

# ============================================================ I2 · nomes parecidos NAO se fundem
outro = modelo.canonico("Clínica Vita", criar=True)
checar("I2 · 'Clinica Vita' e 'Clinica Vitta' sao clientes diferentes",
       outro != sid, f"{outro} vs {sid}")
checar("I2 · e ambos existem no registro",
       {sid, outro} <= {i["id"] for i in modelo.identidades()["identidades"]})

fonte("Clínica Vitta", "Ticket", "Ticket medio de 2400 reais.")
fonte("Clínica Vita", "Ticket", "Ticket medio de 180 reais.")
ctx_a = modelo.contexto_cliente(sid)
ctx_b = modelo.contexto_cliente(outro)
checar("I2 · a Source of Truth de um nao vaza para o outro",
       "2400" in str(ctx_a) and "2400" not in str(ctx_b), str(ctx_b)[:150])

# ============================================================ I3 · apelido liga ao mesmo id
modelo.adicionar_alias(sid, "Vitta Estetica")
checar("I3 · apelido chega ao mesmo CLIENT_ID",
       modelo.canonico("Vitta Estetica") == sid, modelo.canonico("Vitta Estetica"))
checar("I3 · e a Source of Truth e a mesma",
       "2400" in str(modelo.contexto_cliente("Vitta Estetica")))

# ============================================================ I4 · apelido tomado e recusado
code, msg = None, ""
try:
    modelo.adicionar_alias(outro, "Vitta Estetica")
except modelo.ErroDeEstado as e:
    code, msg = None, str(e)
checar("I4 · apelido que ja e de outro cliente e recusado", "ja e o cliente" in
       msg.replace("já", "ja").replace("é", "e"), msg[:140])
checar("I4 · a recusa diz o que ha em disco do outro lado",
       "em disco" in msg.lower(), msg[:200])

# ============================================================ I5 · fusao nunca e silenciosa
aurora = modelo.canonico("Clinica Aurora", criar=True)
fonte("Clinica Aurora", "Horario", "Atende das 9h as 18h.")
dem_aurora = nova("Clinica Aurora", "Relatorio do mes sob o nome antigo")

msg = ""
try:
    modelo.adicionar_alias(sid, "Clinica Aurora")
except modelo.ErroDeEstado as e:
    msg = str(e)
checar("I5 · ligar apelido que tem dado proprio e recusado sem --fundir",
       "fundir" in msg, msg[:160])
checar("I5 · a recusa mostra o que seria juntado",
       "fonte" in msg or "demanda" in msg, msg[:200])
checar("I5 · e nada foi alterado",
       modelo.canonico("Clinica Aurora") == aurora)

# ============================================================ I6 · fusao explicita
antes_vitta = len(modelo.carregar_fontes(sid).get("fontes", []))
antes_aurora = len(modelo.carregar_fontes(aurora).get("fontes", []))
modelo.adicionar_alias(sid, "Clinica Aurora", fundir=True)

checar("I6 · depois da fusao os dois nomes chegam ao mesmo CLIENT_ID",
       modelo.canonico("Clinica Aurora") == sid and modelo.canonico("Clínica Vitta") == sid,
       modelo.canonico("Clinica Aurora"))
depois = modelo.carregar_fontes(sid).get("fontes", [])
checar("I6 · nenhuma fonte foi perdida",
       len(depois) == antes_vitta + antes_aurora,
       f"{len(depois)} != {antes_vitta} + {antes_aurora}")
checar("I6 · a fonte trazida diz de onde veio",
       any(f.get("fundida_de") == "clinica-aurora" for f in depois))
checar("I6 · a fonte trazida entra na Source of Truth do canonico",
       "9h" in str(modelo.contexto_cliente(sid)))
checar("I6 · o arquivo de origem nao foi apagado, virou .fundido",
       (modelo.dir_clientes() / "clinica-aurora.fontes.json.fundido").is_file())
ident = [i for i in modelo.identidades()["identidades"] if i["id"] == sid][0]
checar("I6 · a fusao fica registrada na identidade", bool(ident.get("fusoes")),
       str(ident)[:160])
checar("I6 · a identidade absorvida some do registro",
       aurora not in {i["id"] for i in modelo.identidades()["identidades"]})

# ============================================================ I7 · historico continua alcancavel
d = modelo.carregar(dem_aurora)
checar("I7 · a demanda antiga NAO foi reescrita (ela e registro do que houve)",
       d["cliente"] == aurora, d["cliente"])
nomes = modelo.nomes_do_cliente("Clínica Vitta")
checar("I7 · mas o nome antigo entra na busca do canonico", aurora in nomes, str(nomes))
_, saida = roda(demanda.cmd_listar, status=None, cliente="Clínica Vitta")
checar("I7 · e a demanda antiga aparece ao listar pelo canonico",
       dem_aurora in saida, saida[:200])
_, saida = roda(demanda.cmd_listar, status=None, cliente="Clinica Aurora")
checar("I7 · e tambem ao listar pelo apelido", dem_aurora in saida, saida[:200])

# ============================================================ I8 · o cliente errado continua fora
_, saida = roda(demanda.cmd_listar, status=None, cliente="Clínica Vita")
checar("I8 · o cliente de nome parecido nao herda a demanda",
       dem_aurora not in saida, saida[:200])
checar("I8 · nem a Source of Truth",
       "9h" not in str(modelo.contexto_cliente(outro)))

# ============================================================ I9 · ambiguidade nao se resolve no palpite
dados = modelo.identidades()
dados["identidades"].append({"id": "clinica-terceira", "nome": "Terceira",
                             "aliases": ["Vitta Estetica"], "criado_em": modelo.agora(),
                             "origem": "teste"})
modelo.salvar_identidades(dados)
msg = ""
try:
    modelo.canonico("Vitta Estetica")
except modelo.ErroDeEstado as e:
    msg = str(e)
checar("I9 · nome que alcanca dois clientes levanta ambiguidade, nao escolhe",
       "ambiguidade" in msg.lower() or "alcanca" in msg.replace("ç", "c"), msg[:160])
checar("I9 · e a mensagem nomeia os dois candidatos",
       "clinica-vitta" in msg and "clinica-terceira" in msg, msg[:200])

shutil.rmtree(TMP, ignore_errors=True)

if falhas:
    print(f"\n{len(falhas)} FALHA(S) em {len(feitos)} checagens")
    for f in falhas:
        print(f"  x {f}")
    sys.exit(1)
print(f"\nteste-identidade-cliente: {len(feitos)} checagens "
      "(mesmo cliente converge, parecido nao funde, historico sobrevive) · OK")
sys.exit(0)
