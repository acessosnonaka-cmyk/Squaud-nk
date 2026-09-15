# Regras Gerais — Núcleo Comum de Revisão

Vale para **todo** tipo de entrega, hoje e no futuro. Réguas especializadas
acrescentam critérios; nunca revogam este núcleo.

---

## 1. BLOCO CALIBRÁVEL

> **Este é o único lugar do projeto onde escala, faixas e confiança são definidos.**
> Nenhuma régua pode redefinir estes valores — todas apontam para cá.
> Para recalibrar o sistema inteiro, edite apenas esta seção.

### 1.1 Escala

Escala **0,0 a 10,0**, com uma casa decimal, para as categorias que usam nota numérica
(hoje: `landing-page` e `video`). Os **pesos** variam por régua; a escala e as faixas não.

> **Exceção declarada:** o tipo `criativo` usa escala de **estrelas inteiras (⭐ a
> ⭐⭐⭐⭐⭐)**, definida em `criterios/criativos.md` §2, e **não** usa as faixas de §1.2
> nem o cálculo ponderado de §4. Uma régua só pode divergir desta seção declarando a
> divergência explicitamente na própria régua, como aquela faz.

### 1.2 Faixas de status

| Nota final | Status |
|---|---|
| 8,5 a 10,0 | **APROVADO** |
| 7,0 a 8,4 | **AJUSTES NECESSÁRIOS** |
| abaixo de 7,0 | **REPROVADO** |

*Faixas iniciais, não calibradas. Serão ajustadas com material real de `calibracao/`.
Enquanto isso, tratar a nota como indicador, não como veredicto automático.*

### 1.3 Sobreposição por falha crítica

*Para o tipo `criativo`, o efeito da falha crítica é o de `criterios/criativos.md` §3.1
— a falha limita o teto de estrelas em vez de reprovar automaticamente.*

Para as demais categorias, a nota **não** é a única via para o status:

- Falha crítica **confirmada** → status **REPROVADO**, independentemente da nota.
  A nota continua sendo calculada e exibida (serve para calibração).
- Falha crítica **suspeita mas não confirmada** (confiança baixa) → status **no máximo
  AJUSTES NECESSÁRIOS**, com a suspeita declarada e o que falta para confirmar.

### 1.4 Graus de confiança

| Grau | Quando usar |
|---|---|
| **Alta** | Verificado diretamente: texto legível, dado medido por ferramenta, requisito escrito no briefing |
| **Média** | Inferido de evidência parcial: leitura de imagem em boa resolução, amostragem representativa |
| **Baixa** | Evidência insuficiente, amostral ou indireta. **Nunca sustenta uma reprovação sozinha.** |

A confiança é declarada por observação **e** consolidada no fim do relatório.

---

## 2. Classificação obrigatória das observações

Toda observação recebe exatamente uma destas classes:

| # | Classe | Definição | Discutível? |
|---|---|---|---|
| 1 | **ERRO OBJETIVO** | Fato incontestável e verificável: erro ortográfico, dado incorreto, arquivo corrompido, medida fora da especificação | Não |
| 2 | **NÃO CONFORMIDADE COM O BRIEFING** | Contraria algo **escrito** no briefing | Não |
| 3 | **PROBLEMA DE QUALIDADE** | Execução deficiente com impacto demonstrável na comunicação | Pouco |
| 4 | **RECOMENDAÇÃO / MELHORIA** | Funcionaria melhor assim, mas o atual não está errado | Sim |
| 5 | **AVALIAÇÃO SUBJETIVA** | Opinião de direção criativa, sem erro nem descumprimento | Sim |

Regras de uso:

- Classes **4 e 5 nunca reprovam** uma entrega e nunca reduzem nota de forma decisiva.
- Na dúvida entre 3 e 4, escolher **4**. O revisor erra para o lado permissivo.
- Na dúvida entre 3 e 5, escolher **5** e declarar que é preferência.
- Classe 3 exige impacto demonstrável. Se não conseguir explicar o impacto na
  comunicação, não é classe 3 — é classe 4 ou 5.

---

## 3. Núcleo comum de verificação

Aplicar a toda entrega, antes da régua especializada:

1. **Aderência ao briefing** — cada requisito escrito foi atendido?
2. **Completude** — tudo que foi pedido foi entregue? Falta formato, peça, variação?
3. **Informações obrigatórias** — dados, textos legais, contatos, datas, preços exigidos
4. **Erros objetivos** — ortografia, gramática, dado incorreto, inconsistência factual
5. **Consistência** — entre peças da mesma demanda e dentro da própria peça
6. **Identidade da marca** — só quando houver material de referência disponível
7. **Qualidade de execução** — acabamento, cuidado, profissionalismo
8. **Requisitos técnicos informados** — formato, dimensão, duração, peso, extensão
9. **CTA** — presente, correto e claro **quando aplicável ao pedido**
10. **Ortografia e textos** — todos os textos, inclusive os embutidos em mídia
11. **Impeditivos** — existe algo que impeça a entrega de ser publicada?

---

## 4. Cálculo da nota

```
nota_final = Σ (nota_do_critério × peso_do_critério) / Σ (pesos considerados)
```

### 4.1 Critérios condicionais e renormalização

Alguns critérios são marcados **(condicional)** na régua: só valem quando existe
evidência para avaliá-los.

Sem evidência, o critério é **excluído** do cálculo e os pesos restantes são
**renormalizados proporcionalmente**. Nunca atribuir nota arbitrária a um critério
não verificável, e nunca puni-lo com nota baixa por ausência de evidência.

> Exemplo: régua com 100 pontos onde "Responsividade (7)" é condicional e não há
> screenshot mobile. Soma considerada = 93. A nota é calculada sobre 93 e
> renormalizada para a escala 0–10. A exclusão é registrada em "Limitações da análise".

### 4.2 Ausência de briefing

> **Não se aplica ao tipo `criativo`.** Ali a ausência de briefing é a situação normal e
> **não** custa nota, estrelas nem confiança — ver `criterios/criativos.md` §1.1.

Para as demais categorias: sem briefing, o critério "Aderência ao briefing" é
**condicional não verificável**:
excluído e renormalizado. O relatório declara em destaque que a maior parte do
princípio central não pôde ser aplicada, e o grau de confiança global cai para
**no máximo Média**.

---

## 5. Postura do revisor

- **Não reprovar por preferência.** Divergência de gosto não é defeito.
- **Não inventar requisitos.** Não existe no briefing → não é cobrança.
- **Não afirmar sem verificar.** Declarar a incerteza é sempre preferível a inventar.
- **Reconhecer o que está certo.** Apontar o que está bom e o que **não** precisa mudar
  é parte obrigatória do parecer, não cortesia.
- **Toda crítica de qualidade responde 4 perguntas:**
  1. Qual é o problema?
  2. Por que é um problema?
  3. Qual o impacto na comunicação?
  4. Como poderia ser corrigido?
- **Nunca converter métrica técnica em juízo perceptivo.** Um dado técnico dentro da
  faixa prova conformidade técnica, não qualidade percebida.
- **Nunca inferir a origem ou o processo de produção da entrega.** Se a peça foi gerada
  por IA, feita à mão, montada em template ou produzida por qualquer ferramenta é
  irrelevante e não é verificável. O revisor avalia a entrega, não como ela foi feita.
  Recomendar uma verificação é sempre permitido; atribuir causa ou origem, nunca.
