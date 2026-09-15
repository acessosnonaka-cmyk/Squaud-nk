# Gestor de Tráfego — o sétimo agente

**Estado: IMPLEMENTADO. Recomenda por padrão; executar na conta exige aprovação.**

Membro formal do roster (`squad.yaml`), com prompt, skill e base de conhecimento em
`agents/gestor-de-trafego/`, publicado como plugin `gestor-de-trafego@squad-legend-ai`. O
Diretor delega a ele por `trafego.planejamento`, `trafego.criacao`, `trafego.otimizacao` e
`trafego.analise`.

**O que continua valendo do desenho original:** nada de campanha é simulado. Sem leitura
real da conta ele declara a limitação em vez de estimar métrica, e qualquer ação de subir,
pausar, ativar ou mexer em orçamento é `REQUER_APROVACAO` no `policy.yaml` — não sai sem
aprovação registrada do gestor humano.

**A decisão que estava em aberto — recomendar ou executar — foi resolvida como
"recomendar primeiro":** ele é seguro de acionar porque a execução depende de um portão
externo a ele, não da própria boa vontade.

---

## O que ainda falta (e não é bloqueio para acionar)

| Lacuna | Efeito hoje |
|---|---|
| As 5 skills da conta claude.ai não estão em disco | O conhecimento embarcado é o de `agents/gestor-de-trafego/conhecimento/`; o acervo da conta segue no claude.ai |
| Conector Meta ADS com OAuth expirado | Sem leitura automática de conta: os dados entram por exportação manual |
| Sem integração web | O agente roda no Claude Code; o dashboard mostra o card, sem botão |

O levantamento abaixo é de 2026-09-15 e continua válido como mapa do que existe fora do
repositório.

---

## O que foi procurado, e onde

Busca feita em 2026-09-15, fora e dentro do repositório:

| Onde | Resultado |
|---|---|
| `agents/**/agents/*.md` do repositório | nenhum agente de tráfego — **resolvido: `agents/gestor-de-trafego/agents/gestor-de-trafego.md`** |
| `~/.claude/agents/` | só `copywriter` e `diretor-de-operacoes` |
| `~/.claude/skills/` e `~/.agents/skills/` | `designer-ia`, `humanizer`, `lp-*` — nenhuma de tráfego |
| Plugins instalados (Linux e Windows) | só `revisor-de-criacao` |
| `~/projetos/` | menções ao papel, nenhuma implementação |
| Arquivos com nome de tráfego/ads/campanha | nenhum |

**Conclusão à época: não existia implementação real a preservar.** Nada foi inventado no lugar — o agente foi escrito depois, e este documento virou o registro do que ele ainda não alcança.

## O que existe de verdade, e por que não serve ainda

Duas coisas reais apareceram. Nenhuma é um agente, e nenhuma é versionável aqui:

### 1. Cinco skills na conta claude.ai

Registradas em `~/.claude/projects/-home-ffili/memory/roteamento-skills-conta.md`. **Não
ficam em disco** e **não são invocáveis pelo Claude Code** — existem apenas dentro do
claude.ai:

| Skill | Cobre |
|---|---|
| `trafego-gestao-nonaka` | analisar, diagnosticar, otimizar e reportar campanha Meta/Google |
| `trafego-diagnostico-inicial-de-conta-meta-ads` | auditoria inicial de conta Meta |
| `google-ads-keywords-nonaka` | palavras-chave, RSA (15 títulos + 4 descrições), negativações |
| `analise-de-concorrentes` | comparação estratégica e plano de ação |
| `mapeamento-concorrentes` | Meta Ads Library e Google Ads Transparency |

Isso é o **acervo de conhecimento** do agente, já escrito, no lugar errado para este
projeto. É o insumo mais valioso que existe hoje — e o caminho mais curto para o agente.

### 2. Um conector Meta ADS

`claude.ai Meta ADS`, conector MCP da conta. Há registro de uso entre 30/08 e 02/09/2026.
O último log traz:

```
authentication_error: OAuth token has been invalidated. Re-authentication is required.
```

Ou seja: **existe, foi usado, e está com a autenticação expirada.** Como todo conector do
claude.ai, ele não existe fora do claude.ai — nem no Claude Code com token de assinatura,
nem numa aplicação própria (ver `docs/arquitetura-web.md` §5).

---

## O plano original — itens 1 e 4 cumpridos

Quatro itens, em ordem. O primeiro sozinho já o torna acionável no Claude Code.

### 1. Prompt do agente — ✅ feito, em `agents/gestor-de-trafego/agents/gestor-de-trafego.md`

O mesmo formato dos outros seis: frontmatter com `name`, `description` e `tools`, e o corpo
definindo escopo, fronteiras, régua de decisão e critério de parada. Precisa responder:

- **O que é dele:** planejamento, criação, acompanhamento e otimização de campanha em Meta
  e Google; estrutura de conta, público, orçamento, UTM, pixel e tag; leitura de métrica,
  mapeamento de gargalo e geração de insight ao gestor humano.
- **O que não é dele:** a copy do anúncio (Copywriter), o criativo (Designer), a página de
  destino (LP Builder), o parecer sobre a peça (Revisor). Ele **recebe** esses artefatos.
- **A fronteira que mais importa:** onde termina recomendar e começa executar na conta do
  cliente. Subir, pausar, alterar orçamento e publicar mexem em dinheiro de terceiro — isso
  precisa de autorização humana explícita, job a job, e o prompt tem de dizer isso.
- **Regra de dado:** métrica afirmada sem leitura da conta é invenção. Sem acesso, ele
  declara a limitação em vez de estimar.

**Decisão tomada:** começa só recomendando. Executar na conta existe como capability
(`trafego.criacao`), mas passa pelo portão do `policy.yaml` e exige `guardrails.md`
preenchido para aquela conta.

### 2. Skills — ⏳ pendente: trazer o conhecimento da conta para o repositório

As cinco skills da conta claude.ai precisam virar `SKILL.md` em
`agents/gestor-trafego/skills/`. Não dá para automatizar: elas não estão em disco. O
caminho é abrir cada uma no claude.ai e trazer o conteúdo.

Sugestão de recorte, para não criar cinco skills onde bastam três:

| Skill nova | Vem de |
|---|---|
| `trafego-diagnostico` | `trafego-diagnostico-inicial-de-conta-meta-ads` + parte de `trafego-gestao-nonaka` |
| `trafego-otimizacao` | resto de `trafego-gestao-nonaka` |
| `pesquisa-concorrencia` | `analise-de-concorrentes` + `mapeamento-concorrentes` |

`google-ads-keywords-nonaka` entra como referência dentro de uma delas, ou como quarta
skill se o volume justificar.

### 3. Acesso aos dados da campanha — ⏳ pendente

Sem isso ele opina no escuro. Três caminhos, do mais barato ao mais robusto:

| Caminho | Custo | Limite |
|---|---|---|
| **Exportação manual** — o gestor humano baixa o CSV do Meta/Google e entrega ao agente | zero | trabalho manual a cada análise; sem acompanhamento contínuo |
| **Reautenticar o conector Meta ADS** no claude.ai | zero | só funciona dentro do claude.ai; não serve ao Claude Code nem ao Squad NK Web |
| **API oficial** (Meta Marketing API / Google Ads API) com credencial própria | gratuito em si, mas exige app, revisão e token | é trabalho de desenvolvimento, e guarda credencial de cliente — decisão de segurança sua |

Para começar, a exportação manual basta e não custa nada.

### 4. Registro no roteamento — ✅ feito

`squad.yaml` com `agente: formal` e `prompt` apontado; `REGISTRY.md` com as capabilities
`trafego.*` na tabela de roteamento; `gestor-de-trafego` no enum de `job.schema.json` e em
`engine/modelo.py`. O Diretor delega sem mais nenhuma mudança.

---

## O que continua proibido

- Não afirmar que campanha foi criada, pausada, ajustada ou otimizada sem que isso tenha
  passado pelo portão e pela aprovação humana.
- Não estimar CPA, CTR, ROAS ou verba sem leitura real da conta.
- Não tratar as cinco skills da conta como já incorporadas: o conhecimento em disco é o
  de `conhecimento/`, e o acervo da conta ainda é o próximo salto de qualidade dele.
