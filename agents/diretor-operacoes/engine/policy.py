"""Portão de autonomia. Classifica uma ação e decide se ela pode rodar.

Isto NÃO é orientação em prosa. É o ponto por onde o Diretor executa qualquer
ação de efeito: se a classe for REQUER_APROVACAO sem aprovação registrada, o
comando não roda; se for PROIBIDO, não roda com aprovação nenhuma.

    policy.py classificar "pausar campanha do cliente X"
    policy.py executar --demanda DEM-... --acao "publicar preview" -- <comando>

Limite honesto: isto fecha o caminho que passa por aqui. Não impede que alguém
rode o comando cru fora do portão — para isso seria preciso um hook do Claude
Code, que está documentado como próximo passo no README deste diretório.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import unicodedata

import yaml

if __package__ in (None, ""):          # permite rodar por caminho direto
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from engine import modelo          # type: ignore
else:
    from . import modelo

ORDEM = ["PROIBIDO", "REQUER_APROVACAO", "AUTONOMO"]   # da mais restritiva à mais livre


def caminho_policy():
    return modelo.REPO / "agents" / "diretor-operacoes" / "policy.yaml"


def carregar() -> dict:
    return yaml.safe_load(caminho_policy().read_text(encoding="utf-8")) or {}


def normalizar(texto: str) -> str:
    """Sem acento, minúsculo, espaço único. Os padrões são escritos assim."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.lower()).strip()


def classificar(acao: str) -> dict:
    """Devolve classe, regra que casou e motivo. Vence a mais restritiva."""
    pol = carregar()
    alvo = normalizar(acao)
    for classe in ORDEM:
        bloco = (pol.get("classes") or {}).get(classe) or {}
        for regra in bloco.get("regras", []):
            for padrao in regra.get("padroes", []):
                if re.search(padrao, alvo):
                    return {"classe": classe, "regra": regra["id"],
                            "motivo": regra.get("motivo", ""),
                            "impacto": regra.get("impacto", ""),
                            "padrao": padrao, "acao": acao}
    return {"classe": pol.get("padrao_desconhecido", "REQUER_APROVACAO"),
            "regra": "(nenhuma regra casou)",
            "motivo": "Ação não reconhecida pela política. Por segurança não é liberada por omissão.",
            "impacto": "desconhecido", "padrao": None, "acao": acao}


# --------------------------------------------- o que é AÇÃO e o que é CONTEÚDO
#
# O portão classifica uma AÇÃO DESCRITA em português: ali a palavra é a ação, e
# quem escreve "faturar o cliente" está dizendo o que pretende fazer.
#
# O hook classifica um COMANDO DE SHELL, e ali a mesma palavra quase sempre não
# é ação nenhuma — é carga. O comando que grava um briefing com um depoimento
# ("trocaram sem cobrar") não movimenta um centavo; ele escreve um arquivo. A
# primeira versão desta política não fazia essa distinção e barrou, no mesmo dia,
# quatro coisas inofensivas: um briefing de cliente, o resumo de um job, uma copy
# de landing page que citava faixa de valor, e um comentário de código que
# explicava justamente este bug.
#
# Falso positivo aqui não é chateação: é o hook ensinando que a trava é ruído, e
# trava que vira ruído é trava que alguém desliga.
#
# A correção NÃO é afrouxar o padrão. É olhar o lugar certo do comando. Um
# comando de shell tem esqueleto — programa, subcomando, opções, alvo — e tem
# carga: corpo de heredoc, comentário, valor de campo de prosa. O esqueleto
# executa. A carga é dado.
#
# E a carga não é ignorada: antes de sair, ela passa por MARCAS_DE_EXECUCAO. Um
# heredoc que traz `requests.post` ou `curl` não é prosa, é programa, e volta
# inteiro para o esqueleto. Prosa de cliente não contém `subprocess`.

MARCAS_DE_EXECUCAO = (
    r"\b(requests|httpx)\s*\.\s*(post|put|patch|delete|request)\b",
    r"\burllib\b|\bhttp\.client\b|\bsocket\b",
    r"\b(curl|wget|http|xh)\b",
    r"\bsubprocess\b|\bos\.system\b|\bpopen\b|\bexec\b|\beval\(",
    r"graph\.facebook\.com|business-api\.tiktok|googleads|google-ads|ads\.google",
    r"\bfacebook_business\b|\bfacebookads\b|\bgoogle\.ads\b",
    r"\brm\s+-[a-z]*r|\bgit\s+push\b|\bmkfs\b|\bdd\s+if=",
)

# Campos cujo VALOR é prosa por contrato: o que vai neles é texto de trabalho,
# nunca o que o comando faz. `--acao` fica deliberadamente de fora — ele é a
# ação descrita que o portão precisa classificar.
CAMPOS_DE_CONTEUDO_PADRAO = (
    "--resumo", "--texto", "--descricao", "--pedido", "--observacao", "--pergunta",
    "--corrigir", "--evidencia", "--motivo", "--plano", "--objetivo", "--contexto",
    "--entrada", "--saida", "--criterio", "--restricao", "--decisao", "--hipotese",
    "--corte", "--busca", "--titulo", "--proximo", "--pendencia", "--caption", "-m",
)


def _config_shell() -> dict:
    return (carregar().get("shell") or {})


def _parece_executavel(trecho: str) -> bool:
    return any(re.search(p, trecho, re.I) for p in
               _config_shell().get("marcas_de_execucao") or MARCAS_DE_EXECUCAO)


def _spans_heredoc(comando: str) -> list:
    """Onde começa e termina o corpo de cada heredoc do comando."""
    spans = []
    for m in re.finditer(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", comando):
        rotulo = m.group(2)
        inicio = comando.find("\n", m.end())
        if inicio == -1:
            continue
        fim = re.search(rf"^\s*{re.escape(rotulo)}\s*$", comando[inicio:], re.M)
        spans.append((inicio, inicio + fim.start() if fim else len(comando)))
    return spans


def _spans_campo_de_conteudo(comando: str) -> list:
    """Onde está o VALOR entre aspas de um campo declarado como prosa."""
    campos = _config_shell().get("campos_de_conteudo") or list(CAMPOS_DE_CONTEUDO_PADRAO)
    alternativa = "|".join(re.escape(c) for c in campos)
    spans = []
    for m in re.finditer(rf"(?:{alternativa})[=\s]+('([^']*)'|\"([^\"]*)\")", comando):
        spans.append((m.start(1), m.end(1)))
    return spans


def _spans_comentario(comando: str) -> list:
    """`#` até o fim da linha, quando abre um token e não está dentro de aspas.

    Na dúvida, NÃO corta: linha com número ímpar de aspas fica inteira. Cortar
    demais abre buraco; cortar de menos só devolve o falso positivo, e o falso
    positivo a gente vê.
    """
    spans, pos = [], 0
    for linha in comando.split("\n"):
        if linha.count("'") % 2 == 0 and linha.count('"') % 2 == 0:
            m = re.search(r"(?:^|\s)#", linha)
            if m:
                spans.append((pos + m.start(), pos + len(linha)))
        pos += len(linha) + 1
    return spans


def esqueleto_shell(comando: str) -> str:
    """O comando sem a carga: só o que executa.

    Cada região de carga só sai se ela mesma não parecer programa. E o que ficou
    por parecer programa fica INTEIRO: cortar um comentário de dentro de um
    heredoc que foi mantido apaga justamente a linha que declara o que o script
    vai fazer.
    """
    heredocs = _spans_heredoc(comando)
    mantidos = [(i, f) for i, f in heredocs if _parece_executavel(comando[i:f])]

    def dentro_de_mantido(ini, fim):
        return any(i <= ini and fim <= f for i, f in mantidos)

    cortes = []
    for ini, fim in (heredocs + _spans_campo_de_conteudo(comando)
                     + _spans_comentario(comando)):
        if dentro_de_mantido(ini, fim):
            continue
        if not _parece_executavel(comando[ini:fim]):
            cortes.append((ini, fim))
    if not cortes:
        return comando
    mantido, cursor = [], 0
    for ini, fim in sorted(cortes):
        if ini > cursor:
            mantido.append(comando[cursor:ini])
        cursor = max(cursor, fim)
    mantido.append(comando[cursor:])
    return " ".join(mantido)


def classificar_shell(comando: str) -> dict | None:
    """Classificação para um COMANDO DE SHELL cru, usada pelo hook.

    Duas diferenças deliberadas em relação a `classificar`:

    1. Classifica o ESQUELETO do comando, não o texto inteiro — ver a nota acima.
    2. Comando que não casa com nenhuma regra devolve None, e o hook deixa
       passar. O fail-closed do portão continua valendo para AÇÃO DESCRITA em
       português; aplicá-lo a todo comando de shell tornaria o Claude Code
       inutilizável, porque `ls`, `git status` e `pytest` também são
       "desconhecidos".

    Em uma frase: o hook barra o que a política reconhece como perigoso; o portão
    barra tudo que ela não reconhece como seguro.
    """
    v = classificar(esqueleto_shell(comando))
    if v.get("padrao"):
        v["comando"] = comando
        return v
    return None


# --------------------------------------------------------------- aprovações

def aprovacao_valida(demanda: dict, acao: str) -> dict | None:
    """Aprovação CONCEDIDA para esta ação exata, ainda não consumida."""
    alvo = normalizar(acao)
    for ap in demanda.get("aprovacoes", []):
        if ap.get("status") == "CONCEDIDA" and normalizar(ap.get("acao", "")) == alvo \
                and not ap.get("consumida_em"):
            return ap
    return None


def solicitar(demanda: dict, acao: str, veredito: dict, *, job: str | None = None) -> dict:
    ap = {
        "id": f"APR-{len(demanda.get('aprovacoes', [])) + 1:03d}",
        "acao": acao, "job": job, "classe": veredito["classe"],
        "motivo": veredito["motivo"], "impacto": veredito["impacto"],
        "regra": veredito["regra"], "status": "PENDENTE",
        "solicitada_em": modelo.agora(), "decidida_em": None,
        "decidida_por": None, "observacao": None, "consumida_em": None,
    }
    demanda.setdefault("aprovacoes", []).append(ap)
    modelo.registrar_evento(demanda["id"], "APROVACAO_SOLICITADA", job=job,
                            resumo=f"{ap['id']}: {acao}")
    return ap


def painel_aprovacao(ap: dict) -> str:
    return (
        "\n┌─ APROVAÇÃO HUMANA NECESSÁRIA ─────────────────────────────\n"
        f"│ SOLICITAÇÃO   {ap['id']}\n"
        f"│ AÇÃO          {ap['acao']}\n"
        f"│ CLASSE        {ap['classe']}  (regra: {ap['regra']})\n"
        f"│ MOTIVO        {ap['motivo']}\n"
        f"│ IMPACTO       {ap['impacto'] or 'não declarado'}\n"
        f"│ O QUE MUDA    {ap.get('alvo') or 'ver o comando abaixo'}\n"
        "│\n"
        "│ Nada foi executado. Silêncio não é aprovação.\n"
        "│ Para autorizar:\n"
        f"│   demanda.py aprovacao conceder <DEMANDA> {ap['id']} --por \"<quem>\"\n"
        "└───────────────────────────────────────────────────────────\n"
    )


# --------------------------------------------------------------- CLI

def cmd_classificar(a) -> int:
    v = classificar(a.acao)
    print(f"  AÇÃO    {v['acao']}")
    print(f"  CLASSE  {v['classe']}")
    print(f"  REGRA   {v['regra']}")
    if v["motivo"]:
        print(f"  MOTIVO  {v['motivo']}")
    if v["impacto"]:
        print(f"  IMPACTO {v['impacto']}")
    return 0 if v["classe"] == "AUTONOMO" else (2 if v["classe"] == "REQUER_APROVACAO" else 3)


def cmd_executar(a) -> int:
    """Executa um comando só se a política permitir. É aqui que a trava morde."""
    if not a.comando:
        print("erro: informe o comando depois de --", file=sys.stderr)
        return 1
    v = classificar(a.acao)

    if v["classe"] == "PROIBIDO":
        if a.demanda:
            d = modelo.carregar(a.demanda)
            modelo.registrar_evento(a.demanda, "ACAO_PROIBIDA_BLOQUEADA",
                                    job=a.job, resumo=f"{a.acao} · regra {v['regra']}")
        print("\n┌─ AÇÃO PROIBIDA ───────────────────────────────────────────")
        print(f"│ AÇÃO    {v['acao']}")
        print(f"│ REGRA   {v['regra']}")
        print(f"│ MOTIVO  {v['motivo']}")
        print("│\n│ Não executa com aprovação nenhuma. Nada foi rodado.")
        print("└───────────────────────────────────────────────────────────\n")
        return 3

    if v["classe"] == "REQUER_APROVACAO":
        if not a.demanda:
            print("erro: ação que requer aprovação precisa de --demanda para registrar a solicitação",
                  file=sys.stderr)
            return 1
        d = modelo.carregar(a.demanda)
        ap = aprovacao_valida(d, a.acao)
        if ap is None:
            nova = solicitar(d, a.acao, v, job=a.job)
            nova["alvo"] = " ".join(a.comando)
            modelo.transitar(d, "AGUARDANDO_APROVACAO",
                             motivo=f"{nova['id']}: {a.acao}") if d["status"] in \
                modelo.TRANSICOES and "AGUARDANDO_APROVACAO" in modelo.TRANSICOES[d["status"]] else None
            modelo.salvar(d)
            print(painel_aprovacao(nova))
            return 2
        # aprovação existe: consome, registra e segue
        ap["consumida_em"] = modelo.agora()
        modelo.salvar(d)
        modelo.registrar_evento(a.demanda, "ACAO_EXECUTADA_COM_APROVACAO",
                                job=a.job, resumo=f"{ap['id']}: {a.acao}")
        print(f"  aprovação {ap['id']} encontrada e consumida · executando")

    proc = subprocess.run(a.comando)
    if a.demanda:
        modelo.registrar_evento(a.demanda, "ACAO_EXECUTADA", job=a.job,
                                resumo=f"[{v['classe']}] {a.acao} · saída {proc.returncode}")
    return proc.returncode


def cmd_listar(a) -> int:
    pol = carregar()
    print(f"  política v{pol.get('versao')} · ação desconhecida -> {pol.get('padrao_desconhecido')}\n")
    for classe in ORDEM:
        bloco = (pol.get("classes") or {}).get(classe) or {}
        print(f"  {classe}")
        for regra in bloco.get("regras", []):
            print(f"    · {regra['id']:<26} {len(regra['padroes'])} padrão(ões)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="policy", description="Portão de autonomia do Squad NK")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classificar", help="diz a classe de uma ação")
    c.add_argument("acao"); c.set_defaults(fn=cmd_classificar)

    e = sub.add_parser("executar", help="executa o comando só se a política permitir")
    e.add_argument("--acao", required=True, help="descrição da ação, em português")
    e.add_argument("--demanda"); e.add_argument("--job")
    e.add_argument("comando", nargs=argparse.REMAINDER)
    e.set_defaults(fn=cmd_executar)

    sub.add_parser("listar", help="mostra a política").set_defaults(fn=cmd_listar)

    a = p.parse_args(argv)
    if getattr(a, "comando", None) and a.comando and a.comando[0] == "--":
        a.comando = a.comando[1:]
    try:
        return a.fn(a)
    except modelo.ErroDeEstado as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
