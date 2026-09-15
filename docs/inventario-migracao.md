# Inventário da migração — 2026-09-15

Varredura real da máquina de origem (WSL2 Ubuntu, `/home/ffili`, com `/mnt/c` montado).
Nada foi apagado da máquina. Este documento registra de onde cada coisa veio.

## Os cinco componentes

| Componente | Origem na máquina | Tipo | Git próprio | Destino no repositório |
|---|---|---|---|---|
| LP Builder | `~/.claude/lp-builder/` + `~/.claude/skills/lp-*` | 3 scripts Python + 4 skills | não | `apps/lp-builder/` |
| Diretor de Operações | `~/projetos/squad/` | prompt + REGISTRY | não | `agents/diretor-operacoes/` |
| Design IA | `~/.claude/art-builder/` + `~/.claude/skills/designer-ia` | 9 módulos Python + 6 templates + skill | não | `agents/design-ia/` |
| Revisor de Arte | `~/projetos/revisor-de-criacao/` | plugin do Claude Code | **sim** | `agents/revisor-arte/` |
| Legend IA | `~/video-editor/` | pipeline Python + FFmpeg | sim (sem remote) | `apps/legend-ia/` |
| Copywriter *(6º, não pedido)* | `~/projetos/copywriter/` | prompt + 4 skills | não | `agents/copywriter/` |

### Nota sobre o repositório oficial

`acessosnonaka-cmyk/Squaud-nk` **já existia com conteúdo**: é o repositório
`revisor-de-arte` renomeado, com os 4 commits do Revisor de Criação v2.0.0.

O conteúdo foi movido com `git mv` para `agents/revisor-arte/`, preservado como rename —
histórico inteiro intacto, nada de force push, nada reescrito. O `marketplace.json` da raiz
passou a apontar `./agents/revisor-arte`, então o comando de instalação do plugin continua
funcionando.

O repositório local `~/projetos/revisor-de-criacao` e o remoto estavam no **mesmo commit**
(`d5349f3`) e sem alterações pendentes. Nada se perdeu.

---

## O que NÃO foi versionado, e por quê

| Item | Tamanho | Motivo |
|---|---|---|
| `~/.claude/lp-builder/clients/` | 19 MB | acervo de fotos de cliente (Arte Mineira) |
| `~/.claude/lp-builder/previews/` | 45 MB | LPs publicadas, versionadas pelo próprio motor |
| `~/.claude/art-builder/clients/` | 1,1 MB | `brand.json`, logos e referências de cliente |
| `~/.claude/art-builder/jobs/` + `output/` | 10 MB | rastro de produção de peças |
| `~/.claude/art-builder/runtime/lib/` | 4,5 MB | `.so` do Chromium (libnss3/libnspr4) — regenerável via apt |
| `~/video-editor/venv/` | 491 MB | dependência Python regenerável |
| `~/video-editor/entrada de vídeo/` + `entrega/` | 56 MB | material bruto e entregas |
| `~/projetos/revisor-de-criacao/revisoes/`, `validacao/`, `.tmp-drive/` | 2,5 MB | material de cliente, já no `.gitignore` original |
| `~/projetos/copywriter/entregas/` | vazio | pasta de trabalho |
| `~/.agents/skills/humanizer/` | 112 KB | skill MIT de terceiros — `setup.sh` clona do upstream |
| `~/.claude/*` (sessions, history, credentials, plugins/cache) | — | configuração pessoal e credenciais |
| `~/projetos/leadtrack`, `~/projetos/plane` | — | projetos sem relação com o Squad. `leadtrack` tem `.env` com segredo real; não foi tocado |
| `~/LP-*.html`, `~/*.zip`, `~/cf-*.log`, `~/*-lp/` | ~20 MB | entregas e logs soltos no home |

O `art-builder` recria `clients/`, `jobs/` e `output/` sozinho. O `lp-builder` recria
`clients/` e `previews/`. `setup.sh` garante que existam.

---

## Dependências ocultas encontradas

Classificação: 🟢 pode ficar local · 🟡 precisa ser reproduzível · 🔴 sem a máquina o agente não existe

| # | Dependência | Onde | Classe | Situação |
|---|---|---|---|---|
| 1 | `~/.claude/art-builder/*.py` fora de qualquer repositório | skill `designer-ia`, REGISTRY | 🔴 → 🟢 | resolvido: motor no repo, `setup.sh` religa por symlink |
| 2 | `~/.claude/lp-builder/*.py` fora de qualquer repositório | 4 skills `lp-*` | 🔴 → 🟢 | resolvido: idem |
| 3 | `~/.claude/skills/*` e `~/.claude/agents/*` só nesta máquina | Claude Code | 🔴 → 🟢 | resolvido: `setup.sh` |
| 4 | `~/projetos/squad/` e `~/projetos/copywriter/` sem git | Diretor, Copywriter | 🔴 → 🟢 | resolvido: versionados |
| 5 | `~/video-editor/` com git mas **sem remote** | Legend IA | 🔴 → 🟢 | resolvido: código no repo central |
| 6 | `~/.agents/skills/humanizer` (symlink de `~/.claude/skills/humanizer`) | todos | 🟡 | `setup.sh` clona de `blader/humanizer` |
| 7 | `revisor.py` varre `/mnt/c/Users/*/.claude/` | Design IA → Revisor | 🟡 | por desenho: descoberta com fallback, mais `DESIGNER_REVISOR_HOME` |
| 8 | `publish.conf.json` → `http://localhost:8090` | LP Builder | 🔴 para o time | preview só abre na máquina que publicou. Bloco `remote` existe e está vazio |
| 9 | `cloudflared` quick tunnel (`~/cf-*.log`) | publicação de LP | 🔴 | URL `trycloudflare.com` cai quando a máquina desliga; sem conta, sem garantia |
| 10 | `brand.json` com `"/home/ffili/arte-mineira-lp"` | Source of Truth da Arte Mineira | 🟡 | dado de cliente, não versionado; corrigir na próxima edição |
| 11 | `handoff.v*.md` com caminhos `/mnt/c/...` | rastro de jobs antigos | 🟢 | log histórico, não é código |
| 12 | `runtime/lib/*.so` injetados no Chromium | render do Design IA | 🟡 | `sudo apt install libnss3 libnspr4` resolve; está no Troubleshooting |
| 13 | Conectores claude.ai: Google Drive, Gamma, Canva, ClickUp | LP Builder, Revisor | 🟡 | ligados à **conta**, não à máquina; reconectar em outra máquina |
| 14 | `~/.claude/projects/-home-ffili/memory/` como Source of Truth (caminho da máquina de origem) | REGISTRY, Copywriter | 🟡 | memória do Claude Code, por usuário. Fica fora — é preferência pessoal |
| 15 | Docker Desktop sem integração WSL | — | 🟢 | nenhum dos cinco usa Docker |
| 16 | Chave SSH `id_ed25519_nonaka` com passphrase e sem acesso | git | 🟢 | o acesso ao repositório é pelo alias `github-revisor` |

Nenhum MCP server configurado (`mcpServers` vazio em `~/.claude.json`). Nenhum banco de dados.
Nenhum Dockerfile nos cinco componentes.

---

## Auditoria de segurança

| Verificação | Resultado |
|---|---|
| `.env` / `.env.*` nos cinco componentes | nenhum |
| Chaves de API, tokens, `sk-ant-`, `ghp_`, `AKIA`, `AIza`, `xox*` | nenhum, nem em arquivo nem no histórico git |
| Chaves privadas e certificados | nenhum no repositório (as chaves SSH ficam em `~/.ssh/`, não versionadas) |
| Cookies, sessões, service accounts | nenhum |
| Histórico dos 4 commits já no GitHub | varrido objeto a objeto — **limpo** |
| Dados privados de cliente | identificados e mantidos fora do git |
| Banco de dados real | nenhum nos cinco componentes |

`~/projetos/leadtrack/.env` contém segredo real, mas é de outro projeto e **não** entrou aqui.

Criados: `.gitignore` (cobre segredos, dados de cliente, caches e artefatos) e `.env.example`
(só nomes de variável, nenhum valor).
