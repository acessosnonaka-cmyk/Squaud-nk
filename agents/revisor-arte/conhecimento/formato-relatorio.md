# Formato dos Relatórios

Dois artefatos por revisão: **individual** (uma por entrega) e **consolidado**
(um por pasta/demanda).

## Local e nomenclatura

```
revisoes/<AAAA-MM-DD>-<slug-da-pasta>/
├── consolidado.md
├── 01-<slug-da-entrega>.md
├── 02-<slug-da-entrega>.md
└── dados/                     # saída bruta de ferramentas (ffprobe, frames)
```

Gravar **sempre dentro deste projeto**, nunca na pasta revisada — ela pode estar
sincronizada, compartilhada ou ser somente leitura. A centralização é o que permite,
depois, cruzar recorrência, responsável, tipo e evolução no tempo.

---

## 1. Relatório individual — MODO NORMAL

**Este é o padrão.** A profundidade do relatório acompanha a profundidade da inspeção.

O formato depende do **tipo de entrega**:

| Tipo | Formato |
|---|---|
| `criativo` aprovado (⭐⭐⭐⭐ ou ⭐⭐⭐⭐⭐) | §1.1 |
| `criativo` com ⭐⭐⭐ ou menos | §1.2 |
| `landing-page`, `video` e demais | §1.3 |

---

### 1.1 CRIATIVOS — ⭐⭐⭐⭐ ou ⭐⭐⭐⭐⭐ (APROVADO)

**Relatório de confirmação, não de cobrança.** A peça passou: o relatório registra o que
foi conferido e libera a publicação.

> **Proibido montar lista de alterações.** Peça aprovada não recebe pendência
> obrigatória. Observação opcional só entra se for realmente útil, e marcada como tal.
> Na ausência de algo útil a dizer, o bloco de observações simplesmente não existe.

```markdown
# Revisão — <nome da peça>

| | |
|---|---|
| **Arquivo** | `<arquivo>` (<dimensões>, <formato>) |
| **Tipo** | `criativo` |
| **Briefing** | Considerado / Não havia |
| **Data** | AAAA-MM-DD |

## ⭐⭐⭐⭐⭐ · APROVADO

## Avaliação

<2 a 4 linhas. O que a peça faz bem e por que está pronta para publicação.
Sem ressalva plantada, sem "porém" artificial.>

## Conferências

| Frente | Resultado |
|---|---|
| **Textual** | <o que foi transcrito e conferido; erros encontrados: nenhum> |
| **Visual** | <sem problemas com impacto observável; o que está bem resolvido> |
| **Técnica** | <ficha: dimensões, proporção, integridade; sem problema identificado> |

## Observações opcionais

<Só se houver algo genuinamente útil. Marcar como **opcional — não é pendência**.
Se não houver, **omitir o bloco inteiro**.>

## Confiança: <Alta | Média>

<Uma linha.>
```

---

### 1.2 CRIATIVOS — ⭐⭐⭐ ou menos

**Toda correção obrigatória tem de estar amarrada a uma evidência concreta e a uma das
bases A–F** de `criterios/criativos.md` §3. Sem isso, a peça não deveria ter saído de 4
estrelas.

```markdown
# Revisão — <nome da peça>

| | |
|---|---|
| **Arquivo** | `<arquivo>` (<dimensões>, <formato>) |
| **Tipo** | `criativo` |
| **Briefing** | Considerado / Não havia |
| **Data** | AAAA-MM-DD |

## ⭐⭐⭐ · <AJUSTES NECESSÁRIOS | REPROVADO>

## Motivo principal

<1 a 3 linhas: o que impede esta peça de receber 4 estrelas. Direto ao ponto.>

## Erros textuais

| O quê | Onde | Evidência | Base | Conf. |
|---|---|---|---|---|

<Ou: `Nenhum identificado.`>

## Problemas visuais

| O quê | Onde | Impacto observável | Evidência | Base | Conf. |
|---|---|---|---|---|---|

<Ou: `Nenhum identificado.`>

## Problemas técnicos

| O quê | Onde | Evidência | Base | Conf. |
|---|---|---|---|---|

<Ou: `Nenhum identificado.`>

## Correções necessárias

1. **[BLOQUEIA]** <ação> — evidência: <qual>
2. **[IMPORTANTE]** <ação> — evidência: <qual>
3. **[DESEJÁVEL]** <ação> — evidência: <qual>

## Observações opcionais

<Preferências e melhorias sem base A–F. **Não são pendência.** Omitir se não houver.>

## O que está bom

<Curto. O que não deve ser mexido na correção.>

## Confiança: <Alta | Média | Baixa>

<Uma linha.>
```

A coluna **Base** cita a letra de `criterios/criativos.md` §3 (A a F). Achado sem base
não entra nestas tabelas — vai para observações opcionais.

---

### 1.3 Demais tipos — nota 0–10 (enxuto)

Princípio: **tabela no lugar de prosa** sempre que a tabela for mais eficiente. Cada
conclusão aparece **uma única vez** — não repetir no resumo, no problema, na prioridade
e no feedback a mesma frase com outras palavras.

Limites orientativos, não rígidos: uma falha que realmente precise de explicação pode
passar do limite. O que não pode é passar por hábito.

```markdown
# Revisão — <nome da entrega>

| | |
|---|---|
| **Arquivo(s)** | `<arquivos>` |
| **Tipo** | `<tipo>` — Nível <n> da cascata |
| **Régua** | `criterios/<arquivo>.md` |
| **Briefing** | Ausente / `<arquivo>` (campos faltantes: <lista>) |
| **Responsável** | <ou "não informado"> |
| **Data** | AAAA-MM-DD |

## Status: <APROVADO | AJUSTES NECESSÁRIOS | REPROVADO> · Nota: <X,X>/10

<Uma linha, apenas se o status vier de falha crítica e não da nota.>

## Resumo executivo

<Até 5 linhas. O que foi pedido, o que veio, o que decide o status. Sem adjetivo vazio,
sem repetir o que as tabelas abaixo já dizem.>

## Falhas críticas

| Cód | O quê | Onde | Evidência | Conf. | Correção |
|---|---|---|---|---|---|

<Ou: `Nenhuma identificada.`>

## Nota por critério

| Critério | Peso | Nota | Observação |
|---|---|---|---|
| **Total** | **<soma>** | | **<X,X>/10** |

<Uma linha com os critérios excluídos e a renormalização aplicada.>

## Problemas encontrados

| Classe | Observação | Onde | Evidência | Ação recomendada | Conf. |
|---|---|---|---|---|---|

<Uma linha por observação. Coluna Classe usa: 1 ERRO OBJETIVO · 2 NÃO CONFORMIDADE ·
3 QUALIDADE · 4 RECOMENDAÇÃO · 5 SUBJETIVA. Ordenar da classe 1 para a 5.
Classe 3 acrescenta, abaixo da linha, uma frase única com o impacto na comunicação —
as demais três perguntas já estão nas colunas.
Classes 4 e 5 não reprovam e não derrubam nota; manter curtas.>

## Correções por prioridade

1. **[BLOQUEIA]** <ação>
2. **[IMPORTANTE]** <ação>
3. **[DESEJÁVEL]** <ação>

## O que NÃO precisa ser alterado

<Lista curta do que está resolvido e não deve ser mexido. Serve também como registro
dos pontos positivos — evita retrabalho e protege o que está bom.>

## Limitações

<Lista curta: o que não foi possível verificar, critérios excluídos, campos ausentes do
briefing que tiveram impacto real. Só o que muda a leitura do parecer.>

## Confiança: <Alta | Média | Baixa>

<Uma linha com o que sustenta ou reduz.>

## Feedback para o responsável

<150 a 300 palavras. Pronto para copiar e encaminhar. Sem códigos internos de falha,
sem jargão de revisor. Diz o que mudar, por quê, e o que está bom. Critica o material,
nunca a pessoa.>
```

### O que sai no enxuto

Ficam **apenas** no modo profundo: a separação das classes em cinco blocos narrativos,
a tabela de aderência ao briefing requisito a requisito, o bloco de pontos positivos em
prosa e o detalhamento longo de limitações. Nada disso decide uma aprovação — por isso
sai do padrão e volta sob demanda.

**Nada é perdido em rigor:** as 5 classes continuam obrigatórias (agora como coluna),
a nota por critério continua completa, as falhas críticas continuam com evidência e
confiança, e as limitações continuam declaradas.

---

## 2. Relatório individual — MODO PROFUNDO (completo)

Usado apenas quando a revisão inteira rodou em modo profundo. Todos os 16 blocos são
obrigatórios. Bloco sem conteúdo é preenchido com `Nenhum identificado.` ou
`Não aplicável.` — **nunca omitido**.

```markdown
# Revisão — <nome da entrega>

| | |
|---|---|
| **Arquivo(s)** | `<arquivos que compõem a entrega>` |
| **Tipo identificado** | `<tipo>` — detectado por: <nível e sinal da cascata> |
| **Régua aplicada** | `criterios/<arquivo>.md` |
| **Responsável** | <do briefing, ou "não informado"> |
| **Cliente / Campanha** | <do briefing, ou "não informado"> |
| **Data da revisão** | AAAA-MM-DD |

## Status

**<APROVADO | AJUSTES NECESSÁRIOS | REPROVADO>**

**Nota: <X,X> / 10**

<Se o status vier de falha crítica e não da nota, dizer isso explicitamente.>

## Resumo executivo

<3 a 6 linhas. O que foi pedido, o que foi entregue, o que decide o status.
Sem adjetivo vazio. Quem ler só este bloco entende a decisão.>

## Falhas críticas

<Formato de `falhas-criticas.md` §5: código, localização, evidência, confiança,
correção, base no briefing. Ou: `Nenhuma identificada.`>

## Erros objetivos
*(Classe 1 — fatos verificáveis, não discutíveis)*

- **<o quê>** — `<onde>` — evidência: <como foi verificado> — confiança: <grau>

## Não conformidades com o briefing
*(Classe 2 — contraria algo escrito)*

- **<o quê>** — briefing pede: "<citação literal>" — entregue: <o que veio> — `<onde>`

## Problemas de qualidade
*(Classe 3 — exige as 4 perguntas)*

- **<título>** — `<onde>` — confiança: <grau>
  - Problema: <o que é>
  - Por quê: <por que é problema>
  - Impacto: <efeito na comunicação>
  - Correção: <como resolver>

## Recomendações
*(Classe 4 — não está errado; funcionaria melhor. Não reprova, não derruba nota.)*

## Avaliação subjetiva
*(Classe 5 — preferência de direção criativa, declarada como tal. Nunca reprova.)*

## Pontos positivos

<O que está bem executado, com especificidade. Obrigatório — parecer só com
defeito é parecer incompleto.>

## Nota por critério

| Critério | Peso | Nota | Contribuição | Observação |
|---|---|---|---|---|
| <critério> | <n> | <X,X> | <calc> | <justificativa curta> |
| **Total** | **<soma considerada>** | | **<X,X>/10** | |

<Listar critérios excluídos por não serem verificáveis e a renormalização aplicada.>

## Correções por prioridade

1. **[BLOQUEIA]** <correção que destrava a entrega>
2. **[IMPORTANTE]** <correção de impacto real>
3. **[DESEJÁVEL]** <melhoria opcional>

## O que NÃO precisa ser alterado

<Explícito. Evita retrabalho e protege o que está bom de mexida desnecessária.>

## Aderência ao briefing

| Requisito do briefing | Situação | Evidência |
|---|---|---|
| <requisito literal> | Atendido / Parcial / Não atendido / Não verificável | <como> |

<Sem briefing: declarar em destaque que este bloco não pôde ser preenchido e que o
critério foi excluído do cálculo (`regras-gerais.md` §4.2).>

## Limitações da análise

<O que não foi possível verificar e por quê. Campos ausentes no briefing.
Critérios excluídos do cálculo. Formatos não legíveis. Ferramentas indisponíveis.>

## Grau de confiança

**<Alta | Média | Baixa>** — <o que sustenta ou reduz a confiança global>

## Feedback para o responsável

<Bloco pronto para copiar e encaminhar. Direto, objetivo, sem jargão de revisor
e sem os códigos internos de falha. Diz o que mudar e por quê. Reconhece o que
está bom. Educado e impessoal — critica o material, nunca a pessoa.>
```

---

## 3. Relatório consolidado

**Sempre gerado**, sem exceção: um por pasta/demanda, inclusive quando há uma única
entrega e inclusive quando a entrada foi um arquivo individual. É ele que alimenta a
série histórica; sem ele a revisão não entra na base.

O formato depende de **quantas entregas** a demanda tem.

---

### 3.1 UMA entrega — consolidado MÍNIMO

Com uma só entrega, o consolidado é um **índice**, não um segundo parecer.
**Não repetir o relatório individual** — nem resumo, nem problemas, nem feedback.

```markdown
# Consolidado — <demanda / campanha, ou nome da entrega se desconhecida>

| | |
|---|---|
| **Demanda / Campanha** | <ou "não informada"> |
| **Pasta revisada** | `<caminho>` |
| **Data** | AAAA-MM-DD |
| **Entregas** | 1 |

| Entrega | Tipo | Avaliação | Status | Confiança | Relatório |
|---|---|---|---|---|---|
| <nome> | <tipo> | <⭐⭐⭐⭐ ou X,X> | <status> | <grau> | [`<arquivo>.md`](<arquivo>.md) |

## Bloqueios

<Só os códigos e o que trava, em uma linha cada. Ou: `Nenhum.`>

## Prioridades principais

1. **[BLOQUEIA]** <ação>
2. **[IMPORTANTE]** <ação>

*Entrega única: recorrência, consistência entre entregas e panorama por tipo não se
aplicam. O parecer completo está no relatório individual.*
```

Mais o bloco YAML de metadados (§3.3), que é obrigatório em qualquer consolidado.

---

### 3.2 DUAS OU MAIS entregas — consolidado COMPLETO

Aqui o consolidado tem papel próprio: é a **visão da campanha**, e traz o que nenhum
relatório individual pode trazer — comparação, consistência, recorrência, panorama e
prioridade global.

#### 3.2.a Criativos — distribuição de estrelas

Quando houver entregas do tipo `criativo`, o panorama usa **distribuição**, nunca média.

> **Proibido calcular média decimal de estrelas.** "3,67 estrelas" é falsa precisão:
> sugere uma resolução que a escala não tem. Distribuição informa; média inventa.

```markdown
## Distribuição — criativos

| | Qtd | Peças |
|---|---|---|
| ⭐⭐⭐⭐⭐ | <n> | <nomes> |
| ⭐⭐⭐⭐ | <n> | <nomes> |
| ⭐⭐⭐ | <n> | <nomes> |
| ⭐⭐ | <n> | <nomes> |
| ⭐ | <n> | <nomes> |

**Aprovadas (4–5★): <n> de <total>.**
```

#### 3.2.b Recorrências — duas listas separadas

**Estas duas listas nunca se misturam.** Promover preferência estética recorrente a
defeito comprovado é o erro mais fácil de cometer num consolidado — e o mais caro, porque
transforma gosto do revisor em pauta de correção para o squad.

```markdown
## Problemas recorrentes comprovados

<Apenas achados com base A–F, presentes em 2 ou mais entregas. Cada linha diz em
quantas peças aparece e qual a base. Ou: `Nenhum.`>

| Recorrência | Base | Peças | Evidência |
|---|---|---|---|

## Oportunidades recorrentes observadas

<Padrões sem base A–F: preferências, melhorias possíveis, escolhas que se repetem.
**Não são defeito. Não geram correção obrigatória. Não reduzem estrelas.**
Servem como insumo de conversa com o squad. Ou: `Nenhuma.`>

| Observação | Peças | Por que pode valer a pena |
|---|---|---|
```

#### 3.2.c Formato completo

Demais blocos abaixo.

```markdown
# Consolidado — <nome da demanda / pasta>

| | |
|---|---|
| **Pasta revisada** | `<caminho informado>` |
| **Data da revisão** | AAAA-MM-DD |
| **Responsável** | <do briefing, ou "não informado"> |
| **Cliente / Campanha** | <do briefing, ou "não informado"> |
| **Entregas revisadas** | <n> |
| **Briefing** | Encontrado (`arquivo`) / Ausente / Incompleto (campos faltantes: ...) |

## Veredicto da demanda

**<APROVADO | AJUSTES NECESSÁRIOS | REPROVADO>**

<A demanda só é APROVADO se **todas** as entregas forem APROVADO.
O veredicto acompanha a entrega em pior situação.
Para criativos, APROVADO significa todas as peças em ⭐⭐⭐⭐ ou ⭐⭐⭐⭐⭐.>

## Entregas

| # | Entrega | Tipo | Avaliação | Status | Falhas críticas | Relatório |
|---|---|---|---|---|---|---|
| 01 | <nome> | <tipo> | <⭐⭐⭐⭐ para criativo · X,X para os demais> | <status> | <n> | [`01-<slug>.md`](01-<slug>.md) |

## Bloqueios da demanda

<Toda falha crítica de todas as entregas, agrupada. Ou: `Nenhum.`>

## Problemas recorrentes

<Problemas que aparecem em mais de uma entrega — o sinal mais útil do consolidado.
Ex.: "Ortografia: 3 de 4 entregas". Ou: `Nenhum padrão identificado.`>

## Panorama por tipo

| Tipo | Entregas | Avaliação | Aprovadas | Ajustes | Reprovadas |
|---|---|---|---|---|---|

<Coluna "Avaliação": para `criativo`, a distribuição em estrelas (§3.2.a) — **nunca**
média. Para os demais tipos, a nota média em 0–10.>

## Consistência entre entregas

<Divergências entre peças da mesma demanda: cor, tom de voz, CTA, oferta, logo,
informação. Ou: `Consistente.`>

## Prioridade de correção da demanda

1. **[BLOQUEIA]** <entrega> — <correção>
2. **[IMPORTANTE]** <entrega> — <correção>
3. **[DESEJÁVEL]** <entrega> — <correção>

## O que já está aprovado

<Entregas e elementos que não devem ser mexidos.>

## Limitações da revisão

<Limitações que afetam a demanda inteira: briefing ausente/incompleto, formatos não
legíveis, ferramentas indisponíveis.>

## Grau de confiança global

**<Alta | Média | Baixa>** — <justificativa>

## Feedback consolidado

<Bloco pronto para encaminhar ao squad, cobrindo a demanda inteira.>

---
### 3.3 Metadados para calibração futura
*(Não editar manualmente. Base para análise de recorrência, qualidade por responsável,
qualidade por tipo e evolução no tempo.)*

```yaml
data: AAAA-MM-DD
pasta: "<caminho>"
responsavel: "<ou null>"
cliente: "<ou null>"
briefing_presente: true|false
briefing_campos_ausentes: []
entregas:
  - nome: "<nome>"
    tipo: "<tipo>"
    estrelas: <1 a 5, inteiro — apenas para tipo criativo; null nos demais>
    nota: <X.X — apenas para os tipos que usam 0-10; null para criativo>
    status: "<status>"
    falhas_criticas: []          # códigos, ex.: [C1, V2]
    criterios_excluidos: []
    confianca: "alta|media|baixa"
```
```

O bloco YAML é o que torna possível, depois, ler a série histórica sem banco de dados:
os relatórios acumulados em `revisoes/` são a base de dados do sistema.
