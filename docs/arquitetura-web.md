# Squad NK na web — diagnóstico de runtime e arquitetura

**Atualizado em 2026-09-15.** Substitui a versão preliminar escrita durante a migração para o
GitHub. Aquela versão concluía que a única saída era API paga; esta investiga o código real,
a documentação oficial e o hardware disponível antes de concluir qualquer coisa.

A Fase A terminou: os componentes estão versionados e um clone limpo reconstrói e executa
todos eles. Isso preserva o **código**. Não torna nada web.

Objetivo da Fase B: um funcionário abre o navegador, faz login e usa o Squad — sem Claude
Code, terminal, WSL, Git ou script.

**Nada aqui foi implementado.** Este documento é diagnóstico e arquitetura.

---

## 1. O fato que decide a arquitetura inteira

```
grep -rniE "anthropic|openai|messages\.create|chat\.completions|litellm|langchain|ollama|gemini" \
     --include='*.py' . | grep -v venv/
→ zero ocorrências
```

**Nenhum dos 13 arquivos Python do repositório chama LLM.** Toda a inteligência vive em
Markdown — `SKILL.md`, os `.md` dos agentes, a base de `conhecimento/` — e é executada hoje
pelo Claude Code. Todo Python é motor determinístico.

Isso tem duas consequências:

1. **Os seis componentes têm exatamente a mesma forma**: instruções em Markdown + ferramentas
   `Bash`/`Read`/`Write` + motores Python. Só existe **uma** peça a substituir — o runtime.
   São seis agentes, **uma** integração.
2. **Todo handoff entre inteligência e motor é um arquivo em disco com formato fixo**:
   `art-direction.json`, `brief.vN.json`, `handoff.vN.md`, `DESIGNER-ACOES`, `index.json`, a
   tabela de três trilhas do Copywriter. Nenhum desses contratos passa por memória de sessão.
   Portanto **quem produz o arquivo é substituível**: hoje é o Claude Code; pode ser um
   formulário; pode ser o Agent SDK. O motor a jusante não sabe a diferença.

---

## 2. Mapa: onde termina o agente e começa o motor

| Componente | Inteligência | Motor próprio | Precisa LLM? | Vira web sem LLM? |
|---|---|---|---|---|
| **Legend IA** | traduzir pedido em flags | `process_video.py` + FFmpeg + faster-whisper | **não** | 🟢 **inteiro** |
| **LP Builder** | escrever o HTML, curar fotos, julgar o QA | `drive_ingest.py`, `lp_qa.py`, `publish.py` | sim, para construir a página | 🟡 QA, publicação e ingestão sim; construir não |
| **Design IA** | direção de arte, foto, tipografia, copy da peça | 9 módulos + Chromium | sim, para decidir | 🟡 render/validate/autofix sim |
| **Revisor de Arte** | julgar, dar nota e status | 2 shell scripts (ffprobe, loudness, frames) | sim | 🟡 só a medição técnica |
| **Diretor de Operações** | rotear por capability, montar jobs | nenhum | sim | 🔴 não |
| **Copywriter** | escrever, classificar claims A/B/C | nenhum | sim | 🔴 não |

### Legend IA — o caso limpo

A skill lê o pedido e emite **uma linha de comando**. Sem artefato intermediário, sem loop.
`faster-whisper` é ASR local (transcrição), não LLM: roda offline e não decide nada.

Trocar a skill por um formulário com dropdowns é tradução de 1 para 1 — e a interface fica
**melhor** que o LLM, porque `--preset`, `--cta-position` e `--text-position` já são `choices`
do argparse. Não há ambiguidade a traduzir.

### Design IA — a fronteira é um arquivo com schema

```
LLM → art-direction.json
  → job.py new --ad          (+ brand.snapshot.json)
  → artdirection.py compile  → brief.vN.json
  → job.py render            → vN.png + vN.report.json + validate.vN.txt
  → selfcheck.py             → fatos, sem veredito
  → job.py review            → handoff.vN.md
  → [Revisor]                → review-vN.md, terminando no bloco DESIGNER-ACOES
  → LLM classifica as ações
  → autofix.py apply         → brief.v(N+1).json
  → job.py render --version N+1 …
```

Teto de **3 ciclos imposto em código** (`agents/design-ia/engine/job.py:37,212`), não por boa
vontade do prompt. As 13 correções do `autofix.py` têm teto numérico cada uma, e as
`BLOQUEADAS` estão enumeradas. **Este é um agente já desenhado para ser operado por máquina —
a parte difícil está feita.**

### LP Builder — a lacuna mais séria

**Não existe motor que construa a LP.** O HTML é escrito linha a linha pelo LLM. O
`lp_qa.py` mede o que tem número e imprime, no próprio output, o que não mede:

> *"foco na oferta, claims sustentados, prova junto da promessa, naturalidade, ritmo visual,
> teste anti-genérico e autocrítica final: olhe as capturas e decida."*

### Revisor, Diretor e Copywriter — prompt puro

Revisor: 468 linhas de agente + 1.062 de conhecimento + 4 skills. Copywriter: 480 linhas de
Master Prompt + 4 skills. Diretor: roteamento por capability via `REGISTRY.md`. Zero código
para portar, e nenhum atalho sem LLM.

---

## 3. O que funciona sem LLM — custo de token: zero

| Entrega | Como | Cobertura |
|---|---|---|
| **Legend IA completo** | upload do MP4, preset em dropdown, campos de CTA/texto/headline | **100%** |
| **QA de Landing Page** | URL → `lp_qa.py --json` → métricas + 3 capturas | 100% do que ele mede |
| **Publicar / rollback / listar LP** | `publish.py publish/rollback/ls` | 100% |
| **Inspeção técnica de vídeo** | `inspecionar-video.sh` → loudness EBU R128, blackdetect, cortes, frames | 100% |
| **Ingestão de acervo** | `map → rank → triage → screen` roda sozinho | ~85% |
| **Render do Design IA** | briefing por formulário → `compile → render → validate → selfcheck` | ~60% |

### O humano na cadeira do LLM

Em decisões pontuais, um funcionário na interface faz o mesmo papel que o LLM faz hoje — e
faz melhor, porque é o dono do cliente. Isso não é degradação; é devolver a decisão a quem
tem contexto. São os **gates**:

| Gate | Onde | O funcionário faz | Vira |
|---|---|---|---|
| `keywords` | `drive_ingest rank` | três campos: alta / média / ruído | `--alta --media --ruido` |
| `pick_from_sheet` | `drive_ingest fetch` | grid clicável sobre `sheet.jpg`, com os índices que o próprio `montar()` já desenha | `--pick 3 7 12` |
| `choose_fixes` | `autofix apply` | checkboxes de `autofix.py list`, com as `BLOQUEADAS` travadas | `--fix X --fix Y` |
| `paste_markdown` | `job.py save-review` | cola o parecer terminando em `DESIGNER-ACOES` | stdin do `save-review` |
| `checklist` | `lp_qa` | os 7 itens que o script declara não verificar | registro no histórico |

`waiting_human` é um **estado de primeira classe** do job, não gambiarra: o job para, mostra o
artefato, espera o clique e continua.

---

## 4. O que exige LLM, e por quê

| Precisa | Por quê |
|---|---|
| Construir a LP | não existe motor; a página é escrita linha a linha |
| Direção de arte (`art-direction.json`) | conceito, leitura da fotografia, escolha tipográfica, copy da peça |
| Parecer do Revisor | nota, status, classificação em 5 classes, grau de confiança |
| Copy (as 4 capabilities) | escrita + classificação A/B/C de claims |
| Orquestração do Diretor | roteamento por capability, dependências, *message match* |
| Classificar `DESIGNER-ACOES` | o que é autofix, o que é decisão criativa, o que para |

Duas capacidades aparecem repetidamente e não têm substituto determinístico: **olhar uma
imagem e julgar** ("esta foto tem legenda embutida de outra campanha", "esta peça parece
montada") e **classificar afirmações por procedência** (A/B/C). São o núcleo do valor do Squad.

### O que se perde evitando LLM

Sem inteligência, o Squad Web é uma boa caixa de ferramentas; com ela, é o Squad. Perde-se:
a construção de LP (o entregável de maior valor), a direção de arte — o motor renderiza
igual, mas a peça fica **genérica**, que é exatamente o que a skill `lp-design-review` foi
escrita para matar —, o parecer do Revisor, a copy inteira junto com a trava A/B/C que impede
publicar afirmação sem lastro, e o roteamento do Diretor.

---

## 5. Runtime — os quatro cenários

### A. Claude Code remoto com a assinatura existente

**Existe e é documentado.** `claude setup-token` gera um token OAuth de **1 ano**, exposto
como `CLAUDE_CODE_OAUTH_TOKEN`, criado para *"CI pipelines, scripts, or other environments
where interactive browser login isn't available"*. Autentica com a assinatura e exige plano
Pro, Max, Team ou Enterprise. É o 5º na ordem de precedência de credenciais.

**Limitações do `setup-token`, e por que ele não serve como backend multiusuário:**

1. **Bloqueio técnico documentado.** *"It can only make model requests, so it can't establish
   Remote Control sessions or **fetch claude.ai connectors**."* O conector Google Drive do
   claude.ai não existe nesse modo — e é por ele que o `drive-baixar.sh` do Revisor recebe
   arquivo hoje.
2. **É uma assinatura individual.** Cinco funcionários trabalhando através de um token pessoal
   é compartilhamento de conta em substância. A Anthropic vende **Claude for Teams** exatamente
   para isso, com seats e billing centralizado. E a documentação do Agent SDK afirma que a
   Anthropic não permite que desenvolvedores terceiros ofereçam login ou limites do claude.ai
   dentro de seus produtos.
3. **Limite de uso é por conta.** Cinco pessoas disputam a mesma janela de rate limit. Dois
   jobs longos em paralelo travam o time inteiro.
4. **Bare mode não lê esse token** — `--bare` só aceita `ANTHROPIC_API_KEY` ou `apiKeyHelper`.
5. **Expira em um ano** e a renovação exige um navegador.

**Veredito: não.** Não por ser impossível, mas por ser frágil, contratualmente inadequado e
tecnicamente quebrado justamente no ponto de entrada de dois componentes.

### B. LLM open-source no nosso próprio servidor

Hardware real medido: **i7-12700H (20 threads), RTX 3060 Laptop com 6 GB de VRAM, RAM do WSL
capada em 7,6 GB, 942 GB livres.** É um laptop — a mesma máquina que a Fase B precisa poder
desligar.

Em 6 GB de VRAM cabem modelos de ~7-8B quantizados em Q4. O trabalho aqui é seguir uma
hierarquia de instruções de 1.500+ linhas, classificar claims por procedência, produzir um
`art-direction.json` válido contra schema, e **julgar imagens**. Um 8B quantizado não faz isso
de forma confiável, e a parte visual exige um multimodal competente, que não cabe nesses 6 GB.

**Veredito: não.** Falta de capacidade por uma ordem de grandeza, não questão de otimizar.

### C. API externa (Anthropic)

Preços vigentes, por milhão de tokens:

| Modelo | Input | Output |
|---|---|---|
| Claude Opus 5 | $5 | $25 |
| Claude Sonnet 5 | $2 | $10 |
| Claude Haiku 4.5 | $1 | $5 |

Batch API: 50% de desconto. **Cache de prompt: leitura a 0,1× do input** — muito relevante
aqui, porque os prompts do Squad são grandes e **estáveis**: o Master Prompt do Copywriter e a
base de conhecimento do Revisor não mudam entre jobs. É o caso de uso ideal de cache.

É o único caminho oficialmente suportado para servir várias pessoas a partir de um servidor.
**Não adotado agora**, por decisão do dono do projeto.

### D. Híbrido — o adotado

Motores determinísticos rodam sem LLM; o LLM é acionado só onde há raciocínio.

**Ressalva honesta:** o híbrido reduz o *volume* de chamadas, não as torna gratuitas. A perna
de inteligência do cenário D **é** o cenário C. O que ele entrega de verdade é (a) valor real
em produção sem gastar token nenhum e (b) a decisão de custo adiada até haver número medido.

### Quadro comparativo

| | A — Claude Code remoto | B — LLM local | C — API | D — Híbrido |
|---|---|---|---|---|
| **Viabilidade** | técnica sim, contratual não | não (hardware) | sim | sim |
| **Custo adicional** | zero | zero (energia) | por token | zero na Etapa 1 |
| **Complexidade** | baixa | alta | média | média |
| **Qualidade** | alta | **inaceitável** | alta | alta |
| **Manutenção** | token anual; quebra em conector | alta | baixa | baixa |
| **Risco** | **alto** | alto | baixo | baixo |

---

## 6. Runtime único compartilhado — o Claude Agent SDK

O Claude Agent SDK (`@anthropic-ai/claude-agent-sdk` / `claude-agent-sdk`) é o Claude Code
empacotado como biblioteca: ele traz o laço do agente, as ferramentas embutidas
(`Read`/`Write`/`Edit`/`Bash`/`Glob`/`Grep`), gerenciamento de contexto, subagentes,
permissões e sessões. **Você hospeda; ele não hospeda nada por você.**

**O ponto que torna a migração barata está confirmado na documentação oficial:** o SDK carrega
as skills do filesystem.

```python
options = ClaudeAgentOptions(
    cwd=REPO,                              # raiz do Squaud-nk
    setting_sources=["project"],           # carrega .claude/skills e .claude/agents do repo
    skills="all",
    allowed_tools=["Read", "Write", "Bash", "Skill"],
)
```

- Skills são descobertas em `.claude/skills/<nome>/SKILL.md` a partir do `cwd` e diretórios pais.
- Subagentes vêm da opção `agents` ou de `.claude/agents/`.
- Despacho direto por `/<nome>` no prompt.
- A mensagem `system/init` lista as skills carregadas — dá para confirmar em runtime.

**Os prompts e as skills deste repositório rodam sem reescrita.** É por isso que "seis agentes"
é uma integração, não seis.

### Um worker, seis agentes

**Um.** O `cwd` é o mesmo repositório para todos; as skills vêm do mesmo filesystem; a
diferença entre os seis é qual subagente é despachado. Seis processos seriam seis cópias do
mesmo carregador de skills em 7,6 GB de RAM. A concorrência vem de N sessões dentro do mesmo
processo, sob o mesmo teto de slots dos motores.

`setting_sources: ["project"]` **sem** `"user"` é deliberado: o comportamento tem de ser
reprodutível a partir do commit, não do que houver no home do servidor. É a regra 3 do
`CLAUDE.md` aplicada ao runtime.

### Jobs longos e a regra do subagente

Dentro de uma sessão, o Diretor aciona três especialistas como subagentes e a sessão roda até
o fim. O que não funciona é voltar a falar com um subagente depois do turno. Logo: **todo
ponto de intervenção humana quebra a cadeia em jobs separados** — e a quebra é grátis, porque
o handoff já é arquivo:

```
job A (agent)  → art-direction.json
job B (motor)  → compile + render + validate + selfcheck + review → v1.png, handoff.v1.md
job C (agent)  → review-v1.md com DESIGNER-ACOES
gate choose_fixes: humano confere o que o agente classificou
job D (motor)  → save-review + autofix apply + render v2
```

O teto de 3 ciclos continua onde está, em `job.py`. O worker chama `can-continue` e obedece.
**Não duplicar regra de negócio no web** — é a diferença entre um MVP que evolui e um que
diverge do motor.

### Os dois contratos que precisam de validador antes da Etapa 2

- **`art-direction.json`** — o "schema" em `agents/design-ia/engine/artdirection.py:123-173` é
  uma string comentada, não um validador. Campo errado cai em default silencioso; o próprio
  código admite isso no comentário sobre `DOMINANCE_ALIASES`. Derivar um JSON Schema real e
  validar **antes** de `job.py new --ad`; falhou, devolve o erro ao agente, no máximo 2
  tentativas.
- **`DESIGNER-ACOES`** — o agente **não** invoca `autofix.py`; emite JSON estrito que o runner
  valida contra `autofix.py list` e contra a constante `BLOQUEADAS`. Nome inventado é
  rejeitado antes de virar comando.

### Teto de custo — quatro camadas

1. `max_turns` por agente no SDK.
2. Orçamento por usuário/dia no banco, verificado **antes** de enfileirar.
3. Timeout de relógio que mata a sessão (rede pendurada não consome turno e consome hora).
4. **Kill switch global**: uma linha de config faz todo job `producer: agent` nascer `blocked`.
   No dia em que a conta sair errada você quer um interruptor, não um deploy.

---

## 7. Arquitetura MVP — Docker Compose portátil

O desenho tem de subir igual no laptop, num PC velho ou numa nuvem gratuita. Por isso
containerizado desde o início: rodar nativo custa menos agora e cobra depois em "funciona na
minha máquina" — exatamente o problema que a Fase A eliminou.

### Quatro serviços. Só.

| Serviço | O quê | Por que existe |
|---|---|---|
| `web` | FastAPI + Jinja2, HTML no servidor, zero build de frontend | funcionário precisa de navegador, não de SPA |
| `worker` | consome a fila e executa os motores como subprocesso | job de vídeo leva minutos; não cabe num request |
| `lp-serve` | `publish.py serve --port 8090`, **sempre atrás do `web`** | já existe, já é threaded, já barra path traversal |
| `tunnel` | exposição pública | sem IP fixo |

A Etapa 2 acrescenta **um**: `agent-worker`.

- **Banco: SQLite em WAL.** Não Postgres — um host, um dev, sem multi-tenancy, dezenas de jobs
  por dia. Postgres traria container, backup e senha em troca de nada.
- **Fila: uma tabela, não um broker.** `BEGIN IMMEDIATE` + poll de 1s. Sem Redis, sem Celery.
- **Resultado volta por SSE** (`GET /jobs/{id}/events`): transições de status + tail do
  `job.log`. Não WebSocket (tráfego unidirecional); não polling puro (o funcionário precisa
  ver movimento durante 6 minutos de ffmpeg).

### Chaves de concorrência são obrigatórias

Chromium headless consome 0,4–1 GB; `faster-whisper base` int8, 1–2 GB; ffmpeg satura os 20
threads. Em 7,6 GB de RAM: global 2, `chromium` 1, `whisper` 1, `ffmpeg` 1. Dois renders
simultâneos matam o host por OOM antes de qualquer outra coisa.

### Imagem do container

As dependências do Chromium já estão resolvidas no repositório — `scripts/chromium-libs.sh`,
`shared/runtime/lib`, e a injeção de `LD_LIBRARY_PATH` que `render.py` e `lp_qa.py` fazem.
Duas exigências na imagem: `libnss3 libnspr4 libatk1.0 libcups libdrm libxkbcommon libgbm
libasound2`, e **`--shm-size=1g`** (Chromium com `/dev/shm` de 64 MB trava em página longa).

**Incerteza registrada:** em host ARM64, as wheels de `ctranslate2`/`faster-whisper` precisam
de teste antes de qualquer promessa.

### Isolamento de dados sem tocar nos motores

Os três motores vazam caminho de formas diferentes. Cada um tem um truque distinto, **todos
verificados por execução**:

| Motor | Como resolve | Verificação |
|---|---|---|
| **LP Builder** | lançar o processo com `HOME=$SQUAD_DATA_HOME/home` | `publish.py:18` e `drive_ingest.py:17` usam `os.path.expanduser('~/...')`, que respeita `$HOME`. Testado: com `HOME` trocado, a raiz muda. **Zero mudança de código** |
| **Design IA** | apontar os symlinks `engine/{clients,jobs,output}` para `$SQUAD_DATA_HOME/art-builder/` | `HOME` não ajuda: `job.py:34` usa `Path(__file__).resolve().parent`, e `.resolve()` segue o symlink. Os symlinks reversos do `setup.sh` são o único ponto de controle |
| **Legend IA** | estagiar o upload **dentro** de `apps/legend-ia/entrada de vídeo/`, carimbado com o `job_id` | `resolve_video_path()` rejeita caminho fora de `PROJECT_ROOT` |

```
$SQUAD_DATA_HOME/
  db.sqlite
  jobs/<job_id>/{input,out,job.log}
  home/.claude/lp-builder/{previews,clients,publish.conf.json}   # HOME dos processos LP
  art-builder/{clients,jobs,output}                              # alvo dos symlinks
  repo/                                                          # clone de trabalho
```

### Motor declarado como dado, não como endpoint

Um YAML por ferramenta. **Nenhum endpoint por motor.** Adicionar ferramenta = escrever um
YAML; nenhum Python, nenhum HTML.

```yaml
id: legend.editar
label: "Legend IA — legendar e finalizar vídeo"
capability: video.edicao          # amarra no REGISTRY.md
concurrency_key: whisper
timeout_s: 2400
steps:
  - id: run
    producer: form                # na Etapa 2 vira "agent" — e só isso muda
    exec: { cwd: apps/legend-ia, argv: ["venv/bin/python", "process_video.py", "{{video}}"] }
    stage: [{ from: input.video, to: "entrada de vídeo/{{job_id}}-{{filename}}", bind: video }]
    inputs:
      - { name: preset, type: enum, options: [classic, editorial, impact], flag: --preset }
      - { name: subtitles, type: bool, flag_true: --subtitles, flag_false: --no-subtitles }
      - { name: cta, type: text, flag: --cta }
      - { name: textos, type: repeat, flag: --text }     # cobre action="append"
    collect: [{ glob: "entrega/{{job_id}}-*_final.mp4", kind: video, primary: true, move_to: out/ }]
```

Três templates Jinja genéricos cobrem todas as ferramentas: `tool_form.html`, `job.html`,
`history.html`. O fluxo INPUT → EXECUTAR → STATUS → RESULTADO → HISTÓRICO é literalmente
`tool_form → POST /jobs → job.html (SSE) → artefatos → history`.

### Por que a Etapa 2 não refaz a Etapa 1

```
Etapa 1:  formulário HTML ──┐
                            ├──► art-direction.json ──► [runner determinístico] ──► PNG
Etapa 2:  agente (SDK)   ───┘
```

Um passo ganha o campo `producer`, que vale `"form"` ou `"agent"`. Na Etapa 2 cada gate ganha
`auto_by: <agente>` e **o widget continua existindo** — vira a tela onde o funcionário vê o que
a IA decidiu e pode discordar. É isso que impede a Etapa 2 de virar caixa-preta.

---

## 8. Hospedagem

### O que existe hoje

Varredura completa: config de SSH, `known_hosts`, histórico do bash, `~/.docker/contexts`,
`~/.aws`, `~/.azure`, `~/.cloudflared`, workflows, Makefiles, `nginx.conf`, systemd.

| Recurso | Situação |
|---|---|
| VPS / servidor | **não existe** |
| Conta Cloudflare / túnel nomeado | **não existe** — `~/.cloudflared/` ausente; os 8 logs usam só `*.trycloudflare.com`, efêmero |
| Domínio próprio | **não existe** — o único que aparece é `seudominio.com.br`, placeholder |
| Docker | Docker Desktop no Windows, integração WSL desligada; nenhum context remoto |
| AWS / Azure / GCP / Oracle | pastas vazias ou ausentes; nenhuma credencial |
| GitHub | repositório privado + Actions no plano gratuito |
| **VPS previsto** | `publish.py` **já implementa** publicação por `rsync`+SSH; o bloco `remote` existe e está **vazio** |

O caminho para servidor já está codado. Falta o servidor.

### Alternativas

| Opção | Custo real | Exige | Veredito |
|---|---|---|---|
| **Máquina própria + quick tunnel anônimo** | R$ 0 | nada; já é o que se usa hoje | URL muda a cada reinício. Serve para desenvolver, não para operar |
| **Máquina própria + túnel nomeado** | **domínio ~US$ 10/ano**; Cloudflare Free + Tunnel + Zero Trust Access (até 50 usuários): R$ 0 | registrar domínio e apontar nameservers | **Recomendado.** URL estável, HTTPS, e o **Access resolve o login no edge** — devolve ~4 h de cronograma e remove uma superfície de segurança inteira |
| **Nuvem de plano gratuito permanente** (ex.: Oracle Free Tier, ARM 4 vCPU / 24 GB) | R$ 0 de fatura, **mas exige cartão cadastrado** | cadastro, aprovação (às vezes negada no Brasil), migração | Mais RAM que o WSL e sempre ligado. Contra: **ARM64** (wheels de `faster-whisper` a testar), sem GPU, e instâncias gratuitas ociosas já foram recuperadas pelo provedor |
| **PaaS de plano gratuito** (Render, Fly, Railway) | **não é gratuito para isso** | — | Descartado: sem disco persistente no tier free, hibernação por ociosidade, 512 MB de RAM, e job de 6 min de ffmpeg estoura o limite de request. É a opção que **parece** grátis e não é |

**O que não é gratuito, explicitamente:** domínio (~US$ 10/ano, único desembolso recomendado);
tokens da API, se a Etapa 2 for adiante; plano Pro/Max/Team, que o `setup-token` exige como
pré-requisito; qualquer nuvem, mesmo "free tier", pede cartão; IP fixo, e-mail transacional e
backup fora da máquina.

**Enquanto o host for o laptop de desenvolvimento, a Fase B não se cumpre:** máquina desligada,
time parado.

---

## 9. Riscos

| Risco | Gravidade | Mitigação |
|---|---|---|
| **`lp-serve` expõe a carteira inteira de clientes** — a porta 8090 serve todos os previews **sem autenticação** e a raiz lista os slugs. Hoje está atrás de um túnel efêmero; com URL estável vira vazamento de carteira | **alta** | nunca expor 8090 direto — proxiar pelo `web` com sessão, exceto rotas explicitamente marcadas como públicas |
| **Colisão de saída do Legend IA** — `process_video.py:579` grava `entrega/{stem}_final.mp4`; dois funcionários subindo `01.mp4` sobrescrevem o vídeo um do outro | média, concreta | carimbar o nome do arquivo de entrada com o `job_id`. Subpasta não resolve, porque o nome de saída usa só o `stem` |
| **Corrida do `$JOB`** — incidente documentado em `designer-ia/SKILL.md:242-257`: `save-review` gravou parecer alheio e `finalize` publicou peça errada marcada como aprovada | some por construção | o job dir vira coluna de banco; não há variável de shell para atropelar. Guarda extra de 4 linhas: conferir `client`/`name` do `job.json` antes de `save-review` e `finalize` |
| **Conector Google Drive não existe fora do claude.ai** | certeza, não risco | `drive-baixar.sh` morre no produto web → upload de arquivo. Mas `drive_ingest.py` **sobrevive**: não usa conector, usa pasta pública. Requisito novo para o cliente: compartilhar como "qualquer pessoa com o link" |
| **RAM de 7,6 GB no WSL** | média | chaves de concorrência; aumentar o limite no `.wslconfig` é grátis, o laptop tem mais RAM física |
| **Dados de cliente** | alta | tudo sob `SQUAD_DATA_HOME`, fora do git; o `.gitignore` já barra `**/clients/`, `**/previews/`, `**/jobs/`, `entrega/`, `*.mp4` |

---

## 10. Correções pendentes herdadas da Fase A

### `LEGEND_WHISPER_MODEL` está no `.env.example` e nunca é lido

`apps/legend-ia/process_video.py:46-47` fixa `WHISPER_MODEL = "base"` e
`WHISPER_DEVICE = "cpu"`. A variável foi declarada no `.env.example` durante a migração e
promete um controle que o código não oferece. **Corrigir: ou o código passa a ler a variável,
ou a variável sai do exemplo.** Enquanto isso não for feito, o `.env.example` mente.

### A RTX 3060 está ociosa

A máquina tem RTX 3060 Laptop com 6 GB de VRAM e passthrough CUDA ativo no WSL
(`/dev/dxg`, `libcuda.so` em `/usr/lib/wsl/lib`). O Whisper roda em CPU por constante
hardcoded. Com `device="cuda"` e o modelo `large-v3`, a transcrição ficaria melhor e mais
rápida — são ~6 linhas.

Duas ressalvas: é mudança de motor, e o ganho **some** se o host virar nuvem sem GPU. Por isso
o caminho certo é ler `LEGEND_WHISPER_MODEL` e um `LEGEND_WHISPER_DEVICE` do ambiente, com
fallback para `base`/`cpu` — assim a mesma imagem serve os dois hosts. Fora do escopo do MVP.

---

## 11. Plano de medição real de tokens e custo

A decisão da Etapa 2 não deve ser tomada por estimativa. **Dá para ter número sem contratar
nem gastar nada:**

1. Rodar **os jobs reais do dia a dia** no Claude Code que já é pago — trabalho próprio, conta
   própria, uso normal da assinatura. Nenhum piloto, nenhuma chave nova.
2. Extrair dos transcripts de sessão, gravados localmente, os tokens de **entrada, saída e
   cache** de cada job.
3. Multiplicar pelas tarifas publicadas: Opus 5 $5/$25, Sonnet 5 $2/$10, Haiku 4.5 $1/$5, com
   leitura de cache a 0,1× do input.
4. Reportar custo medido **por tipo de entrega**: peça de design, landing page, roteiro,
   parecer de revisão, copy de anúncio. Com e sem cache, e com Opus e Sonnet lado a lado.

Isso é medição do que já acontece, não experimento pago. Saem números por entregável, e a
decisão da Etapa 2 passa a ser aritmética em vez de fé.

**Estimativa: 4 a 6 h.** Deve ser feito **antes** de qualquer linha de código da Etapa 2.

---

## 12. Recomendação

Descartados, com motivo:

- **Cenário A** — assinatura individual servindo cinco pessoas, limite de uso compartilhado e,
  decisivo, sem conector do claude.ai, que é a porta de entrada de dois componentes.
- **Cenário B** — 6 GB de VRAM num laptop que precisa poder desligar. Falta de capacidade por
  uma ordem de grandeza.
- **Cenário C puro** — funciona, mas não é preciso adotar para começar.

### Adotado: Cenário D, em duas etapas, com o Claude Agent SDK como a única camada de inteligência

1. **A Etapa 1 entrega valor real com custo zero de token** e não é trabalho jogado fora: o
   runner, a fila, o histórico, os formulários, os gates e a autenticação são os mesmos na
   Etapa 2.
2. **A Etapa 2 é uma integração, não seis.** O SDK carrega os `SKILL.md` e os agentes do
   próprio repositório, sem reescrita — confirmado na documentação oficial.
3. **O repositório já foi escrito para isso sem saber**: todo handoff é arquivo com formato
   fixo, o teto de ciclos está em código, o `autofix` tem teto numérico por correção e as
   decisões bloqueadas estão enumeradas.
4. **A decisão de custo fica adiada até existir número medido**, e o kill switch a torna
   reversível num arquivo de config.

### Cronograma

**Etapa 1 — ~138 h** (esqueleto, fila e SSE, registry de ferramentas, runner, autenticação,
histórico, Legend IA, LP QA, LP publish, LP ingestão, Design IA, inspeção de vídeo, Docker,
deploy, testes, folga). Ordem: esqueleto → Legend IA completo → LP publish/QA → Design IA →
ingestão.

**Etapa 2 — ~136 h** (agent-worker, captura de artefatos e tetos, credencial, validador do
`art-direction.json`, contrato do `DESIGNER-ACOES`, Design IA ponta a ponta, Revisor,
Copywriter, construtor de LP, Diretor, observabilidade de custo, ajuste de prompts, folga).

**Total ~274 h**, cerca de 7 semanas úteis para um desenvolvedor, sem paralelismo.

*Incerteza declarada:* o schema do `brief.json` do caminho não-AD do Design IA não foi
verificado campo a campo. Se exigir engenharia reversa dos 5 templates, **+4 a 8 h**.

---

## 13. Critério de aceitação da Etapa 1

Cada item tem de passar **a partir de um navegador, numa máquina sem Claude Code**:

1. `docker compose up` sobe os quatro serviços a partir de um clone limpo; `scripts/check.sh`
   continua verde.
2. **Legend IA** — upload de MP4, preset, CTA → MP4 final tocando na tela. Dois funcionários
   subindo `01.mp4` ao mesmo tempo recebem **dois vídeos distintos**.
3. **LP QA** — URL → métricas + 3 capturas + checklist salvo no histórico.
4. **LP publish** → URL estável abre; `rollback` volta a versão. A porta 8090 **não** responde
   de fora do proxy.
5. **Ingestão** — link de pasta pública → contact sheet na tela → clicar 8 fotos → `fetch`
   baixa exatamente essas.
6. **Design IA** — briefing por formulário → PNG + relatório de `validate` e `selfcheck` →
   colar parecer → `choose_fixes` → v2. `can-continue` recusa o 4º ciclo.
7. **Inspeção de vídeo** — upload → loudness, blackdetect, cortes, galeria de frames.
8. **Isolamento** — nenhum arquivo novo em `git status` do clone; todo dado sob
   `SQUAD_DATA_HOME`.
9. **Concorrência** — 5 jobs pesados na fila; sem OOM e sem sobrescrita.
10. **Medição de custo** — o relatório de tokens por tipo de entrega existe e está no
    repositório.

A Etapa 2 só começa depois de 1–10 verdes e do número de custo na mão.
