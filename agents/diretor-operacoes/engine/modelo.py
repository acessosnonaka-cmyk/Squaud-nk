"""Estado persistente do Diretor de Operações.

Divisão de trabalho, deliberada: o LLM interpreta, planeja, decide o grafo e
delega. Este módulo só guarda, valida e transita estado. Nenhuma decisão de
roteamento mora aqui — se morasse, o Diretor deixaria de ser agente.

Onde os dados vivem: SQUAD_DATA_HOME (padrão ~/.squad-nk), subdiretório
diretor/. É a raiz de dados já declarada no .env.example, já coberta pelo
.gitignore, e a mesma que a aplicação web usa — demanda aberta no Claude Code e
demanda aberta pela web futura compartilham estado, sem migração.

Formato: um JSON por demanda, mais um event log append-only em JSONL. Sem banco:
são dezenas de demandas, não milhões, e arquivo é auditável a olho nu.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from datetime import datetime, timezone

if __package__ in (None, ""):                      # permite rodar por caminho direto
    import pathlib as _pl, sys as _sys
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
    from engine import roster                     # type: ignore
else:
    from . import roster

# --------------------------------------------------------------- caminhos

def data_home() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("SQUAD_DATA_HOME") or (pathlib.Path.home() / ".squad-nk")
    ).expanduser()


def raiz() -> pathlib.Path:
    return data_home() / "diretor"


def dir_demandas() -> pathlib.Path:
    return raiz() / "demandas"


def dir_clientes() -> pathlib.Path:
    return raiz() / "clientes"


def dir_demanda(demanda_id: str) -> pathlib.Path:
    return dir_demandas() / demanda_id


REPO = pathlib.Path(__file__).resolve().parents[3]
DIR_SCHEMAS = REPO / "agents" / "diretor-operacoes" / "schemas"


# --------------------------------------------------------------- estados

ESTADOS_DEMANDA = ["RECEBIDA", "PLANEJADA", "EM_EXECUCAO", "EM_REVISAO",
                   "AGUARDANDO_APROVACAO", "BLOQUEADA", "CONCLUIDA", "CANCELADA"]

# Transições permitidas. Fora disto, o CLI recusa — estado não anda por descuido.
TRANSICOES = {
    "RECEBIDA": {"PLANEJADA", "CANCELADA", "BLOQUEADA"},
    "PLANEJADA": {"EM_EXECUCAO", "BLOQUEADA", "CANCELADA"},
    "EM_EXECUCAO": {"EM_REVISAO", "AGUARDANDO_APROVACAO", "BLOQUEADA",
                    "CONCLUIDA", "CANCELADA"},
    "EM_REVISAO": {"EM_EXECUCAO", "AGUARDANDO_APROVACAO", "CONCLUIDA",
                   "BLOQUEADA", "CANCELADA"},
    "AGUARDANDO_APROVACAO": {"EM_EXECUCAO", "EM_REVISAO", "BLOQUEADA",
                             "CONCLUIDA", "CANCELADA"},
    "BLOQUEADA": {"EM_EXECUCAO", "PLANEJADA", "CANCELADA", "CONCLUIDA"},
    "CONCLUIDA": set(),
    "CANCELADA": set(),
}

ESTADOS_JOB = ["PENDENTE", "EM_EXECUCAO", "CONCLUIDO", "FALHOU",
               "BLOQUEADO", "AGUARDANDO_APROVACAO"]

def agentes_acionaveis() -> list:
    """Especialistas com executor real, lidos do roster oficial (squad.yaml).

    Lista copiada aqui vira lista desatualizada: quem entra ou sai do Squad muda
    no squad.yaml, e este motor enxerga a mudança no mesmo instante. Agente em
    estado `conceito` fica de fora de propósito — sem executor, job para ele é
    job que ninguém roda.
    """
    return roster.acionaveis()


ESTADOS_REQUISITO = ["PENDENTE", "CUMPRIDO", "BLOQUEADO", "NAO_APLICAVEL", "CANCELADO"]

# Teto de tentativas por job. O mesmo princípio do job.py do Designer: o limite
# vive em código, não na boa vontade do prompt. Sem isto, dois agentes ficam
# corrigindo um ao outro para sempre.
MAX_TENTATIVAS = 3

CLASSES_FEEDBACK = ["feedback_da_demanda", "preferencia_do_cliente", "regra_global"]

# Modo de execução carimbado em todo briefing. SILENT é a interface do Squad
# (seção 0 do prompt do Diretor): o especialista executa sem narrar etapa,
# handoff ou progresso. Viaja no contrato, e não na lembrança do Diretor —
# briefing improvisado à mão é justamente onde a regra se perde.
EXECUTION_MODE_PADRAO = "SILENT"   # enum em schemas/briefing.schema.json


class ErroDeEstado(Exception):
    """Operação recusada porque violaria a máquina de estados ou um contrato."""


# --------------------------------------------------------------- utilidades

def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (texto or "").lower()).strip("-")
    return s[:40] or "sem-nome"


def ler_json(caminho: pathlib.Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_json(caminho: pathlib.Path, dados: dict) -> None:
    """Gravação atômica: um Ctrl+C no meio não deixa demanda.json pela metade."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, caminho)


# --------------------------------------------------------------- validação

def _tipo_ok(valor, tipo: str) -> bool:
    return {
        "string": isinstance(valor, str), "integer": isinstance(valor, int),
        "number": isinstance(valor, (int, float)), "boolean": isinstance(valor, bool),
        "array": isinstance(valor, list), "object": isinstance(valor, dict),
    }.get(tipo, True)


def validar(dados: dict, nome_schema: str) -> list:
    """Validador mínimo contra os schemas de schemas/*.json.

    Cobre required, type e enum — que é o que os contratos deste sistema usam.
    Escrito à mão de propósito: o motor roda com o python do sistema, sem
    dependência externa, do mesmo jeito que os motores dos especialistas.
    """
    caminho = DIR_SCHEMAS / f"{nome_schema}.schema.json"
    if not caminho.is_file():
        return [f"schema ausente: {caminho.name}"]
    schema = ler_json(caminho)
    erros = []
    for campo in schema.get("required", []):
        if dados.get(campo) in (None, ""):
            erros.append(f"campo obrigatório ausente ou vazio: '{campo}'")
    for campo, regra in (schema.get("properties") or {}).items():
        if campo not in dados or dados[campo] is None:
            continue
        valor = dados[campo]
        tipo = regra.get("type")
        if tipo and not _tipo_ok(valor, tipo):
            erros.append(f"'{campo}': esperado {tipo}, veio {type(valor).__name__}")
        if regra.get("enum") and valor not in regra["enum"]:
            erros.append(f"'{campo}': '{valor}' fora de {regra['enum']}")
    return erros


# --------------------------------------------------------------- event log

def registrar_evento(demanda_id: str, evento: str, *, agente: str = "diretor-operacoes",
                     job: str | None = None, resumo: str = "") -> None:
    """Append-only. Guarda decisão e resultado — nunca raciocínio interno."""
    linha = {"em": agora(), "demanda": demanda_id, "job": job,
             "agente": agente, "evento": evento, "resumo": resumo[:400]}
    caminho = dir_demanda(demanda_id) / "eventos.jsonl"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(linha, ensure_ascii=False) + "\n")


def eventos(demanda_id: str) -> list:
    caminho = dir_demanda(demanda_id) / "eventos.jsonl"
    if not caminho.is_file():
        return []
    saida = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            try:
                saida.append(json.loads(linha))
            except json.JSONDecodeError:
                pass
    return saida


# --------------------------------------------------------------- demanda

def novo_id() -> str:
    hoje = datetime.now().strftime("%Y%m%d")
    dir_demandas().mkdir(parents=True, exist_ok=True)
    usados = [d.name for d in dir_demandas().iterdir()
              if d.is_dir() and d.name.startswith(f"DEM-{hoje}-")]
    return f"DEM-{hoje}-{len(usados) + 1:03d}"


def caminho_demanda(demanda_id: str) -> pathlib.Path:
    return dir_demanda(demanda_id) / "demanda.json"


def carregar(demanda_id: str) -> dict:
    caminho = caminho_demanda(demanda_id)
    if not caminho.is_file():
        raise ErroDeEstado(f"demanda '{demanda_id}' não existe em {dir_demandas()}")
    return ler_json(caminho)


def salvar(demanda: dict) -> None:
    demanda["atualizada_em"] = agora()
    erros = validar(demanda, "demanda")
    if erros:
        raise ErroDeEstado("demanda inválida: " + "; ".join(erros))
    _travar_pedido_original(demanda)
    gravar_json(caminho_demanda(demanda["id"]), demanda)


def _travar_pedido_original(demanda: dict) -> None:
    """`descricao` é o pedido do gestor, palavra por palavra, e não se reescreve.

    Resumo substituindo o original é exatamente como requisito desaparece entre a
    demanda e o briefing. Mudança do gestor entra como alteração datada, ao lado
    do original — nunca por cima dele.
    """
    caminho = caminho_demanda(demanda["id"])
    if not caminho.is_file():
        return
    anterior = ler_json(caminho).get("descricao")
    if anterior is not None and anterior != demanda.get("descricao"):
        raise ErroDeEstado(
            "o pedido original é imutável. Registre o que mudou com "
            f"'demanda.py alteracao {demanda['id']} --texto \"...\"' — o original fica.")


def listar() -> list:
    if not dir_demandas().is_dir():
        return []
    saida = []
    for d in sorted(dir_demandas().iterdir(), reverse=True):
        caminho = d / "demanda.json"
        if caminho.is_file():
            try:
                saida.append(ler_json(caminho))
            except json.JSONDecodeError:
                pass
    return saida


def transitar(demanda: dict, novo: str, *, motivo: str = "") -> dict:
    atual = demanda["status"]
    if novo == atual:
        return demanda
    if novo not in TRANSICOES.get(atual, set()):
        raise ErroDeEstado(
            f"transição recusada: {atual} -> {novo}. "
            f"De '{atual}' só se vai para: {', '.join(sorted(TRANSICOES[atual])) or '(nenhum estado)'}"
        )
    demanda["status"] = novo
    registrar_evento(demanda["id"], f"DEMANDA_{novo}", resumo=motivo)
    return demanda


# --------------------------------------------------------------- jobs

def proximo_job_id(demanda: dict) -> str:
    return f"JOB-{len(demanda.get('jobs', [])) + 1:03d}"


def proximo_requisito_id(demanda: dict) -> str:
    return f"REQ-{len(demanda.get('requisitos', [])) + 1:03d}"


def proxima_alteracao_id(demanda: dict) -> str:
    return f"ALT-{len(demanda.get('alteracoes', [])) + 1:03d}"


def achar_requisito(demanda: dict, req_id: str) -> dict:
    for r in demanda.get("requisitos", []):
        if r["id"] == req_id:
            return r
    raise ErroDeEstado(f"requisito '{req_id}' não existe na demanda {demanda['id']}")


def achar_job(demanda: dict, job_id: str) -> dict:
    for j in demanda.get("jobs", []):
        if j["id"] == job_id:
            return j
    raise ErroDeEstado(f"job '{job_id}' não existe na demanda {demanda['id']}")


def elegiveis(demanda: dict) -> list:
    """Jobs PENDENTE cujas dependências já estão CONCLUIDO.

    É o grafo funcionando: quem decide as arestas é o Diretor, quem calcula o
    que pode rodar agora é o código.
    """
    por_id = {j["id"]: j for j in demanda.get("jobs", [])}
    prontos = []
    for j in demanda.get("jobs", []):
        if j["status"] != "PENDENTE":
            continue
        deps = j.get("dependencias") or []
        if all(por_id.get(d, {}).get("status") == "CONCLUIDO" for d in deps):
            prontos.append(j)
    return prontos


def bloqueados_por_dependencia(demanda: dict) -> list:
    por_id = {j["id"]: j for j in demanda.get("jobs", [])}
    saida = []
    for j in demanda.get("jobs", []):
        if j["status"] != "PENDENTE":
            continue
        travas = [d for d in (j.get("dependencias") or [])
                  if por_id.get(d, {}).get("status") != "CONCLUIDO"]
        if travas:
            saida.append((j, travas))
    return saida


def validar_dependencias(demanda: dict, deps: list, job_id: str) -> None:
    ids = {j["id"] for j in demanda.get("jobs", [])}
    for d in deps:
        if d not in ids:
            raise ErroDeEstado(f"dependência '{d}' não existe nesta demanda")
        if d == job_id:
            raise ErroDeEstado("um job não pode depender de si mesmo")
    # ciclo simples: a dependência não pode depender de volta deste job
    por_id = {j["id"]: j for j in demanda.get("jobs", [])}
    vistos, pilha = set(), list(deps)
    while pilha:
        atual = pilha.pop()
        if atual == job_id:
            raise ErroDeEstado("dependência circular detectada")
        if atual in vistos:
            continue
        vistos.add(atual)
        pilha.extend(por_id.get(atual, {}).get("dependencias") or [])
