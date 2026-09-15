# Squad NK na web — diagnóstico e caminho

Fase A (código preservado e reconstruível pelo GitHub) está feita. Este documento trata da
Fase B: o time usar o Squad pelo navegador, com a máquina de origem desligada.

## Agente não é runtime

Um prompt salvo no GitHub não roda sozinho. Os cinco componentes são **instruções e motores**;
quem raciocina é um modelo, carregado hoje pelo Claude Code.

| | LP Builder | Diretor de Operações | Design IA | Revisor de Arte | Legend IA |
|---|---|---|---|---|---|
| **O que é** | 4 skills + 3 scripts Python | prompt de subagente + REGISTRY | skill + motor Python/Chromium | plugin (prompt + base de critérios) | script Python + FFmpeg |
| **Runtime** | Claude Code | Claude Code | Claude Code chama o Python | Claude Code | Python puro |
| **Modelo** | o da sessão do Claude Code | idem | idem (o Python não usa modelo) | idem | **nenhum** — Whisper local, sem LLM |
| **Interface atual** | linguagem natural no Claude Code | `Agent(diretor-de-operacoes)` | `Skill(designer-ia)` | linguagem natural + link do Drive | linha de comando |
| **Depende do Claude Code** | sim | sim | sim, para decidir; não, para renderizar | sim | **não** |
| **Web-ready** | 🔴 não | 🔴 não | 🟡 o motor sim, a decisão não | 🔴 não | 🟢 **sim** |

Só o Legend IA é uma aplicação de verdade: entra MP4, sai MP4, sem modelo de linguagem no meio.
Ele pode virar web hoje. Os outros quatro precisam de um executor de LLM.

## Infraestrutura que existe hoje

Varredura feita. O que há:

| Recurso | Situação |
|---|---|
| VPS / servidor próprio | **não existe** |
| Docker | Docker Desktop no Windows, com integração WSL **desligada**. Nenhum dos cinco usa |
| `cloudflared` | instalado, usado em modo *quick tunnel* sem conta — URL temporária, cai com a máquina |
| GitHub | repositório privado, com GitHub Actions no plano gratuito |
| Conta claude.ai | conectores Drive, Gamma, Canva, ClickUp |

Não há onde hospedar nada sem ligar a máquina de origem. O plano abaixo parte disso.

## O custo que não dá para esconder

Tirar a dependência da máquina significa um processo servidor que fala com um modelo. Duas formas,
e nenhuma delas é gratuita para um time:

1. **API da Anthropic** (`ANTHROPIC_API_KEY`) — cobra por token. É a única forma tecnicamente
   limpa de servir várias pessoas a partir de um servidor. Custo proporcional ao uso: cada job do
   Diretor que aciona três especialistas é uma sessão longa, com skills e base de critérios no
   contexto.
2. **Claude Code em modo headless** (`claude -p`) com a assinatura existente — funciona, mas a
   credencial é pessoal e de um usuário. Usar como backend multiusuário significa vários
   funcionários operando sob uma conta só; não é o uso previsto da assinatura e não escala.

**Não existe caminho com zero custo adicional para os quatro agentes que dependem de LLM.**
O que dá para fazer com custo zero está na Fase B1.

## Caminho recomendado, em três fases

### B1 — Custo zero, hoje

Sem executor de LLM. Entrega valor real e prova a arquitetura.

| Entrega | Como | Esforço |
|---|---|---|
| **Preview de LP com URL estável** | Cloudflare Tunnel **nomeado** (conta gratuita + domínio próprio) apontando para o `publish.py`, em vez do quick tunnel anônimo | 2–3 h |
| **Legend IA pela web** | app web mínimo (FastAPI + HTML) num container: upload do MP4, campo de CTA, fila simples, download do resultado | 2–3 dias |
| **Login do time** | autenticação básica por sessão, usuários em arquivo, sem banco | dentro do item acima |
| **Histórico** | SQLite num volume Docker | dentro do item acima |

Onde hospedar sem pagar: uma máquina *always free* de nuvem (ex.: Oracle Cloud Free Tier, 4 vCPU
ARM) roda o Legend IA e o preview de LP com folga. Não é contratação — é cadastro num plano
gratuito. **Requer decisão sua.** Enquanto não houver host, isso roda na máquina de origem e a
Fase B não se cumpre.

### B2 — Painel único, com custo de API

Aí sim os quatro agentes de LLM entram.

```
FUNCIONÁRIO → LOGIN → SQUAD NK WEB → escolhe o agente → fila → worker
                                                               │
                                              worker roda o agente via API
                                              (mesmos prompts e skills do repo)
                                                               │
                                                        resultado + histórico
```

**Uma aplicação só, três processos em Docker Compose:**

| Serviço | O quê | Reaproveita |
|---|---|---|
| `web` | FastAPI + HTML server-side. Login, escolha do agente, formulário, histórico, download | — |
| `worker` | consome a fila, monta o contexto lendo `agents/` e `skills/` **direto do repositório**, chama a API, executa os motores Python | 100% dos prompts, skills, critérios e motores |
| `db` | Postgres ou SQLite. Usuários, jobs, entregas | — |

**A ser desenvolvido:** login e sessão; fila de jobs; o *loader* que transforma um `SKILL.md` em
contexto de chamada de API; o laço de ferramentas (o worker precisa executar `render.py`,
`lp_qa.py`, `publish.py` quando o modelo pedir); tela de upload e de resultado.

Estimativa: **3 a 5 semanas** de desenvolvimento para um MVP com os cinco agentes.
Sem Kubernetes, sem mensageria dedicada, sem microserviço.

**Riscos.** O laço de ferramentas é a parte difícil — hoje quem executa `Skill(...)` e
`Agent(...)` é o Claude Code, e essa camada precisa ser reescrita. Jobs longos (o Diretor
acionando três especialistas) precisam de timeout e retomada. O conector de Google Drive do
claude.ai **não** existe fora do claude.ai: a ingestão de LP teria que usar a API do Google Drive,
com credencial própria (gratuita, mas é trabalho). Custo de token cresce com o uso e precisa de
teto por usuário.

**Limitações aceitas no MVP:** um job por vez por usuário; sem colaboração em tempo real; sem
edição visual da peça no navegador.

### B3 — Depois

Multiempresa, permissão por cliente, aprovação em duas etapas, integração com o ClickUp.
Só faz sentido com B2 em produção e uso medido.

## Resumo para decisão

| | Fase B1 | Fase B2 |
|---|---|---|
| Entrega | Legend IA + preview de LP na web | os cinco agentes na web |
| Custo adicional | **zero** (exige cadastro num plano gratuito de nuvem) | **token de API, proporcional ao uso** |
| Prazo | ~3 dias | 3–5 semanas |
| Máquina de origem pode desligar | sim, para esses dois | sim, para tudo |

Recomendação: fazer B1 primeiro. Prova a arquitetura, tira duas dependências da máquina e não
custa nada. B2 só depois de você decidir sobre o custo de API — e essa decisão é sua, não minha.
