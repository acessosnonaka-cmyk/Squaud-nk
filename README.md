# SQUAD NK

Repositório central do **Squad NK**: **1 orquestrador + 6 especialistas = 7 agentes**, usados na
operação da Nonaka ADS. Fonte da verdade do código e da configuração — o que não está aqui não
existe.

O roster oficial é [`squad.yaml`](squad.yaml): legível por máquina, lido pela documentação, pelo
Diretor de Operações e pelo dashboard do Squad NK Web. Os três reconhecem a mesma arquitetura.

| | Agente | Papel | Representação | Web |
|---|---|---|---|---|
| ♟️ | **Diretor de Operações** | orquestrador | prompt | não integrado |
| ✍️ | **Copywriter** | especialista | prompt + 4 skills | não integrado |
| 🎨 | **Designer** | especialista | prompt + skill + motor | não integrado |
| 🧱 | **LP Builder** | especialista | prompt + 4 skills + motor | parcial |
| 🎬 | **Legend IA** | especialista | prompt + skill + motor | **integrado** |
| 🔎 | **Revisor de Arte** | especialista | prompt + 4 skills + motor | não integrado |
| 📈 | **Gestor de Tráfego** | especialista | prompt + skill + conhecimento | não integrado |

**Agente ≠ skill ≠ motor ≠ conector.** Um agente raciocina e decide; skill é conhecimento que ele
carrega; motor é executor determinístico que ele aciona; conector é integração externa que ele usa.
Estar implementado hoje como skill ou motor não faz de ninguém menos agente.

O Gestor de Tráfego **recomenda por padrão e só executa com autorização**: criar, subir, pausar
ou mexer em orçamento é `REQUER_APROVACAO` no [`policy.yaml`](agents/diretor-operacoes/policy.yaml).
Sem leitura real da conta ele declara a limitação em vez de estimar — nada de campanha é
simulado. Estado do acesso em [`docs/gestor-de-trafego.md`](docs/gestor-de-trafego.md).

---

## Arquitetura

```
                        ┌──────────────────────────┐
   demanda  ─────────►  │  DIRETOR DE OPERAÇÕES    │  lê REGISTRY.md,
                        │  (orquestrador)          │  roteia por capability
                        └───────────┬──────────────┘
                                    │  cria briefing mestre + jobs
        ┌───────────────┬───────────┼───────────────┬──────────────┐
        ▼               ▼           ▼               ▼              ▼
  ┌───────────┐  ┌────────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐
  │COPYWRITER │  │ DESIGN IA  │ │LP BUILDER│ │ LEGEND IA  │ │  humanizer │
  │  (copy)   │  │ (peça)     │ │ (página) │ │  (vídeo)   │ │  (revisão  │
  └─────┬─────┘  └─────┬──────┘ └────┬─────┘ └─────┬──────┘ │   textual) │
        │              │             │             │        └────────────┘
        └──────────────┴──────┬──────┴─────────────┘
                              ▼
                    ┌──────────────────┐
                    │ REVISOR DE ARTE  │  julga a peça pronta
                    └────────┬─────────┘  (LP passa por lp-qa)
                             ▼
                          entrega
                             │
                             ▼
                  ┌──────────────────────┐
                  │  GESTOR DE TRÁFEGO   │  veicula, mede e diagnostica;
                  └──────────┬───────────┘  o gargalo vira a próxima demanda
                             │
                             └────────────► volta ao Diretor de Operações
```

Precedência verbal: existindo job de copy, os executores não reinventam a estratégia verbal.
`COPYWRITER → COPY APROVADA → ESPECIALISTA`. Detalhe em
[`agents/diretor-operacoes/REGISTRY.md`](agents/diretor-operacoes/REGISTRY.md).

**Runtime de todos eles é o Claude Code.** Os agentes são prompts, skills e motores Python; quem
raciocina é o modelo carregado pelo Claude Code. Isso importa para a etapa web — veja
[`docs/arquitetura-web.md`](docs/arquitetura-web.md).

---

## Componentes

### LP Builder

**Função** — constrói Landing Page de ponta a ponta: triagem do acervo do Google Drive,
implementação da página, design review, QA e publicação de preview versionado.

**Tecnologia** — 4 skills do Claude Code + 3 scripts Python (`drive_ingest.py`, `lp_qa.py`,
`publish.py`). QA e screenshots usam Playwright/Chromium.

**Como executar** — dentro do Claude Code, em linguagem natural. As skills disparam sozinhas:

```
Skill(lp-ingestao)      → tria o Drive do cliente
Skill(lp-design-review) → crítica de direção de arte
Skill(lp-qa)            → QA obrigatório antes de entregar
Skill(lp-publicar)      → publica o preview e devolve URL
```

Motor direto, se precisar:

```bash
python3 ~/.claude/lp-builder/lp_qa.py <arquivo.html>
python3 ~/.claude/lp-builder/publish.py <slug> <arquivo.html>
```

### Diretor de Operações

**Função** — porta única do Squad. Entende a demanda, carrega a Source of Truth do cliente,
identifica as capabilities necessárias, cria o briefing mestre e os jobs, delega, paraleliza o que
é independente, aciona a revisão e consolida a entrega. **Não executa o trabalho dos especialistas.**

**Como executar** — no Claude Code:

```
Agent(subagent_type: "diretor-de-operacoes")
```

Ou em linguagem natural: "organize e execute", "acionando o squad", qualquer demanda que envolva
mais de um especialista.

**Travas de pedido.** O que o gestor escreveu entra na demanda palavra por palavra e é
imutável; cada coisa pedida vira um requisito com dono; e `demanda.py concluir` passa pelo
FINAL_REQUEST_GATE — requisito pendente, "cumprido" sem evidência, job aberto ou aprovação
esperando barram a entrega. Revisão aprovada não substitui a conferência: 4 criativos aprovados
não fecham um pedido de 5.

```bash
E=agents/diretor-operacoes/engine
python3 $E/auditoria.py                     # o roster bate com o disco?
python3 agents/diretor-operacoes/testes/teste-roteamento.py   # roteamento, contrato e travas
```

A auditoria compara `squad.yaml` com os prompts, o frontmatter de cada um, skills, motores, o
`REGISTRY.md` e a forma de instalação — symlink do `setup.sh` ou plugin do marketplace — e
devolve `SQUAD NK VALIDADO` ou o bloqueio. Os seis especialistas passam, **Gestor de Tráfego
incluído**: ele é acionável por `Agent(subagent_type: "gestor-de-trafego")` e recebe job como
qualquer outro. Acionável não é autorizado — subir, ativar, pausar ou mexer em orçamento
continua `REQUER_APROVACAO` no `policy.yaml`.

**Interface — modo ultrassilencioso.** O Diretor analisa, planeja e delega sem publicar nada.
A única mensagem antes da entrega é o painel, com **apenas os especialistas realmente acionados**:

```
╔══════════════════════════════════════╗
║         ♟️ ATIVANDO SQUAD NK          ║
╠══════════════════════════════════════╣
║ ✍️ COPYWRITER        ● TRABALHANDO... ║
║ 🎨 DESIGNER          ● TRABALHANDO... ║
║ 🔎 REVISOR DE ARTE   ● TRABALHANDO... ║
╚══════════════════════════════════════╝
```

Quem não tem job nesta demanda não aparece — sem `aguardando`, sem `standby`. Depois do painel
vem silêncio: nada de progresso, handoff ou log. Só a dúvida que muda o resultado interrompe, e
o que volta no fim é a entrega. Todo especialista acionado recebe `EXECUTION_MODE: SILENT` no
briefing e trabalha da mesma forma.

Os status são dois: `● TRABALHANDO...` para job real disparado e `⚠ BLOQUEADO` para
especialista necessário que não está disponível na sessão. Indisponível **não** vira execução
pelo Claude principal — vira bloqueio declarado com a causa.

**Roteamento sem palavra-chave.** Demanda de marketing entra pelo Diretor sozinha; o gestor não
escreve "acione o Squad". A regra global e autocontida está na seção *Roteamento obrigatório* do
[`CLAUDE.md`](CLAUDE.md), que é o arquivo que o Claude Code carrega em toda sessão — inclusive na
web. O prompt do Diretor ([seção 0](agents/diretor-operacoes/agents/diretor-de-operacoes.md)) e
este README repetem o template por necessidade de plataforma, e `auditoria.py` confere que as
três cópias não divergiram.

**Portabilidade.** Os 7 agentes chegam ao Claude Code por [`.claude/agents/`](.claude/agents) e
as skills próprias por [`.claude/skills/`](.claude/skills), como symlink para o arquivo canônico
do repositório. Clone novo já enxerga o Squad, sem `setup.sh` antes. O `setup.sh` continua sendo
o que instala **motores e dependências** — Chromium, Pillow, humanizer, dados fora do git.

### Design IA

**Função** — cria peça gráfica profissional a partir de briefing em linguagem natural: interpreta o
pedido, consulta a identidade visual do cliente, define direção de arte, escreve os textos, monta a
peça, valida e submete ao Revisor de Arte antes de entregar.

**Tecnologia** — skill `designer-ia` + motor `art-builder`: Python (só stdlib) que monta HTML a
partir de 6 templates e renderiza em PNG via Playwright/Chromium. Pool de 19 fontes embarcado.

**Como executar** — no Claude Code:

```
Skill(designer-ia)
```

"crie uma arte de feed para o cliente X divulgando Y".

### Revisor de Arte

**Função** — controle de qualidade. Compara **o que foi pedido** com **o que foi entregue** —
criativos, landing pages e vídeos. Devolve parecer com estrelas, status e correções.
Nunca edita o que revisa.

**Como executar** — é um plugin do Claude Code. Uma vez por máquina:

```bash
claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
claude plugin install revisor-de-criacao@squad-legend-ai
```

Depois, em linguagem natural: link do Drive + tipo da peça. O Design IA o localiza sozinho via
`python3 ~/.claude/art-builder/revisor.py locate`.

### Gestor de Tráfego

**Função** — performance e aquisição em Meta Ads, Google Ads e TikTok Ads: planeja mídia, lê
resultado, encontra o gargalo com evidência e recomenda manter, pausar, testar ou escalar. Pensa
negócio antes de plataforma. **Não escreve a copy do anúncio** (Copywriter) e não produz peça
(Designer, Legend IA, LP Builder) — ele define o ângulo, o público e o critério de sucesso, e
depois mede o que voltou.

**Capabilities** — `trafego.planejamento`, `trafego.criacao`, `trafego.otimizacao`,
`trafego.analise`. Acionável pelo Diretor por qualquer uma delas.

**Fronteira de execução** — recomendar é autônomo; executar na conta do cliente não. Subir,
pausar, ativar ou mexer em orçamento cai em `REQUER_APROVACAO` no `policy.yaml`, passa pelo portão
do Diretor e pelo hook `PreToolUse`, e exige `guardrails.md` preenchido para aquela conta.

**Como executar** — é um plugin do Claude Code. Uma vez por máquina:

```bash
claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
claude plugin install gestor-de-trafego@squad-legend-ai
```

Depois, em linguagem natural: "use o Gestor de Tráfego para analisar a conta do cliente X".

**Antes de operar uma conta** — a memória de mídia fica fora do git, em
`$SQUAD_DATA_HOME/trafego/clients/<slug>/` (`contexto.md`, `guardrails.md`,
`historico.md`). Sem `guardrails.md` preenchido, toda alteração financeira exige aprovação
humana. Detalhe em [`agents/gestor-de-trafego/README.md`](agents/gestor-de-trafego/README.md).

### Legend IA

**Função** — pipeline de vídeo: transcreve o áudio, revisa a transcrição, queima legendas,
headline e CTA no vídeo. O arquivo de entrada nunca é alterado.

**Tecnologia** — Python + FFmpeg (libx264, drawtext, libass) + `faster-whisper` (modelo `base`,
CPU, português, timestamps por palavra). Fontes embarcadas em `apps/legend-ia/fonts/`.

**Como executar**

```bash
apps/legend-ia/venv/bin/python apps/legend-ia/process_video.py 01.mp4 --cta "CLIQUE NO BOTÃO ABAIXO"
```

Entrada em `apps/legend-ia/entrada de vídeo/`, saída em `apps/legend-ia/entrega/`.
Presets visuais: `--preset classic` (padrão) e `--preset pro`.

---

## Skills compartilhadas

| Skill | Onde | Origem | Licença |
|---|---|---|---|
| `humanizer` | `shared/skills/humanizer` | [blader/humanizer](https://github.com/blader/humanizer) v3.0.0 | MIT |
| `copywriting` | `agents/copywriter/skills/` | entpnomad/copywriting `c3b84cb` | MIT |
| `caption-writer` | `agents/copywriter/skills/` | social-media-skills/skills `6e30eeb` | MIT |
| `short-form-video-script` | `agents/copywriter/skills/` | social-media-skills/skills `6e30eeb` | MIT |
| `landing-page-copy` | `agents/copywriter/skills/` | rampstackco/claude-skills `a67dd34` | MIT |

`humanizer` não é versionado aqui — `scripts/setup.sh` clona do upstream. As outras quatro estão
no repositório com o LICENSE de cada uma. Procedência completa em
[`agents/copywriter/PROCEDENCIA.md`](agents/copywriter/PROCEDENCIA.md).

---

## Dependências

| Dependência | Quem precisa | Obrigatória |
|---|---|---|
| **Claude Code** 2.1.251+ | todos os componentes | sim — é o runtime |
| Python 3.11+ | LP Builder, Design IA, Legend IA | sim |
| Git | setup e plugin do Revisor | sim |
| FFmpeg + ffprobe (libx264, libass) | Legend IA; medição técnica do Revisor | sim para vídeo |
| Playwright + Chromium | render do Design IA, QA/screenshot do LP Builder | sim para arte e LP |
| `Pillow` | `validate.py` do Design IA — conferência da peça renderizada | sim para arte |
| `faster-whisper` | Legend IA | sim para transcrição |
| Conector Google Drive do claude.ai | LP Builder (ingestão), Revisor (link de Drive) | conta, não máquina |
| `rsync` + SSH | LP Builder, só ao publicar em VPS | não |

Nenhum MCP server está configurado. Nenhum banco de dados é usado por estes cinco componentes.

---

## Variáveis de ambiente

Todas opcionais — sem nenhuma delas o Squad roda local. Copie `.env.example` para `.env`:

```bash
cp .env.example .env
```

| Variável | Para quê |
|---|---|
| `SQUAD_DATA_HOME` | raiz dos dados de trabalho (padrão `~/.squad-nk`) |
| `LP_PUBLISH_BASE_URL` | URL pública do preview; sem ela, `http://localhost:8090` |
| `LP_PUBLISH_REMOTE_*` | host, user, path e chave do VPS de preview |
| `DESIGNER_REVISOR_HOME` | aponta manualmente a instalação do Revisor de Arte |
| `LEGEND_WHISPER_MODEL` | modelo do faster-whisper (`base`, `small`, `medium`, `large-v3`) |
| `ANTHROPIC_API_KEY` | **só** para a futura execução web. **Gera custo.** |
| `SQUAD_WEB_SESSION_SECRET` | sessão da futura interface web |

O `.env` está no `.gitignore`. Nunca comite valor real.

---

## Instalação

```bash
git clone git@github.com:acessosnonaka-cmyk/Squaud-nk.git
cd Squaud-nk
bash scripts/setup.sh
bash scripts/check.sh
```

`setup.sh` liga os agentes e as skills ao Claude Code por symlink, prepara os motores em
`~/.claude/art-builder` e `~/.claude/lp-builder`, clona o `humanizer` e monta o venv do Legend IA.
É idempotente e não sobrescreve dado de cliente já existente.

Faltam os plugins, que são manuais (uma vez por máquina). Cada um é instalado
separadamente — instalar um não traz o outro:

```bash
claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
claude plugin install revisor-de-criacao@squad-legend-ai
claude plugin install gestor-de-trafego@squad-legend-ai
```

Dependências de sistema, se `check.sh` reclamar:

```bash
sudo apt install ffmpeg python3-venv
pip install playwright Pillow && python3 -m playwright install chromium
apps/lp-builder/venv/bin/python -m playwright install chromium   # o QA da LP roda no venv dele
bash scripts/chromium-libs.sh          # libnss3/libnspr4, funciona sem root
```

---

## Desenvolvimento local

Edite sempre **no repositório**. `~/.claude/agents/*` e `~/.claude/skills/*` são symlinks para cá,
então a mudança vale na hora, sem reinstalar nada.

```bash
bash scripts/check.sh          # diagnóstico: 🟢 pronto  🟡 falta instalar  🔴 quebrado
git add -p && git commit
git push origin main
```

Dados de trabalho ficam fora do git, por desenho:

| Fica em | O que é |
|---|---|
| `~/.claude/art-builder/clients/<slug>/brand.json` | Source of Truth do cliente (canônica) |
| `~/.claude/art-builder/jobs/` | rastro de produção das peças |
| `~/.claude/lp-builder/clients/<slug>/index.json` | acervo triado da ingestão |
| `~/.claude/lp-builder/previews/<slug>/current/` | LP vigente |
| `$SQUAD_DATA_HOME/trafego/clients/<slug>/` | memória de mídia do Gestor de Tráfego |

---

## Produção

Hoje não existe produção. Os cinco componentes rodam **na máquina de quem opera**, dentro do
Claude Code. O único artefato que sai para fora é o preview de LP:

- **padrão** — `python3 -m http.server 8090` sobre `~/.claude/lp-builder/previews/`, só local;
- **VPS** — preencha o bloco `remote` de `~/.claude/lp-builder/publish.conf.json` e a publicação
  passa a enviar por `rsync` + SSH, com URL pública estável e rollback por versão.

---

## Squad NK Web

Aplicação para o time usar o Squad pelo navegador, sem terminal, WSL, Git ou Claude Code.
Está em [`apps/web/`](apps/web/); como operar em [`docs/squad-nk-web.md`](docs/squad-nk-web.md).

```bash
cp .env.example .env
python3 -c "import secrets;print(secrets.token_urlsafe(48))"   # SQUAD_WEB_SESSION_SECRET
docker compose up -d                                           # http://127.0.0.1:8000
```

**Versão atual: v0.2.** Login, dashboard dos seis agentes, fila, status ao vivo e histórico.

| Componente | Estado |
|---|---|
| **Legend IA** | integrado — vídeo entra, legenda e CTA queimados, download |
| **LP Builder — QA** | integrado — relatório e capturas em três viewports |
| **LP Builder — Preview** | integrado — servido pela camada autenticada, por dono |
| **LP Builder — Publicar / Rollback** | integrado — versionado, com rollback |
| **LP Builder — Publicação remota** | **somente quando um servidor estiver configurado.** Sem configuração, a interface informa isso e o preview continua acessível aqui dentro |
| **Diretor, Design IA, Revisor, Copywriter** | ainda não integrados |

Nenhuma integração é simulada: um agente só aparece como **DISPONÍVEL** quando existe uma
declaração de ferramenta para ele.

### Por que esses e não os outros

A [arquitetura aprovada](docs/arquitetura-web.md) parte de um fato do código: **nenhum dos
arquivos Python do repositório chama LLM.** Toda inteligência é Markdown executada pelo Claude
Code; todo Python é motor determinístico. Isso divide a Fase B em duas etapas:

- **Etapa 1 — sem consumo de LLM.** Os motores determinísticos rodam na web sem nenhuma chamada
  a modelo, e portanto **sem custo por token**. O Legend IA é o caso completo (transcrição é ASR
  local, não LLM) e o LP Builder entrou em seguida: QA, publicação, preview e rollback. Falta
  desta etapa a inspeção técnica de vídeo e o render do Design IA.
- **Etapa 2 — runtime de inteligência.** Diretor de Operações, Copywriter, o parecer do Revisor,
  a direção de arte e a **construção** da LP dependem de um modelo raciocinando. Essa etapa
  acrescenta um worker com o Claude Agent SDK, que carrega os `SKILL.md` e os agentes deste
  repositório sem reescrita.

**A Fase B inteira não é gratuita.** A Etapa 1 é, e entrega valor real hoje. A Etapa 2 tem custo
por token, e a decisão de ligá-la fica adiada até existir medição — o plano de medir está na
seção 11 de [`docs/arquitetura-web.md`](docs/arquitetura-web.md).

---

## Como adicionar novo agente

1. `agents/<nome>/agents/<nome>.md` — o prompt do agente, com frontmatter `name` e `description`.
2. Skills próprias em `agents/<nome>/skills/<skill>/SKILL.md`; motor em `agents/<nome>/engine/`.
3. Registre as capabilities em `agents/diretor-operacoes/REGISTRY.md` — sem isso o Diretor não o
   enxerga, e inventar dono de tarefa é proibido.
4. Adicione o symlink em `scripts/setup.sh` e a verificação em `scripts/check.sh`.
5. Documente o componente neste README.
6. Commit único com prompt, REGISTRY, scripts e README juntos.

## Como atualizar agentes

Edite no repositório, commite e `git push`. Nas outras máquinas:

```bash
git pull && bash scripts/setup.sh && bash scripts/check.sh
```

O Revisor de Arte é plugin e tem passo próprio — suba a `version` em
`agents/revisor-arte/.claude-plugin/plugin.json` e, na máquina do usuário:

```bash
claude plugin marketplace update squad-legend-ai
```

---

## Troubleshooting

| Sintoma | Causa provável | Correção |
|---|---|---|
| Skill `lp-*` ou `designer-ia` não aparece | symlink não criado | `bash scripts/setup.sh` |
| `Agent(diretor-de-operacoes)` não existe | `~/.claude/agents/` sem o symlink | `bash scripts/setup.sh` |
| Render da peça falha sem erro claro | Playwright/Chromium ausente | `pip install playwright && python3 -m playwright install chromium` |
| Render falha com `libnspr4.so` / `libnss3.so` | libs do Chromium ausentes no host | `bash scripts/chromium-libs.sh` — resolve com ou sem root |
| `revisor.py locate` não acha nada | plugin não instalado | `claude plugin install revisor-de-criacao@squad-legend-ai` ou exporte `DESIGNER_REVISOR_HOME` |
| Legend IA: `ffmpeg not found` | FFmpeg ausente | `sudo apt install ffmpeg` |
| Legend IA: `No module named faster_whisper` | venv não montado | `bash scripts/setup.sh` |
| Legenda sai fora de lugar em vídeo vertical | metadado de rotação | já tratado; confirme o ffprobe do arquivo |
| Preview publicado não abre para outra pessoa | `base_url` é `localhost:8090` | preencha o bloco `remote` do `publish.conf.json` |
| Ingestão do Drive não acha nada | conector Google Drive desconectado | reconecte o conector na conta claude.ai |
