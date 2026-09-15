# COPYWRITER — Squad Legend AI

Especialista estreito em escrita. Faz quatro coisas e recusa o resto.

| Capability | Entrega |
|---|---|
| `copywriting.script` | roteiro de vídeo, para ser falado |
| `copywriting.social` | copy de postagem de social media |
| `copywriting.meta_ads` | primary text, headline, description, copy do criativo, CTA, variações de ângulo |
| `copywriting.landing_page` | copy de Landing Page com um objetivo de conversão |

## Como acionar

Registrado como subagente em `~/.claude/agents/copywriter.md` (symlink para
`agents/copywriter.md`, que é a fonte canônica). Em sessão nova ele aparece como tipo de agente
`copywriter` na ferramenta `Agent`.

Em sessão já aberta, ou por outro agente do squad, o padrão do squad funciona igual: abrir um
subagente e instruir a ler `~/projetos/copywriter/agents/copywriter.md` e assumir esse agente.

## Mapa

| Arquivo | O que é |
|---|---|
| `agents/copywriter.md` | **Master Prompt.** Define o cargo. Superior a qualquer skill |
| `capabilities.json` | as quatro capabilities, o fora-de-escopo e a Source of Truth |
| `PROCEDENCIA.md` | origem, commit e licença de cada skill; o que não foi instalado e por quê |
| `skills/ADAPTACOES.md` | como cada skill importada se submete ao Master Prompt |
| `skills/*/` | as quatro skills complementares (locais do agente, não globais) |
| `testes/` | validação da V1 |
| `entregas/<slug>/` | o que foi entregue, com a classe A/B/C de cada claim |

## Fronteiras

COPYWRITER escreve a mensagem. **LP Builder** constrói a página. **Design** decide fonte, cor,
grid e composição. **Legend AI** executa vídeo, motion e edição. **Gestor de Tráfego** (futuro)
cuida de campanha, orçamento, conjunto e segmentação. **Diretor de Operações** (futuro) define a
missão e recebe o que cai fora do escopo.

## Estado

V1. Funciona isoladamente. O Diretor de Operações e o roteamento global **não** foram alterados —
a conexão é a etapa seguinte.
