# Template — entregável visual de performance

Toda análise de performance sai em **duas peças**: o relatório executivo, que explica, e o
visual, que permite compreender e apresentar. Uma não substitui a outra e nenhuma das duas
é opcional.

O visual serve à **decisão**, não à decoração. Se um bloco não ajuda a decidir, ele sai.

## Qual dos dois

| | Quando |
| --- | --- |
| **Dashboard executivo** | há volume — várias métricas, períodos, campanhas, conjuntos, canais, comparações. O gestor vai **explorar**: filtrar, comparar, passar o mouse, procurar o porquê |
| **Infográfico executivo** | a análise é fechada e a resposta já é uma. O objetivo é comunicar rápido diagnóstico, evolução, gargalo e decisão, numa leitura linear |

A escolha é sua e não se pergunta ao gestor. Na dúvida entre os dois, pergunte-se o que ele
fará com a peça: se vai investigar, dashboard; se vai apresentar e decidir, infográfico.

## Blocos, quando o dado existir

Nunca invente métrica para completar gráfico. Indicador que a conta não entrega **sai da
peça ou aparece declarado como ausente** — nas duas formas, jamais preenchido por estimativa.

| Bloco | O que entra |
| --- | --- |
| **Identificação** | cliente, conta, período analisado, período comparado, data da extração, escopo (somente leitura ou com execução autorizada) |
| **Resultado do período** | investimento, resultados, custo por resultado (CPL/CPA), CAC e ROAS **só quando realmente calculáveis** |
| **Comparação** | o mesmo conjunto contra o período anterior, com a variação explícita |
| **Eficiência de mídia** | CTR, CPC, CPM e frequência quando forem relevantes para a decisão em pauta |
| **Evolução** | a curva dentro do período. Um total mensal costuma esconder a tendência que decide a próxima ação |
| **Melhores e piores** | campanhas, conjuntos, criativos e públicos, com o que separa um do outro |
| **Desperdício** | quanto foi investido sem resultado registrado, em valor e em percentual |
| **Gargalo** | qual é, com a evidência que o sustenta e o impacto |
| **Oportunidade** | o que está barato, o que está funcionando e comporta mais verba |
| **Recomendações** | em ordem de prioridade, e explicitamente **não executadas** quando dependem de autorização |

Métrica derivada mostra a conta que a gerou: quem lê precisa poder refazê-la.

## As quatro camadas continuam separadas no visual

A distinção vale na peça, não só no texto:

| Camada | Como aparece |
| --- | --- |
| **FATO** | número lido da conta, com a fonte e o período ao lado |
| **CÁLCULO** | derivado de fatos, com a fórmula ou os termos declarados |
| **HIPÓTESE** | rotulada como hipótese no próprio bloco — nunca com a mesma ênfase de um diagnóstico |
| **CONCLUSÃO** | o que decorre dos três acima, separada da recomendação que ela sustenta |

**Hipótese apresentada como diagnóstico confirmado é falha grave de entrega.** Um bloco que
mistura as camadas sem dizer qual é qual está errado, mesmo que bonito.

Toda ressalva que altera a leitura entra na peça, não só no relatório: janela de atribuição
ainda aberta, resultado abaixo do limite de privacidade, período incompleto, conta sem
tracking. Zero sem ressalva vira decisão errada.

## Padrão da peça

- **Limpa, executiva, legível.** Sem elemento que não carregue informação.
- **Responsiva** quando o formato permitir — ela vai ser aberta no celular.
- **Identidade do cliente** quando existir em `$DATA/art-builder/clients/<slug>/brand.json`:
  nome e cores da marca, desde que não prejudiquem legibilidade nem contraste. Legibilidade
  vence identidade; `restrictions` e `tone.avoid` valem aqui como em qualquer peça.
- **Nome do cliente sempre**, mesmo sem brand kit.
- **Rodapé com procedência:** fonte dos dados, data da extração e o que não foi alterado na
  conta.
- Gráfico serve ao número, não ao contrário: escala honesta, sem eixo duplo, sem truncar
  base para dramatizar variação.

## Fluxo

1. Termine a análise e o relatório executivo.
2. Escolha dashboard ou infográfico pelo critério acima.
3. Monte a peça só com o que a conta entregou.
4. Prosa que vai ao cliente passa pelo `Skill(humanizer)` antes.
5. Devolva **as duas peças** nos `artefatos` do `retorno.schema.json` — relatório e visual.
   Retorno de análise com um artefato só está incompleto.
