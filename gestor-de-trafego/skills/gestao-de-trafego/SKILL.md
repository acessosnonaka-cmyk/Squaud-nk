---
name: gestao-de-trafego
description: Esta skill deve ser usada sempre que houver trabalho de tráfego pago e performance — analisar conta ou campanha de Meta Ads, Google Ads ou TikTok Ads, diagnosticar queda de resultado, interpretar CPL, CPA, CAC, ROAS, CTR, CPM ou frequência, avaliar criativos e públicos, investigar qualidade de lead ou tracking, montar planejamento de mídia, criar e publicar campanha, estruturar teste, decidir escala ou pausa, e produzir relatório de performance. Traz o fluxo operacional passo a passo do Gestor de Tráfego.
---

# Gestão de Tráfego — fluxo operacional

Fluxo operacional do agente `gestor-de-trafego`. Em qualquer pedido, o método é sempre:

```
DADO → DIAGNÓSTICO → HIPÓTESE → AÇÃO → RESULTADO ESPERADO
     → EXECUÇÃO → MENSURAÇÃO → APRENDIZADO
```

E a hierarquia de análise é sempre **negócio → funil → mídia → elementos**.
Nunca otimize uma métrica inferior prejudicando uma métrica superior.

## Passo 0 — carregar contexto (sempre)

1. Localize a base de conhecimento do plugin:

```bash
BASE="${CLAUDE_PLUGIN_ROOT:-$(find "$HOME/.claude/plugins" -maxdepth 7 -type d -name conhecimento -path '*gestor-de-trafego*' 2>/dev/null | head -1 | xargs -r dirname)}"; echo "BASE=$BASE"
```

2. Leia, quando existirem no diretório de trabalho:
   `clientes/<cliente>/contexto.md`, `clientes/<cliente>/guardrails.md` e
   `clientes/<cliente>/historico.md`.

3. Só pergunte ao gestor humano o que **não** estiver nesses arquivos nem nos dados
   disponíveis. Cliente novo: copie `$BASE/modelos/cliente/` para `clientes/<cliente>/`.

## Fluxo A — assumir conta nova / diagnóstico inicial

1. Levantar o que falta de negócio, oferta, cliente, ticket, margem, funil, objetivo,
   histórico, plataformas, orçamento, tracking, ativos e comercial
   (checklist em `$BASE/conhecimento/marketing-e-negocio.md`).
2. Ler a estrutura atual e o desempenho por nível (campanha → conjunto → anúncio).
3. Rodar o mapeamento de gargalos (`$BASE/conhecimento/diagnostico-de-gargalos.md`).
4. Entregar situação atual, gargalo principal, gargalos secundários, evidências,
   prioridades (crítico/alto/médio/baixo) e plano de ação.
5. Preencher `contexto.md` e abrir o `historico.md` do cliente.

## Fluxo B — planejar campanha

Toda campanha nasce de uma **tese**, não de uma plataforma. Ordem obrigatória:

```
NEGÓCIO → OBJETIVO → OFERTA → FUNIL → CONVERSÃO → TRACKING
→ PLATAFORMA → PÚBLICO → CRIATIVO → ESTRUTURA → ORÇAMENTO → MENSURAÇÃO
```

Entregue no formato de `$BASE/modelos/plano-de-campanha.md`.

## Fluxo C — analisar performance / otimizar

1. Contexto (Passo 0) + período e volume suficientes para separar sinal de ruído.
2. Leitura em cascata: negócio → funil → mídia → elementos.
3. Comparar com objetivo financeiro e histórico da conta — nunca com benchmark inventado.
4. Identificar gargalo principal e secundários, com evidência numérica.
5. Decidir manter, reduzir, pausar, testar ou escalar — cada decisão com hipótese e
   critério de verificação.
6. Executar o que estiver dentro dos guardrails; pedir aprovação do que estiver fora.
7. Registrar no `historico.md`.

Descoberta não óbvia vira insight no formato de `$BASE/modelos/insight.md`.

## Fluxo D — criar / publicar campanha

1. Plano aprovado (Fluxo B) e guardrails verificados.
2. Nomenclatura padronizada (`$BASE/conhecimento/execucao-e-guardrails.md`).
3. Rodar `$BASE/modelos/checklist-pre-publicacao.md` item a item antes de publicar.
4. Publicar e registrar data, hipótese e resultado esperado no histórico.

## Fluxo E — testar

Nenhum teste aleatório. Todo teste tem hipótese, variável, controle, versão teste,
métrica principal, métricas secundárias, critério de sucesso e período/volume mínimo.
Use `$BASE/modelos/teste.md` e consulte o histórico para não repetir teste fracassado
sem motivo novo.

## Fluxo F — escalar

Antes de escalar verifique estabilidade, volume de conversões, CAC, margem, qualidade de
lead, capacidade de atendimento, frequência, estoque e criativos disponíveis.
Não escale porque ontem foi bom.

## Fluxo G — reportar

Relatório existe para gerar decisão, não para decorar. Use
`$BASE/modelos/relatorio-executivo.md` e garanta resposta a: quanto investimos, que
resultado geramos, se estamos na meta, o que melhorou, o que piorou, por quê, qual o
maior gargalo, qual a maior oportunidade, o que fizemos e o que faremos agora.

## Fluxo H — acionar o squad

Gargalo fora da mídia? Acione o especialista com briefing completo
(`$BASE/modelos/briefing-squad.md`) e depois **meça o resultado da entrega**.
Mapa de destinos em `$BASE/conhecimento/squad-e-handoffs.md`.

---

## Regras que valem em todos os fluxos

- **Métrica sem contexto não é decisão.** Cruze custo, volume e qualidade.
- **Sem benchmark inventado.** Compare com objetivo financeiro, histórico da conta,
  períodos anteriores e campanhas semelhantes.
- **Sinal ≠ ruído.** Um dia ruim não derruba campanha.
- **Se está funcionando, não mexa sem motivo.**
- **Nunca ultrapasse limites financeiros silenciosamente.**
- **Dado insuficiente é uma resposta válida** — mas sempre acompanhada do que sabemos, do
  que falta, de como obter e da decisão temporária mais segura.
