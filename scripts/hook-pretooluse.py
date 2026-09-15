#!/usr/bin/env python3
"""Hook PreToolUse do Claude Code — fecha o contorno do portão de autonomia.

Sem ele, o portão (`engine/policy.py executar`) só protege quem passa por ele:
bastava rodar o comando cru pelo Bash. Um PreToolUse dispara **antes de qualquer
checagem de permissão**, em todo modo, e `permissionDecision: "deny"` barra a
ferramenta mesmo em bypassPermissions.

Fonte única: este arquivo NÃO tem regra de segurança própria. Ele chama
`policy.classificar_shell()`, que lê `agents/diretor-operacoes/policy.yaml`.
Regra nova entra lá e passa a valer aqui no mesmo instante.

Decisão, por classe:
  PROIBIDO          nega sempre, com ou sem aprovação
  REQUER_APROVACAO  nega e manda passar pelo portão, que sabe checar aprovação
  nenhuma regra      deixa passar — ver a nota sobre fail-closed abaixo

Sobre fail-closed: o portão trata ação DESCRITA desconhecida como
REQUER_APROVACAO. Aqui não dá para fazer o mesmo, porque `ls`, `git status` e
`pytest` também são desconhecidos, e negar tudo tornaria o Claude Code inútil —
o que foi vedado explicitamente. O hook barra o que a política reconhece como
perigoso; o portão barra tudo que ela não reconhece como seguro. As duas
superfícies se complementam e leem o mesmo arquivo.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys


def responder_deny(motivo: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": motivo,
    }}, ensure_ascii=False))
    sys.exit(0)


def liberar() -> None:
    sys.exit(0)


# O caminho do portão é sancionado: ele faz a própria checagem, incluindo
# aprovação. Precisa ser a invocação que ABRE o comando, não uma menção solta no
# meio de uma linha — senão bastaria prefixar um `echo policy.py executar`.
GATE = re.compile(
    r"""^\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*        # variáveis de ambiente à frente
        (?:/\S*/)?python3?(?:\s+-\S+)*\s+             # python / python3
        \S*policy\.py\s+executar\b""",
    re.X,
)


def main() -> None:
    try:
        entrada = json.load(sys.stdin)
    except Exception:
        liberar()                      # entrada ilegível: não é papel do hook travar a sessão

    if entrada.get("tool_name") != "Bash":
        liberar()
    comando = (entrada.get("tool_input") or {}).get("command") or ""
    if not comando.strip():
        liberar()

    if GATE.match(comando):
        liberar()                      # é o próprio portão; ele decide

    raiz = pathlib.Path(os.environ.get("SQUAD_NK_HOME")
                        or (pathlib.Path.home() / ".claude" / "squad-nk"))
    try:
        sys.path.insert(0, str(raiz / "agents" / "diretor-operacoes"))
        from engine import policy      # type: ignore
        veredito = policy.classificar_shell(comando)
    except Exception as exc:
        # Política ilegível é falha de configuração, não motivo para travar o
        # trabalho. Avisa no stderr (vai para a transcript) e libera.
        print(f"[squad-nk] política indisponível, comando liberado: {exc}", file=sys.stderr)
        liberar()

    if veredito is None:
        liberar()

    classe = veredito["classe"]
    if classe == "AUTONOMO":
        liberar()

    if classe == "PROIBIDO":
        responder_deny(
            f"BLOQUEADO pela política do Squad NK (regra: {veredito['regra']}).\n"
            f"{veredito['motivo']}\n"
            "Esta ação é PROIBIDA: não executa com aprovação nenhuma. "
            "Não tente uma variação do comando — explique ao gestor humano por que "
            "ela seria necessária e pare."
        )

    responder_deny(
        f"BLOQUEADO pela política do Squad NK (regra: {veredito['regra']}).\n"
        f"{veredito['motivo']}\n"
        f"Impacto: {veredito['impacto'] or 'não declarado'}\n"
        "Esta ação REQUER APROVAÇÃO HUMANA e não pode ser executada direto pelo Bash.\n"
        "Passe pelo portão, que registra a solicitação e checa se já existe aprovação:\n"
        "  python3 ~/.claude/squad-nk/agents/diretor-operacoes/engine/policy.py executar \\\n"
        "      --acao \"<o que você vai fazer, em português>\" --demanda <DEM-...> -- <o comando>"
    )


if __name__ == "__main__":
    main()
