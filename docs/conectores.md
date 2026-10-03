# Conectores — o que existe, quem alcança, e o que isso obriga

Levantado em **2026-09-25**, revisto em **2026-10-02**, com chamada real — não com
leitura de configuração. Este documento existe porque a autópsia da produção real achou
uma coisa que nenhum teste anterior tinha achado: **o Gestor de Tráfego nunca leu uma
conta de anúncio.** Não por bug — por arquitetura. Ele não tem como.

## 1. O que está conectado

| Conector | Estado | Cobre | Provado por |
|---|---|---|---|
| **Ads Editor** | conectado, ativo na sessão | **fonte operacional prioritária de mídia paga.** Meta **e** Google Ads na mesma superfície: conta, campanha, conjunto, anúncio, criativo, público, placement, keyword, termo de busca, orçamento, regra, otimização, relatório, UTM | `list_meta_accounts` devolveu **120 contas reais** com id, status e moeda (2026-10-02) |
| **Meta ADS** | conectado | contas, campanhas, insights, criativos, públicos, catálogo, pixel, benchmark de leilão | `ads_get_ad_accounts` devolveu 25+ contas, com `is_queryable` e moeda |
| **Google Drive** | conectado, ativo na sessão | busca, leitura, metadado, permissão, upload | acervo de cliente lido em produção |
| **Canva** | conectado | design, template de marca, export, remoção de fundo | — |
| **Gamma** | conectado | apresentação, doc, site | — |
| **ClickUp** | conectado | tarefa, lista, comentário, doc, tempo | — |
| **Higgsfield** | **desconectado** | — | `installState: disconnected` |

### 1.1 Ads Editor — as capacidades reais, por família

Conferidas no inventário de ferramentas da sessão. **Nada aqui é endpoint inventado**:
o que não estiver nesta lista, o runtime não executa.

| Família | Leitura (livre) | Alteração (passa pelo portão) |
|---|---|---|
| **Conta Meta** | `list_meta_accounts` · `get_account_dashboard` · `get_account_insights` · `get_account_info` · `get_account_summary` · `get_account_balance_status` | `hide_account_in_central` |
| **Campanha / conjunto / anúncio** | `list_campaigns` · `get_campaign_details` · `get_campaign_metrics` · `get_campaigns_budgets` · `list_adsets` · `get_adset_details` · `get_adset_insights` · `list_ads` · `list_ads_with_insights` · `get_ad_details` · `get_ad_insights` | `create_campaign` · `update_campaign` · `update_budget` · `pause_*` · `activate_*` · `toggle_*` · `delete_*` · `clone_*` · `bulk_pause_ads` |
| **Recorte analítico** | `get_insights_breakdown` (idade, gênero, dispositivo, placement) · `get_adsets_locations` | — |
| **Criativo** | `get_ad_details` (um `ad_id` por chamada) · `get_ad_post_links` · `list_campaign_videos` · `list_page_videos` · `list_ig_videos` | `update_ad_creative` · `upload_ad_media` · `create_ads_from_media` |
| **Público** | `list_audiences` · `get_audience_size` · `list_audience_campaigns` | `create_audience` · `update_*` · `delete_audience` |
| **Tracking** | `list_pixel_events` · `list_pixel_custom_events` · `list_lead_forms` · `list_integrations_utms` | `set_google_url_options` · `create_lead_form` |
| **Google Ads** | `list_google_accounts` · `list_google_campaigns` · `get_google_campaign_details` · `get_google_campaign_metrics` · `list_google_adgroups` · `list_google_ads` · `list_google_keywords` · `list_google_search_terms` · `list_google_demographics` · `list_google_recommendations` · `get_google_account_timeseries` | `update_google_budget` · `update_google_bidding` · `add/remove_google_keyword` · `pause_google_*` · `create_google_*` |
| **Histórico de alteração** | `get_optimization_history` · `get_google_optimization_history` · `list_recent_rule_executions` | `create_optimization` · `create_rule` · `toggle_rule` |

**Corrigido em 2026-10-03, por execução:** `get_creatives` estava listado aqui e **não existe**
no inventário da sessão. Quem achou foi a coleta da Arte Mineira, tentando chamá-lo. A lição não
é o nome errado — é que lista de capacidade escrita de memória envelhece como documentação e
falha como contrato. Vale conferir contra o inventário antes de escrever um `--corte`.

**Limites de leitura medidos na mesma coleta, que mudam o que se pode pedir:**

| Ferramenta | O limite |
|---|---|
| `list_adsets`, `list_ads_with_insights` | **ignoram `date_since`/`date_until`**. As chamadas com dois períodos diferentes voltam idênticas. A única janela que funciona é `period="last_30d"` |
| `get_insights_breakdown` | recusa chamada sem `breakdowns` nem `time_increment`. Agregado de período por campanha sai com `time_increment=7` dentro da janela |
| `list_pixel_events` | não aceita período e não devolve data do último evento: os counts vêm sem recorte |
| `get_optimization_history` | exige `optimization_id`. Com `list_optimizations` vazia, não há change log |
| `list_audience_campaigns` | devolve as campanhas da conta, **não** o vínculo público→campanha |
| `list_campaigns` | parou em 200 numa conta com 270+ campanhas: corte silencioso, pagine |

**O que o Ads Editor NÃO cobre, e por isso continua lacuna:** comportamento na página
(sem GA4), TikTok Ads, CRM e WhatsApp. Ver §2 — o conector novo não fecha nenhuma delas.

## 2. O que NÃO existe

| Fonte | Situação | Consequência prática |
|---|---|---|
| **GA4 / Google Analytics** | **nenhum conector** | comportamento na página, origem de sessão e funil fora da plataforma de mídia **não são leitura, são relato**. Atribuição cruzada entre plataforma e site não se resolve aqui |
| **TikTok Ads** | **nenhum conector** | o Gestor cobre TikTok no raciocínio e no planejamento; **não lê a conta**. `capabilities.json` que prometa leitura de TikTok está prometendo o que a máquina não faz |
| **CRM** | nenhum conector | qualificação de lead e fechamento entram por export que alguém colocou na mão do Squad. Sem isso, CAC e taxa de fechamento são CÁLCULO sobre dado relatado, não FATO |
| **WhatsApp** | nenhum conector | conversa iniciada, respondida e agendada — o fundo do funil de quase todo cliente — é invisível ao Squad |

Declarar isto tem uso imediato: são exatamente as quatro lacunas que um relatório de
tráfego costuma preencher com linguagem de fato sem ter o fato.

## 3. A descoberta estrutural: nenhum agente alcança nada disso

Uma linha prova:

```bash
grep -h "^tools:" .claude/agents/*.md
```

```
tools: Read, Grep, Glob, Bash, Write, Skill                      # copywriter
tools: Read, Grep, Glob, Bash, Write, Skill, Agent               # designer
tools: Read, Grep, Glob, Bash, Write, Skill, Agent               # diretor-de-operacoes
tools: Read, Grep, Glob, Bash, Write, Edit, WebSearch, WebFetch, Skill   # gestor-de-trafego
tools: Read, Grep, Glob, Bash, Write, Skill                      # legend-ia
tools: Read, Grep, Glob, Bash, Write, Skill, Agent               # lp-builder
tools: Read, Grep, Glob, Bash, Write, Skill                      # revisor-de-criacao
```

**Nenhum `mcp__` em nenhum dos sete.** Os conectores vivem na **sessão** que aciona o
Squad, e um subagente não alcança as ferramentas da sessão — a mesma fronteira de
plataforma que impede o Diretor de chamar outro agente.

Então o mapa real é este:

```
SESSÃO          tem Drive, Meta ADS, Ads Editor, Canva, Gamma, ClickUp
DIRETOR         não tem nenhum  — planeja, cobra, fecha
ESPECIALISTA    não tem nenhum  — raciocina sobre o dado que alguém trouxe
```

Consequência que precisa estar escrita para não ser redescoberta por acidente: **um
especialista que não pede dado analisa o resumo do briefing achando que analisou a
conta.** Foi o que aconteceu com o relatório do Psiu Cosméticos e com a Source of Truth
da Academia Mergulho — em nenhum dos dois casos o especialista mentiu; ele analisou
honestamente o que chegou, e o que chegou era um resumo.

## 4. O único caminho que funciona: a consulta

Por isso o motor ganhou `demanda.py consulta`. O especialista declara o que quer
descobrir; a sessão executa o conector; o dado bruto volta em arquivo.

```bash
demanda.py consulta abrir <DEM> <JOB> --fonte ads_editor \
  --pergunta "<o que se quer DESCOBRIR, não a tabela que se quer puxar>" \
  --corte    "<nível, campos, período, quebra, filtro — o que o runtime executa>" \
  --hipotese "<o que este dado pode DERRUBAR>"

demanda.py consulta pendentes <DEM>                       # fila do runtime
demanda.py consulta responder <DEM> CONSULTA-001 --arquivo <caminho> \
  --ferramenta mcp__Ads_Editor__get_account_insights \
  --ferramenta mcp__Ads_Editor__get_insights_breakdown
```

`ads_editor` é a fonte prioritária de mídia paga: um conector só, Meta e Google na mesma
superfície, e é o único que desce a placement, dispositivo, termo de busca e histórico de
alteração.

**`--ferramenta` registra o que o runtime chamou de verdade.** Sem ele, "o Ads Editor foi
consultado" é afirmação do runtime sobre si mesmo — e a autópsia já mostrou onde isso
termina. Com o nome gravado em `consultas[].ferramentas`, a diferença entre conector
chamado e conector citado para de ser questão de confiança. `consulta listar` imprime.

Três travas, todas do motor e nenhuma de etiqueta:

1. `--pergunta` com menos de 25 caracteres é recusada: *"quero ver os anúncios"* não é
   pergunta de investigação;
2. `--corte` é obrigatório — corte vago volta dado vago;
3. **consulta `PENDENTE` trava o `FINAL_REQUEST_GATE`**: a demanda não fecha com dado
   pedido e não recebido, e `responder` exige arquivo que exista no disco.

`--hipotese` não é enfeite: escrever o que o dado **derrubaria** é a diferença entre
testar uma tese e procurar confirmação para ela.

## 5. O que fazer quando a fonte não tem conector

GA4, TikTok, CRM e WhatsApp continuam sem conector depois desta rodada — e isso **não**
é motivo para o especialista inferir. `consulta abrir --fonte ga4` registra o pedido; se
a sessão não tem como executar, `consulta responder --sem-dado` fecha a consulta
declarando a ausência, e a lacuna viaja declarada até o relatório em vez de virar
hipótese silenciosa.

Runtime que falta é **BLOQUEADO declarado**, nunca desvio silencioso (`CLAUDE.md`).
Vale para Chromium e vale igual para conector.
