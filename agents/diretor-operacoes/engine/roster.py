"""Leitor do roster oficial — `squad.yaml` na raiz do repositório.

Por que um leitor próprio, e não PyYAML: este motor roda com o python do
sistema, sem venv e sem dependência externa, igual aos motores dos
especialistas. O mesmo princípio do validador escrito à mão em `modelo.py`.
O formato de `squad.yaml` é nosso e é simples — escalar, lista inline, lista
em bloco e bloco dobrado (`>-`). Nada além disso entra no arquivo.

O roster é a fonte única: quem existe, quem tem implementação e como se aciona
cada um. Nada aqui decide roteamento — isso é do Diretor, com o `REGISTRY.md`.
"""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
ARQUIVO = REPO / "squad.yaml"

# Campos que este leitor conhece. Chave nova no squad.yaml não quebra nada:
# vira texto ou lista, conforme a forma que estiver escrita.
LISTAS = ("capabilities", "skills", "motores", "conectores", "ferramentas_web")


def _sem_comentario(texto: str) -> str:
    """Remove comentário de fim de linha. Aspas protegem o `#`."""
    fora, aspas = [], ""
    for i, ch in enumerate(texto):
        if ch in "\"'":
            aspas = "" if aspas == ch else (aspas or ch)
        if ch == "#" and not aspas and (i == 0 or texto[i - 1] in " \t"):
            break
        fora.append(ch)
    return "".join(fora).strip()


def _escalar(bruto: str):
    v = bruto.strip()
    if v in ("null", "~", ""):
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
    return v


def _indent(linha: str) -> int:
    return len(linha) - len(linha.lstrip(" "))


def carregar(caminho: pathlib.Path | None = None) -> dict:
    """Devolve {'versao':…, 'estrutura':…, 'agentes':[{…}]} a partir do squad.yaml."""
    caminho = caminho or ARQUIVO
    linhas = caminho.read_text(encoding="utf-8").split("\n")
    dados: dict = {"agentes": []}
    atual: dict | None = None
    i = 0
    while i < len(linhas):
        crua = linhas[i]
        i += 1
        linha = _sem_comentario(crua)
        if not linha:
            continue
        ind = _indent(crua)

        if ind == 0 and linha.endswith(":") and linha[:-1] == "agentes":
            atual = None
            continue
        if ind == 0 and ":" in linha:                       # escalar de topo
            chave, _, valor = linha.partition(":")
            dados[chave.strip()] = _escalar(valor)
            continue

        if ind == 2 and linha.startswith("- "):             # novo agente
            atual = {}
            dados["agentes"].append(atual)
            linha, ind = linha[2:], 4                       # "- id: x" tem par na própria linha

        if atual is None or ":" not in linha:
            continue

        chave, _, valor = linha.partition(":")
        chave, valor = chave.strip(), valor.strip()

        if valor in (">-", ">", "|", "|-", ">+"):           # bloco dobrado
            corpo = []
            while i < len(linhas) and (not linhas[i].strip() or _indent(linhas[i]) > ind):
                corpo.append(linhas[i].strip())
                i += 1
            atual[chave] = " ".join(x for x in corpo if x)
        elif valor == "":                                   # lista em bloco
            itens = []
            while i < len(linhas) and _indent(linhas[i]) > ind and _sem_comentario(linhas[i]).startswith("- "):
                itens.append(_escalar(_sem_comentario(linhas[i])[2:]))
                i += 1
            atual[chave] = itens
        else:
            v = _escalar(valor)
            atual[chave] = ([v] if v and chave in LISTAS and not isinstance(v, list) else
                            (v if v is not None else ([] if chave in LISTAS else None)))
    for a in dados["agentes"]:
        for c in LISTAS:
            a.setdefault(c, [])
    return dados


# ------------------------------------------------------------ consultas

def agentes(caminho: pathlib.Path | None = None) -> list:
    return carregar(caminho)["agentes"]


def por_id(agente_id: str, caminho: pathlib.Path | None = None) -> dict | None:
    return next((a for a in agentes(caminho) if a.get("id") == agente_id), None)


def especialistas(caminho: pathlib.Path | None = None) -> list:
    return [a for a in agentes(caminho) if a.get("papel") == "especialista"]


def formais(caminho: pathlib.Path | None = None) -> list:
    """Quem tem prompt próprio e pode ser acionado de fato."""
    return [a for a in agentes(caminho) if a.get("agente") == "formal"]


def conceitos(caminho: pathlib.Path | None = None) -> list:
    """Papel definido, implementação ausente. Não se aciona, não se simula."""
    return [a for a in agentes(caminho) if a.get("agente") == "conceito"]


def acionaveis(caminho: pathlib.Path | None = None) -> list:
    """`subagent_type` dos especialistas com implementação — o que vira job."""
    return [a["subagent_type"] for a in formais(caminho)
            if a.get("papel") == "especialista" and a.get("subagent_type")]


def por_subagent_type(nome: str, caminho: pathlib.Path | None = None) -> dict | None:
    return next((a for a in agentes(caminho) if a.get("subagent_type") == nome), None)


def dono_da_capability(capability: str, caminho: pathlib.Path | None = None) -> dict | None:
    """Qual agente atende a capability. Prefixo casa: `copywriting` acha `copywriting.script`."""
    for a in agentes(caminho):
        for c in a.get("capabilities") or []:
            if c == capability or c.startswith(capability + "."):
                return a
    return None
