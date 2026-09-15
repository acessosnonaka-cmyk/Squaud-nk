# SQUAD NK

Repositório central do Squad Legend AI: cinco componentes de IA usados na operação da Nonaka ADS,
mais o Copywriter. Fonte da verdade do código e da configuração — o que não está aqui não existe.

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
| **Claude Code** 2.1.251+ | todos os cinco | sim — é o runtime |
| Python 3.11+ | LP Builder, Design IA, Legend IA | sim |
| Git | setup e plugin do Revisor | sim |
| FFmpeg + ffprobe (libx264, libass) | Legend IA; medição técnica do Revisor | sim para vídeo |
| Playwright + Chromium | render do Design IA, QA/screenshot do LP Builder | sim para arte e LP |
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

Falta o plugin do Revisor, que é manual (uma vez por máquina):

```bash
claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
claude plugin install revisor-de-criacao@squad-legend-ai
```

Dependências de sistema, se `check.sh` reclamar:

```bash
sudo apt install ffmpeg python3-venv
pip install playwright && python3 -m playwright install chromium
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

---

## Produção

Hoje não existe produção. Os cinco componentes rodam **na máquina de quem opera**, dentro do
Claude Code. O único artefato que sai para fora é o preview de LP:

- **padrão** — `python3 -m http.server 8090` sobre `~/.claude/lp-builder/previews/`, só local;
- **VPS** — preencha o bloco `remote` de `~/.claude/lp-builder/publish.conf.json` e a publicação
  passa a enviar por `rsync` + SSH, com URL pública estável e rollback por versão.

---

## Arquitetura Web

O plano para o time usar o Squad pelo navegador, sem terminal e sem WSL, está em
[`docs/arquitetura-web.md`](docs/arquitetura-web.md), com o que dá para reaproveitar, o que precisa
ser construído e onde aparece custo.

Resumo honesto: salvar os agentes no GitHub **não** os torna web. Todos dependem do Claude Code
como runtime. Tirar essa dependência exige um executor próprio chamando a API da Anthropic, e isso
tem custo por token. Não há caminho com custo zero para a Fase B.

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
| Render falha com `libnss3.so` | libs do Chromium ausentes no host | `sudo apt install libnss3 libnspr4` |
| `revisor.py locate` não acha nada | plugin não instalado | `claude plugin install revisor-de-criacao@squad-legend-ai` ou exporte `DESIGNER_REVISOR_HOME` |
| Legend IA: `ffmpeg not found` | FFmpeg ausente | `sudo apt install ffmpeg` |
| Legend IA: `No module named faster_whisper` | venv não montado | `bash scripts/setup.sh` |
| Legenda sai fora de lugar em vídeo vertical | metadado de rotação | já tratado; confirme o ffprobe do arquivo |
| Preview publicado não abre para outra pessoa | `base_url` é `localhost:8090` | preencha o bloco `remote` do `publish.conf.json` |
| Ingestão do Drive não acha nada | conector Google Drive desconectado | reconecte o conector na conta claude.ai |
