# Régua — <NOME DA CATEGORIA>

**Tipo:** `<slug-do-tipo>`
**Usa nota:** sim | não
**Escala e faixas de status:** definidas em `regras-gerais.md` §1 — **não redefinir aqui**

<Uma ou duas linhas: a que entregas esta régua se aplica, e a que não se aplica.>

> **Limite estrutural desta fase (se houver):** <o que o ambiente impede de verificar
> nesta categoria, e por quê.>

---

## 1. Pesos

Os pesos são livres e devem refletir o que importa **nesta** categoria. A soma precisa
fechar em 100. A **escala (0–10) e as faixas de status são comuns a todas as réguas** —
o que muda entre categorias são os pesos, nunca a escala.

| # | Critério | Peso | Condicional |
|---|---|---|---|
| 1 | Aderência ao briefing | <n> | sim¹ |
| 2 | <critério> | <n> | não |
| … | | | |
| | **Total** | **100** | |

¹ Excluído se não houver briefing (`regras-gerais.md` §4.2).
<Uma nota de rodapé para cada critério condicional, dizendo **exatamente** que evidência
ele exige e quando é excluído.>

Exclusão sempre acompanhada de renormalização (`regras-gerais.md` §4.1) e registro
em "Limitações da análise".

---

## 2. O que avaliar em cada critério

### <n>. <Critério> — <peso>
<O que observar, de forma acionável. Quando a avaliação for estimativa e não medição,
dizer aqui qual confiança declarar. Quando um item for falha crítica e não apenas nota
baixa, apontar o código em `falhas-criticas.md`.>

<Repetir para cada critério da tabela.>

---

## 3. Não avaliável nesta fase

<Lista explícita do que o ambiente **não** permite verificar nesta categoria.
Estes itens têm peso zero, nunca são pontuados, nunca viram falha crítica, e vão
integralmente para "Limitações da análise" do relatório.>

<Se a categoria tiver métricas objetivas obtidas por ferramenta, separe-as em
uma seção própria antes desta — como faz `videos.md` §2/§3 — e registre a regra:
métrica técnica nunca vira juízo perceptivo.>

---

## 4. Notas de calibração

- <Qual perfil de entrega **deve** aprovar nesta categoria.>
- <O que é Classe 5 aqui e, portanto, não derruba nota.>
- <Qual confiança global é realista para esta categoria.>

---

## Checklist para registrar a categoria

1. [ ] Este arquivo salvo como `criterios/<slug-do-tipo>.md`
2. [ ] Pesos somam 100
3. [ ] Critérios condicionais têm regra de exclusão explícita
4. [ ] §3 preenchida com honestidade — o que não dá para verificar está listado
5. [ ] Falhas críticas específicas acrescentadas em `falhas-criticas.md`
6. [ ] **Uma linha** acrescentada à tabela de `deteccao-de-tipo.md` §1, com os sinais
7. [ ] Sinais de detecção não conflitam com os das categorias existentes

Feito isso, a categoria está ativa. **O arquivo do agente não é alterado, e nenhuma outra régua
é alterada.**
