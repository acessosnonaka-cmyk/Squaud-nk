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

## Duas camadas, que falham separado

O Squad tem uma camada de **controle** e uma de **runtime**. Elas quebram por motivos
diferentes e não se substituem.

| | **CAMADA A · CONTROLE** | **CAMADA B · RUNTIME** |
|---|---|---|
| O que é | quem existe, quem decide, quem faz o quê | o que executa bit |
| Onde mora | `CLAUDE.md`, `.claude/agents/`, `.claude/skills/`, `.claude/settings.json`, `squad.yaml`, REGISTRY | Playwright, Chromium, ffmpeg, Pillow, venvs, `humanizer` |
| Como chega | **só clonando o repositório** | `scripts/setup.sh` e instaladores |
| Sem ela | não existe Squad: nem painel, nem Diretor, nem delegação | existe Squad, e os motores visuais não rodam |

Tudo da camada A é **versionado e carregado sozinho**: `.claude/agents/` e
`.claude/skills/` são symlinks relativos para o arquivo canônico — um arquivo só, sem
cópia divergindo. Editar continua sendo no caminho canônico (`agents/…`, `apps/…`).

**Demanda textual não depende da camada B.** Diretor → Copywriter escrevendo roteiro roda
num container recém-clonado, sem Chromium e sem ffmpeg. Só o PDF final precisa de
Playwright, e só o Designer e o Legend precisam dos motores visuais.

**Runtime ausente é BLOQUEADO declarado, nunca desvio silencioso.** Faltando a dependência,
o especialista diz o que falta e como instalar, e para. Não entrega por outro caminho, não
improvisa, não entrega pela metade fingindo que está inteiro.

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
   A regra está na seção 0 de `agents/diretor-operacoes/agents/diretor-de-operacoes.md` e viaja
   nos briefings como `EXECUTION_MODE: SILENT`. Painel não é decoração: agente listado ali tem
   job de verdade.
8. **Demanda de cliente entra pelo Diretor.** Pedido que vira entregável — peça, roteiro,
   página, vídeo, campanha — é acionado com `Agent(diretor-de-operacoes)`, não executado
   direto na sessão. É o Diretor que publica o painel de acionamento, monta o briefing com
   `EXECUTION_MODE: SILENT` e fecha pelo gate. **Executar direto pula o painel, pula o gate
   e pula a revisão** — e o gestor recebe algo que o squad nunca viu. Pergunta de uma linha
   sobre o repositório não é demanda de cliente: essa é da sessão mesmo.
9. **Entrega de roteiro é PDF.** Toda demanda de `copywriting.script` fecha pelo motor
   `agents/copywriter/engine/roteiro_pdf.py`. Markdown na resposta não é entrega.
10. **Pedido inviável se avisa antes de executar.** Percebendo que o pedido, do jeito que veio,
   não produz o que o gestor quer — falta insumo, a ferramenta não faz aquilo, o pedido se
   contradiz, o resultado seria reprovado na plataforma — diga **antes**, em duas linhas, com
   o caminho que funciona. Executar sabendo que vai dar errado é retrabalho que o gestor paga
   duas vezes. A regra completa está na seção 1.1 do Diretor.
11. **Nada visual sai sem alguém ter aberto o arquivo.** Parecer `APROVADO` é opinião sobre a
   peça, não a peça. Designer, Revisor e Diretor abrem o `.png` — o motor exige a inspeção
   registrada (`job.py inspecionar`) antes de liberar o handoff.
12. **Peça genérica é defeito, não questão de gosto.** O piso de suficiência
   (`agents/revisor-arte/conhecimento/criterios/criativos.md` §3.5) vale nos dois lados:
   o Designer responde as três perguntas em `art-direction.json` antes de renderizar — o motor
   recusa compilar sem elas — e o Revisor as verifica na peça pronta. Peça sem defeito que
   falha em duas das três não é aprovada.

13. **Não prometa aviso futuro.** Não existe execução em segundo plano para o gestor: a
   sessão não volta sozinha depois que o turno fecha. "Aviso quando terminar", "te aviso
   quando estiver pronto" e "assim que ficar pronto eu mando" são promessas que o Squad
   não tem como cumprir — o gestor fica esperando um retorno que nunca chega. Fechando o
   turno **sem a entrega na mão** — limite de turnos, de sessão, de ferramenta ou de
   ambiente — declare o estado real em uma linha: **onde parou, o ID da demanda e do job,
   e o que o gestor digita para retomar.** O motor já preserva o job; o que faltava era
   dizer. Isso não é narração de etapa e não abre exceção na regra 7: é o fechamento do
   turno, que sempre foi obrigatório — só não pode ser fechado com promessa.

## Layout

| Caminho | O que é |
|---|---|
| `.claude/` | **camada de controle versionada**: 7 agentes, skills próprias e `settings.json` com o hook. Symlinks relativos — o arquivo canônico é o de `agents/`/`apps/` |
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

**O controle já está de pé.** Clonou, abriu o Claude Code: os 7 agentes, as skills próprias
e o hook `PreToolUse` carregam de `.claude/`, sem rodar nada. Demanda textual funciona aqui.

`setup.sh` instala a **camada B** — motores, dependências e os dados fora do git:

```bash
bash scripts/setup.sh    # runtime: Playwright, Chromium, ffmpeg, venvs, humanizer
bash scripts/check.sh    # diagnostica CONTROLE e RUNTIME separados
```

`setup.sh` é idempotente e não apaga dado de cliente já existente na máquina. Ele também
mantém os symlinks em `~/.claude/`, para quem usa o Squad fora deste repositório.

## Ao mexer num agente

- Edite o arquivo **no repositório**, nunca a cópia em `~/.claude/` — ela é um symlink para cá.
- Mudou capability? Atualize `REGISTRY.md` no mesmo commit.
- Mudou dependência? Atualize `scripts/check.sh` e a seção *Dependências* do README.
