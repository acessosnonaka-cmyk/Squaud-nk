# Diretor de Operações — camada operacional

O Diretor continua sendo **agente**: ele interpreta, planeja, decide o grafo de jobs e delega.
Este diretório contém só o que não pode depender de memória de conversa.

| Arquivo | O que faz |
|---|---|
| `agents/diretor-de-operacoes.md` | o prompt — quem ele é, como roteia, como usa o resto |
| `REGISTRY.md` | roteamento por capability |
| `policy.yaml` | **política de autonomia** — AUTONOMO / REQUER_APROVACAO / PROIBIDO |
| `engine/modelo.py` | estados, transições, validação, event log, grafo de dependências |
| `engine/policy.py` | o **portão**: classifica a ação e só então executa (ou não) |
| `engine/demanda.py` | CLI operacional: demandas, jobs, briefings, aprovações, feedback, retomada |
| `engine/auditoria.py` | confere o roster em duas camadas: repositório e instalação desta máquina |
| `engine/entrega_pdf.py` | markdown da entrega -> PDF do cliente. Recusa gravar dentro do git |
| `schemas/*.json` | os quatro contratos: demanda, job, briefing, retorno |

## Onde ficam os dados

`$SQUAD_DATA_HOME/diretor/` — padrão `~/.squad-nk/diretor/`. **Fora do git**, como o dado dos
outros agentes. É a mesma raiz que a aplicação web usa, então demanda aberta no Claude Code e
demanda aberta pela web futura compartilham estado sem migração.

```
diretor/
  demandas/<DEM-...>/demanda.json     estado completo
                     eventos.jsonl    log append-only
                     handoffs/        briefings e retornos, um par por job
  clientes/<slug>.md                  memória estável do cliente
```

## O ciclo, em comandos

```bash
E=agents/diretor-operacoes/engine

demanda.py nova --cliente x --titulo "..." --descricao "..."   # -> DEM-AAAAMMDD-NNN
demanda.py planejar DEM-... --plano "..."
demanda.py job add DEM-... --agente copywriter --objetivo "..."
demanda.py job add DEM-... --agente designer --objetivo "..." --depende JOB-001
demanda.py briefing DEM-... JOB-001         # contrato para colar no Agent()
demanda.py job iniciar DEM-... JOB-001
demanda.py job concluir DEM-... JOB-001 --resumo "..." --artefato /caminho
demanda.py retomar DEM-...                  # onde parou e qual o próximo passo
```

## A trava

```bash
policy.py classificar "alterar o orçamento da campanha"
policy.py executar --acao "publicar o preview" --demanda DEM-... -- <comando>
```

Ação AUTONOMO roda. REQUER_APROVACAO **não roda**: abre a solicitação com ação, motivo, impacto e
o que muda, e espera `demanda.py aprovacao conceder`. PROIBIDO não roda com aprovação nenhuma.
Ação que a política não reconhece cai em REQUER_APROVACAO — não é liberada por omissão.

### O hook: fechando o contorno

`scripts/hook-pretooluse.py` é um hook `PreToolUse` do Claude Code que inspeciona todo comando
Bash **antes** de ele rodar. Um PreToolUse dispara antes de qualquer checagem de permissão, em
todo modo — `permissionDecision: "deny"` barra a ferramenta mesmo em `bypassPermissions`.

Registro em `~/.claude/settings.json`:

```json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
  {"type": "command",
   "command": "python3 \"$HOME/.claude/squad-nk/scripts/hook-pretooluse.py\"",
   "timeout": 15}]}]}}
```

**Fonte única:** o hook não tem regra própria. Chama `policy.classificar_shell()`, que lê o mesmo
`policy.yaml`. Regra nova entra lá e passa a valer nas duas superfícies.

**Dois fail-closed diferentes, de propósito:**

| Superfície | O que faz com o desconhecido |
|---|---|
| portão (`policy.py executar`) | ação **descrita** que não casa com nada → REQUER_APROVACAO |
| hook (comando de shell) | comando que não casa com nada → **passa** |

Aplicar o fail-closed do portão a todo comando de shell negaria `ls`, `git status` e `pytest` —
tornaria o Claude Code inútil. O hook barra o que a política reconhece como perigoso; o portão
barra tudo que ela não reconhece como seguro.

### Limitações do hook, medidas e não maquiadas

1. **Ele lê o texto do comando, não o que o comando faz.** Um script composto que *mencione* uma
   ação protegida é barrado mesmo sem executá-la — e, na outra direção, `bash script.sh` esconde o
   conteúdo do arquivo do olhar do hook. **Ele protege contra contorno acidental, não contra
   evasão deliberada.**
2. **Variável não é resolvida.** `rm -rf "$DIR"` é barrado porque o hook não sabe o que a variável
   contém. Conservador por escolha.
3. **Falha do hook libera o comando.** Timeout ou erro de execução em PreToolUse é não-bloqueante,
   por desenho do Claude Code. Política ilegível vira aviso no stderr e não trava a sessão.
4. **Só cobre a ferramenta `Bash`.** `Write` e `Edit` não passam por ele.
5. **Remoção recursiva** é liberada em área temporária (`/tmp`, `$TMPDIR`) e barrada fora dela.

## Teto de tentativas

3 por job, em `modelo.MAX_TENTATIVAS`. Ao bater, o job é bloqueado e o Diretor precisa corrigir o
briefing conscientemente ou escalar. Mesmo princípio do `job.py` do Designer: o limite vive em
código, não na boa vontade do prompt.
