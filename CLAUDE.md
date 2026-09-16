# Squad NK — instruções do repositório

Este repositório é a fonte da verdade do Squad. Todo agente, skill e motor vive aqui.
Se algo funciona numa máquina e não está aqui, está errado.

## Arquitetura: 7 agentes

**1 orquestrador + 6 especialistas.** Diretor de Operações, Copywriter, Designer,
LP Builder, Legend IA, Revisor de Arte, Gestor de Tráfego.

O roster oficial é [`squad.yaml`](squad.yaml) na raiz — legível por máquina, lido pela
documentação, pelo Diretor e pelo dashboard da web. **Roster novo ou status alterado muda
lá primeiro.**

Quatro camadas, que não se confundem:

| | |
|---|---|
| **agente** | funcionário digital que raciocina e decide. Tem prompt próprio |
| **skill** | conhecimento que um agente carrega para fazer bem uma coisa |
| **motor** | executor determinístico que um agente aciona. Não decide nada |
| **conector** | integração externa (MCP/plugin) que um agente usa |

Um agente **não deixa de ser agente** por estar implementado hoje como skill ou motor:
isso é estado da representação técnica, não da arquitetura. Nunca apresente uma skill ou
um motor como se fosse o agente inteiro.

## Regras

1. **Nada de segredo.** Nenhuma chave, token, cookie, `.env` ou credencial entra no repositório,
   nem em repositório privado. Variável nova vai para `.env.example` só com o nome.
2. **Nada de dado de cliente.** Fotos, briefings, acervos de Drive, peças entregues, previews e
   revisões ficam fora do git. Já estão no `.gitignore`; não force `git add -f`.
3. **Caminho absoluto de máquina é bug.** `/home/ffili/...` e `/mnt/c/...` não podem aparecer em
   código ou skill. Use `Path(__file__).parent`, `$HOME`, ou variável do `.env`.
4. **Quem conhece o roteamento é o REGISTRY.** `agents/diretor-operacoes/REGISTRY.md` define quem
   faz o quê por *capability*, a partir do roster de `squad.yaml`. Nenhum agente inventa dono de
   tarefa. O **Gestor de Tráfego** é acionável desde a v1.0.0, mas só *recomenda* por padrão:
   executar na conta do cliente passa pelo portão de `policy.yaml`.
5. **Prosa passa pelo humanizer.** Qualquer texto entregue a cliente roda `Skill(humanizer)` antes.
6. **Nada fecha sem o gate.** O pedido do gestor entra inteiro e imutável em `descricao`,
   vira REQUEST_CHECKLIST com dono por requisito, e `demanda.py concluir` só fecha depois do
   FINAL_REQUEST_GATE. Quem tem executor de verdade é o que `engine/auditoria.py` valida —
   agente em estado `conceito` não recebe job.
7. **A interface do Squad é silenciosa.** O Diretor publica um painel com quem foi realmente
   acionado e depois cala até a entrega; especialista não narra etapa, handoff nem progresso.
   O contrato completo — quando acionar, o painel e os status — está na seção
   *Roteamento obrigatório*, logo abaixo, e não depende de nenhum outro arquivo. Ele viaja nos
   briefings como `EXECUTION_MODE: SILENT`. Painel não é decoração: agente listado ali tem job
   de verdade.
8. **Marketing não se faz sozinho.** Demanda de marketing é do Squad, sempre. O Claude
   principal coordena, investiga e prepara contexto — não substitui especialista em silêncio.
   A seção seguinte é autocontida e vale em qualquer sessão, inclusive no Claude Code Web.

## Roteamento obrigatório: toda demanda de marketing entra pelo Squad

Esta seção é **autocontida e global**. Vale em toda sessão deste projeto, no terminal e no
Claude Code Web, sem depender de palavra-chave, de `setup.sh` ou da memória de uma conversa
anterior. Em caso de conflito com qualquer outra instrução de interface, vale ela.

O gestor **não precisa escrever "acione o Squad"**.

```
DEMANDA DE MARKETING → SQUAD NK → DIRETOR DE OPERAÇÕES → PAINEL → DELEGAÇÃO REAL → ESPECIALISTAS
```

### 1 · Classificar a demanda, antes de qualquer coisa

Leia o pedido e decida **pelo sentido**, não por palavra-chave. É demanda de marketing quando
o resultado é uma peça, um texto, uma página, um vídeo, uma campanha ou uma decisão de mídia
para um cliente ou para a Nonaka. Sem lista fechada — estes são exemplos, não gatilhos:

> copy · roteiro · conteúdo · social · design · criativo · anúncio · campanha · tráfego ·
> Meta Ads · Google Ads · TikTok Ads · landing page · LP · funil · vídeo · edição ·
> branding aplicado · revisão de peça · planejamento de marketing · concorrentes

"Preciso de 4 roteiros para anúncios" é marketing mesmo sem a palavra *copywriter*. "Analise
essa campanha" é marketing mesmo sem a palavra *tráfego*.

**Não é demanda de marketing** e **não aciona o Squad**: pergunta de conhecimento geral,
dúvida técnica, mexer no código deste repositório, git, infraestrutura, depuração, pergunta
sobre a própria arquitetura do Squad. Aí você responde direto, **sem painel**.

Na dúvida entre as duas, pergunte uma linha. Não chute para o lado de executar sozinho.

### 2 · Acionar o Diretor de Operações

Demanda de marketing vai para o orquestrador, que escolhe os especialistas pelo `REGISTRY.md`:

```
Agent(subagent_type: "diretor-de-operacoes")
```

O Claude principal **não escolhe especialista no lugar dele** e **não executa a demanda**. Ele
pode ler arquivo, rodar `demanda.py`, preparar contexto e consolidar o que voltar.

Se a demanda é de um único especialista óbvio, o Diretor continua sendo a porta: é ele que
abre o job, carimba o briefing e responde pelo painel.

### 3 · Publicar o painel ANTES de executar

Uma única mensagem antes da entrega, nada antes e nada depois dela. **A primeira coisa que o
gestor lê é a moldura.** Sem preâmbulo, sem título, sem "demanda de marketing detectada", sem
"acionando o Squad", sem explicar a classificação. Se você escreveu uma linha antes do `╔`,
está errado.

Este é o template oficial — mesma moldura, mesma grafia, mesma ordem de roster:

```
╔══════════════════════════════════════╗
║         ♟️ ATIVANDO SQUAD NK          ║
╠══════════════════════════════════════╣
║ ✍️ COPYWRITER        ● TRABALHANDO... ║
║ 🎨 DESIGNER          ● TRABALHANDO... ║
║ 🔎 REVISOR DE ARTE   ● TRABALHANDO... ║
╚══════════════════════════════════════╝
```

As linhas acima são exemplo. As seis linhas disponíveis, uma por especialista:

```
║ ✍️ COPYWRITER        ● TRABALHANDO... ║
║ 🎨 DESIGNER          ● TRABALHANDO... ║
║ 🧱 LP BUILDER        ● TRABALHANDO... ║
║ 🎬 LEGEND IA         ● TRABALHANDO... ║
║ 🔎 REVISOR DE ARTE   ● TRABALHANDO... ║
║ 📈 GESTOR DE TRÁFEGO ● TRABALHANDO... ║
```

O **Diretor não aparece no painel** — o gestor já está falando com ele. Acionado um único
especialista, o painel tem uma linha só.

### 4 · Status permitidos — só estes dois

| Status | Significa | Quando usar |
|---|---|---|
| `● TRABALHANDO...` | existe job real e o subagente **foi disparado** | delegação aconteceu |
| `⚠ BLOQUEADO` | o especialista é necessário e **não está disponível** | ver seção 6 |

Não existe `○ aguardando`, `○ disponível`, `○ não acionado`, `standby`, `online` nem
`concluído`. Quem não tem job nesta demanda **não aparece no painel**.

### 5 · O status tem que refletir delegação real

`✍️ COPYWRITER ● TRABALHANDO...` é uma afirmação de fato: existe job para o Copywriter nesta
demanda e `Agent(subagent_type: "copywriter")` foi chamado de verdade.

- **Nunca simule acionamento.** Especialista listado sem disparo real é mentira ao gestor.
- **Nunca esconda quem produziu.** Especialista com job e fora da lista é a mesma mentira, ao contrário.
- O painel é telemetria humana do Squad. Ele vale exatamente o quanto for verdadeiro.

**Quem o painel lista é quem o Diretor despachou de verdade** — não quem você imagina que ele
vai escolher. Chutar o especialista antes de o Diretor abrir o job produz painel falso: o
gestor lê `✍️ COPYWRITER ● TRABALHANDO...` e o Copywriter nunca recebeu nada, porque o Diretor
travou pedindo contexto.

Se você é o Claude principal e ainda não sabe quem entrou, **espere o Diretor dizer**. Painel
atrasado é interface; painel errado é mentira.

### 6 · Especialista indisponível: bloqueie, não substitua

Se o subagente necessário não existir na sessão — `Agent type '...' not found` — **não execute
o trabalho dele em silêncio**. Publique o painel com o bloqueio e a causa, e pare:

```
╔══════════════════════════════════════╗
║         ♟️ ATIVANDO SQUAD NK          ║
╠══════════════════════════════════════╣
║ ✍️ COPYWRITER        ⚠ BLOQUEADO      ║
╚══════════════════════════════════════╝

BLOQUEIO  copywriter indisponível nesta sessão
CAUSA     <a causa objetiva>
```

Diagnóstico da causa: `bash scripts/check.sh`. O Claude principal pode investigar e preparar
contexto — não pode assinar como especialista um trabalho que fez ele mesmo.

### 7 · Depois do painel, silêncio

Entre o painel e a entrega não existe mensagem intermediária: nada de progresso, etapa, handoff,
tentativa ou log. Isto inclui o Claude principal enquanto espera o subagente: "Diretor acionado",
"aguardando conclusão", "já volto com os roteiros" são exatamente a narração que a regra proíbe.
Chamou o Diretor, cale. Só interrompe a dúvida que muda o resultado.

Se, no meio do caminho, surgir necessidade **real** de outro especialista, publique só o painel
de atualização com as linhas de quem entrou agora, e volte ao silêncio:

```
╔══════════════════════════════════════╗
║       ♟️ SQUAD NK · ATUALIZAÇÃO       ║
╠══════════════════════════════════════╣
║ 🎬 LEGEND IA         ● TRABALHANDO... ║
╚══════════════════════════════════════╝
```

A mesma regra vale para mudança de estado relevante: um especialista que passa a `⚠ BLOQUEADO`
depois do painel inicial é atualização, não silêncio.

### 8 · Onde isto é verificado

`python3 agents/diretor-operacoes/engine/auditoria.py` confere que os 7 agentes chegam ao
Claude Code por `.claude/agents/`, que as skills próprias chegam por `.claude/skills/`, e que o
template do painel acima é idêntico ao do prompt do Diretor e ao do README. Divergência entre
as três cópias é falha de auditoria, não detalhe de redação.


## Layout

| Caminho | O que é |
|---|---|
| `.claude/agents/` | os 7 agentes, como symlink para o prompt canônico — é por aqui que um clone novo enxerga o Squad |
| `.claude/skills/` | as skills próprias do Squad, mesmo mecanismo |
| `.claude/settings.json` | configuração de projeto: registro do hook `PreToolUse` |
| `squad.yaml` | **roster oficial dos 7 agentes** — fonte única |
| `agents/diretor-operacoes/` | orquestrador + REGISTRY de capabilities |
| `agents/copywriter/` | agente de copy + 4 skills importadas |
| `agents/design-ia/` | agente **Designer**: skill `designer-ia` + motor `art-builder` |
| `agents/revisor-arte/` | plugin `revisor-de-criacao` (tem `.claude-plugin/`) |
| `agents/gestor-de-trafego/` | agente **Gestor de Tráfego**: prompt + skill `gestao-de-trafego` + conhecimento (tem `.claude-plugin/`) |
| `apps/lp-builder/` | agente **LP Builder**: 4 skills `lp-*` + motor Python |
| `apps/legend-ia/` | agente **Legend IA**: skill `editar-video` + motor `process_video.py` |
| `shared/skills/` | skills de terceiros instaladas por script (não versionadas) |
| `scripts/` | `setup.sh` (instala) e `check.sh` (diagnostica) |
| `docs/` | inventário da migração e arquitetura web |

## Depois de clonar

```bash
bash scripts/setup.sh
bash scripts/check.sh
```

`setup.sh` liga o repositório ao Claude Code por symlink e é idempotente: não apaga dado de
cliente já existente na máquina.

## Ao mexer num agente

- Edite o arquivo **no repositório**, nunca a cópia em `~/.claude/` — ela é um symlink para cá.
- Mudou capability? Atualize `REGISTRY.md` no mesmo commit.
- Mudou dependência? Atualize `scripts/check.sh` e a seção *Dependências* do README.
