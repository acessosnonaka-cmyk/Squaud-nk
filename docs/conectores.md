# Conectores — o que existe, quem alcança, e o que isso obriga

Levantado em **2026-09-25**, com chamada real, não com leitura de configuração.
Este documento existe porque a autópsia da produção real achou uma coisa que nenhum
teste anterior tinha achado: **o Gestor de Tráfego nunca leu uma conta de anúncio.**
Não por bug — por arquitetura. Ele não tem como.

## 1. O que está conectado

| Conector | Estado | Cobre | Provado por |
|---|---|---|---|
| **Meta ADS** | conectado, ativo na sessão | contas, campanhas, insights, criativos, públicos, catálogo, pixel, benchmark | `ads_get_ad_accounts` devolveu 25+ contas reais, com `is_queryable` e moeda |
| **Ads Editor** | conectado, ativo na sessão | Meta **e Google Ads**: campanha, ad set, anúncio, keyword, orçamento, regra, relatório, UTM | listado como `connected` / `enabledInChat` |
| **Google Drive** | conectado, ativo na sessão | busca, leitura, metadado, permissão, upload | acervo de cliente lido em produção nesta semana |
| **Canva** | conectado | design, template de marca, export, remoção de fundo | — |
| **Gamma** | conectado | apresentação, doc, site | — |
| **ClickUp** | conectado | tarefa, lista, comentário, doc, tempo | — |
| **Higgsfield** | **desconectado** | — | `installState: disconnected` |

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
demanda.py consulta abrir <DEM> <JOB> --fonte meta_ads \
  --pergunta "<o que se quer DESCOBRIR, não a tabela que se quer puxar>" \
  --corte    "<nível, campos, período, quebra, filtro — o que o runtime executa>" \
  --hipotese "<o que este dado pode DERRUBAR>"

demanda.py consulta pendentes <DEM>                       # fila do runtime
demanda.py consulta responder <DEM> CONSULTA-001 --arquivo <caminho>
```

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
