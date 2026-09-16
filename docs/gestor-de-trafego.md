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
| As 5 skills da conta não estão **neste repositório** | O conhecimento versionado é o de `agents/gestor-de-trafego/conhecimento/`. Elas são sincronizadas para a máquina pela conta (`~/.claude/skills/synced/`) e ficam invocáveis, mas continuam fora do git e fora do controle deste projeto |
| Nenhum motor de dados | Não há código que leia, agregue ou cruze métrica. O conector do Meta responde no claude.ai; fora dele, o dado entra por exportação manual |
| Sem integração web | O agente roda no Claude Code; o dashboard mostra o card, sem botão |

O levantamento abaixo é de 2026-09-15. **Revisado em 2026-09-16** — ver a nota de
verificação em cada item que mudou.

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

> **Corrigido em 2026-09-16.** A afirmação original — "não ficam em disco, não são
> invocáveis pelo Claude Code" — **está errada**. A conta sincroniza as skills para
> `~/.claude/skills/synced/<org>_<conta>/`, e o Claude Code as carrega e invoca com
> prefixo de origem (ex.: `Skill(anthropic-skills:trafego-gestao-nonaka)`). Verificado
> por leitura de disco e pelo `manifest.json`, que traz `source: custom` e a data de
> cada uma. São **27 skills** sincronizadas no total, não só estas cinco.
>
> O que continua verdadeiro: elas **não estão neste repositório**, não são versionadas
> aqui, não passam por revisão do projeto e somem se a conta parar de sincronizá-las.
> Por isso o item 2 do plano abaixo segue pendente — o objetivo nunca foi "estar em
> disco", e sim **ser código do Squad**.

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

> **Corrigido em 2026-09-16.** O token acima **foi renovado**. Verificação por leitura
> real nesta data, com `ads_get_ad_accounts` (somente leitura): o conector respondeu com
> as contas de anúncio da carteira, todas `ACTIVE`, `is_ads_mcp_enabled: true` e
> `is_queryable: true` — ou seja, `ads_get_ad_entities` e os endpoints de insights também
> estão ao alcance. **Leitura de conta deixou de ser uma lacuna.**

O que **não** mudou, e continua decidindo a arquitetura: como todo conector do claude.ai,
ele não existe fora do claude.ai — nem no Claude Code com token de assinatura, nem numa
aplicação própria (ver `docs/arquitetura-web.md` §5). Então a leitura automática existe
**na superfície onde o conector está montado**, e não no Squad NK Web.

Duas regras seguem valendo, e não dependem do token:

- **Escrita continua fechada.** Criar, subir, pausar, duplicar ou mexer em orçamento é
  `REQUER_APROVACAO` no `policy.yaml`, com ou sem conector autenticado. O hook
  `PreToolUse` também barra a forma crua (`curl -X POST` na Graph API) desde a correção
  de 2026-09-16.
- **Métrica sem leitura é invenção.** A regra nunca foi "não há acesso"; é "não estime o
  que você não leu". Com acesso, ele lê e cita; sem acesso, declara a limitação.

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

### 3. Acesso aos dados da campanha — ⏳ parcial (era: pendente)

**O segundo caminho da tabela deixou de ser hipótese** — o conector do Meta está
autenticado e lê (verificado em 2026-09-16). Continua valendo o limite dele: só funciona
na superfície onde o conector está montado.

| Caminho | Custo | Situação em 2026-09-16 | Limite |
|---|---|---|---|
| **Exportação manual** — o gestor humano baixa o CSV do Meta/Google e entrega ao agente | zero | disponível | trabalho manual a cada análise; sem acompanhamento contínuo |
| **Conector Meta ADS** no claude.ai | zero | **✅ autenticado e lendo** | só Meta (não cobre Google nem TikTok); não serve ao Squad NK Web |
| **API oficial** (Meta Marketing API / Google Ads API) com credencial própria | gratuito em si, mas exige app, revisão e token | não iniciado | é trabalho de desenvolvimento, e guarda credencial de cliente — decisão de segurança sua |

O que falta para fechar o item: **Google Ads e TikTok continuam sem leitura**, e nenhuma
das três vias alimenta o `historico.md` sozinha — registrar o aprendizado segue sendo
passo do agente, não do conector.

### 4. Registro no roteamento — ✅ feito

`squad.yaml` com `agente: formal` e `prompt` apontado; `REGISTRY.md` com as capabilities
`trafego.*` na tabela de roteamento; `gestor-de-trafego` no enum de `job.schema.json` e em
`engine/modelo.py`. O Diretor delega sem mais nenhuma mudança.

---

## O que continua proibido

- Não afirmar que campanha foi criada, pausada, ajustada ou otimizada sem que isso tenha
  passado pelo portão e pela aprovação humana.
- Não estimar CPA, CTR, ROAS ou verba sem leitura real da conta.
- Não tratar as cinco skills da conta como já incorporadas: o conhecimento **versionado**
  é o de `conhecimento/`. Estarem sincronizadas e invocáveis na máquina não as torna
  código do Squad — o acervo da conta ainda é o próximo salto de qualidade dele.
- Não confundir **ler** com **poder mexer**: o conector do Meta autenticado libera leitura,
  e nada mais. Toda escrita continua em `REQUER_APROVACAO`, job a job.
