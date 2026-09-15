# Gestor de Tráfego

Agente de performance e aquisição do **Squad Legend AI**. Planeja, executa, analisa,
diagnostica, otimiza e reporta mídia paga — Meta Ads, Google Ads e TikTok Ads.

Não é um operador de plataformas. Pensa **negócio antes de plataforma**, encontra o
gargalo de aquisição com evidência e propõe a próxima melhor ação.

---

## Instalação

```bash
claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
claude plugin install gestor-de-trafego@squad-legend-ai
```

Os dois comandos são necessários, nesta ordem. Conferir com `claude plugin list`.

---

## Como usar

Em linguagem natural:

```
Use o Gestor de Tráfego para analisar a conta do cliente X. Segue o relatório do mês.
```

```
Use o Gestor de Tráfego: o CPL do cliente Y subiu 40% em duas semanas. O que aconteceu?
```

```
Use o Gestor de Tráfego para montar o planejamento de mídia do cliente Z.
```

Ele cobre: diagnóstico de conta nova, planejamento de campanha, análise e otimização,
criação e publicação, testes, escala, relatório executivo e acionamento do squad.

---

## Antes de colocar o agente para operar uma conta

A identidade do cliente ele já lê do squad (`brand.json` e a LP vigente) — não duplique
nada disso. O que falta é a memória de mídia, que fica **fora do git**:

```bash
DATA="${SQUAD_DATA_HOME:-$HOME/.squad-nk}"
mkdir -p "$DATA/trafego/clients/<slug>"
cp modelos/cliente/*.md "$DATA/trafego/clients/<slug>/"
```

| Arquivo | Para quê |
| --- | --- |
| `contexto.md` | Ticket, margem, CAC máximo, funil, objetivo, tracking, processo comercial |
| `guardrails.md` | Limites de autonomia: orçamento máximo, CPA/CAC máximos, o que ele executa sozinho |
| `historico.md` | Hipóteses, testes, vencedores, perdedores, feedback e aprendizados |

**Enquanto `guardrails.md` estiver vazio, toda alteração financeira exige sua aprovação.**
Essa é a trava principal: autonomia sem limite escrito é risco de orçamento, não
produtividade.

O `historico.md` é o que impede o agente de tratar cada análise como o primeiro dia da
conta e de repetir um teste que já falhou.

## O que você recebe

**Diagnóstico:**

```
GARGALO PRINCIPAL: criativo
EVIDÊNCIA: CTR caiu 28% em 14 dias, frequência subiu de 2,1 para 4,6,
           2 anúncios concentram 81% da entrega
IMPACTO: CPL +34% no período, ~R$ 4.200 de eficiência perdida no mês
AÇÃO: briefing de 3 novos ângulos para o Squad de Design
PRIORIDADE: ALTA
```

**Insight:**

```
INSIGHT: pagamos 30% mais por lead, mas a taxa de fechamento dobrou
EVIDÊNCIA: CPL R$ 62 → R$ 81 | fechamento 8% → 17% | CAC R$ 775 → R$ 476
IMPACTO: o CAC real melhorou 39% — a campanha que parece pior é a melhor
AÇÃO SUGERIDA: realocar verba da campanha A para a campanha B
PRIORIDADE: ALTA
```

E ainda: plano de campanha com tese, relatório executivo, briefing para o squad,
estrutura de teste e checklist de pré-publicação.

---

## Estrutura

```
agents/gestor-de-trafego.md      o agente: missão, método, regras e autonomia
skills/gestao-de-trafego/        fluxos A-H: assumir conta, planejar, analisar,
                                 publicar, testar, escalar, reportar, acionar squad
conhecimento/                    plataformas · marketing e negócio · diagnóstico de
                                 gargalos · métricas e atribuição · execução e
                                 guardrails · squad e handoffs
modelos/                         insight · relatório executivo · plano de campanha ·
                                 briefing · teste · checklist
modelos/cliente/                 contexto · guardrails · histórico (copiar por cliente)
```

---

## Posição no squad

Ele fecha o ciclo de aquisição, mas não faz o trabalho dos outros:

| Precisa de | Vai para |
| --- | --- |
| Copy de anúncio, headline, ângulo escrito | **Copywriter** (`copywriting.meta_ads`) |
| Criativo, peça de feed, story | **Design IA** (`design.peca_grafica`) |
| Vídeo, legenda, motion | **Legend IA** (`video.edicao`) |
| Landing page nova ou correção de página | **LP Builder** (`lp.implementacao`) |
| Julgar a peça pronta | **Revisor de Arte** (`revisao.visual`) |

Ele define o ângulo a testar, a métrica principal e o critério de sucesso — e depois mede
o que voltou. Roteamento completo em
[`../diretor-operacoes/REGISTRY.md`](../diretor-operacoes/REGISTRY.md).

---

## Limitações conhecidas

- **Não tem acesso nativo às plataformas.** Sem conector de Meta/Google/TikTok
  autorizado, ele analisa o que você fornecer (exports, prints, relatórios) e executa
  nada — apenas recomenda.
- **Atribuição.** Ele compara plataforma × GA4 × CRM quando os dados existem. Se só
  houver o número da plataforma, ele diz isso em vez de fingir precisão.
- **Qualidade de lead** depende de dado de CRM. Sem retorno comercial, CPL é o teto da
  análise e o CAC real fica fora de alcance.
- **Não produz peça criativa, copy de anúncio nem landing page** — gera o briefing, aciona
  o especialista e mede o resultado.
