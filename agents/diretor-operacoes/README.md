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

**Limite honesto:** o portão fecha o caminho que passa por ele. Não impede que alguém rode o
comando cru por fora. Fechar isso de vez exigiria um hook `PreToolUse` no Claude Code, que
interceptaria toda chamada de Bash da sessão — decisão do gestor, não implementada aqui.

## Teto de tentativas

3 por job, em `modelo.MAX_TENTATIVAS`. Ao bater, o job é bloqueado e o Diretor precisa corrigir o
briefing conscientemente ou escalar. Mesmo princípio do `job.py` do Designer: o limite vive em
código, não na boa vontade do prompt.
