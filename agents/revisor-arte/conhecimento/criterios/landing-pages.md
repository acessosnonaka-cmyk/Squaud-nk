# Régua — Landing Pages

**Tipo:** `landing-page`
**Usa nota:** sim
**Escala e faixas de status:** definidas em `regras-gerais.md` §1 — **não redefinir aqui**

Aplica-se a páginas de captura, vendas e campanha, entregues como **código-fonte**,
**screenshots** (desktop/mobile) ou ambos.

> **Limite estrutural desta fase:** não há navegador instalado. A página **não é
> renderizada**. Toda avaliação vem de leitura de código-fonte e/ou de screenshots
> fornecidos. Ver §3.

---

## 1. Pesos

| # | Critério | Peso | Condicional |
|---|---|---|---|
| 1 | Aderência ao briefing | 16 | sim¹ |
| 2 | Proposta de valor e mensagem | 13 | não |
| 3 | Estrutura e hierarquia | 12 | não |
| 4 | Copy | 11 | não |
| 5 | CTA | 11 | não |
| 6 | Legibilidade | 8 | sim² |
| 7 | Consistência visual | 8 | sim² |
| 8 | Responsividade | 7 | sim³ |
| 9 | Experiência e fluxo de leitura | 6 | não |
| 10 | Links e elementos funcionais | 4 | sim⁴ |
| 11 | Erros visuais, acabamento e requisitos técnicos | 4 | não |
| | **Total** | **100** | |

¹ Excluído se não houver briefing (`regras-gerais.md` §4.2).
² Excluído se **não houver screenshot** — não se avalia legibilidade nem consistência
visual lendo apenas CSS.
³ Excluído se não houver screenshot mobile **e** desktop. Com apenas código, dá para
verificar a **existência** de media queries / classes responsivas, mas não o resultado:
nesse caso o critério é excluído e a observação vai para Recomendações.
⁴ Excluído se não houver código-fonte — em screenshot, link não é verificável.

Exclusão sempre acompanhada de renormalização (`regras-gerais.md` §4.1) e registro
em "Limitações da análise".

---

## 2. O que avaliar em cada critério

### 1. Aderência ao briefing — 16
Objetivo da página atendido. Mensagem principal presente. Textos e elementos
obrigatórios presentes. Público coerente. Restrições respeitadas.

### 2. Proposta de valor e mensagem — 13
A primeira dobra responde "o que é, para quem, por que agora"? A promessa é clara e
específica? Há benefício, ou só descrição de característica?
*Ausência de proposta de valor na primeira dobra é falha crítica L3.*

### 3. Estrutura e hierarquia — 12
Sequência lógica das seções. Hierarquia semântica (`h1` único, `h2`/`h3` coerentes —
verificável no código). Densidade de informação por seção. Progressão até a conversão.

### 4. Copy — 11
Ortografia e gramática (Classe 1). Clareza e objetividade. Consistência de tom.
Ausência de placeholder (`lorem ipsum`, `TODO`, `xxx` → falha crítica L4).
Textos legais e obrigatórios presentes.

### 5. CTA — 11
Presente e destacado. Verbo de ação claro. Repetido ao longo da página quando o
comprimento justifica. Coerente com o CTA do briefing. **Destino válido** — `href`
preenchido e coerente (`href="#"` ou vazio é falha crítica L1). Formulário com `action`
e campos pedidos (falha crítica L2).

### 6. Legibilidade *(exige screenshot)* — 8
Contraste texto/fundo. Corpo de texto adequado. Largura de linha. Texto sobre imagem
com tratamento. Espaçamento entre blocos.
*Estimativa visual, confiança Média. Sem screenshot, excluir.*

### 7. Consistência visual *(exige screenshot)* — 8
Paleta, tipografia, espaçamentos e estilo de botões coerentes entre seções. Alinhamento
com a identidade da marca, quando houver referência disponível.

### 8. Responsividade *(exige screenshots desktop + mobile)* — 7
Layout adaptado sem quebra. Texto legível em mobile. Botões com área de toque razoável.
Imagens sem distorção. Ordem de conteúdo preservada.
*Com apenas código: registrar a **existência** de media queries/classes responsivas como
Recomendação, excluir o critério da nota e declarar que o comportamento real não foi
verificado. Nunca afirmar que a página é responsiva sem ver o resultado.*

### 9. Experiência e fluxo de leitura — 6
Caminho até a conversão sem obstáculo. Atrito desnecessário (excesso de campos, etapas,
informação fora de hora). Objeções antecipadas. Prova social, quando pedida no briefing.
*Avaliação estrutural, não comportamental — não há teste com usuário.*

### 10. Links e elementos funcionais *(exige código-fonte)* — 4
`href` preenchidos e plausíveis. Âncoras internas com destino existente. Imagens com
`src` válido e arquivo presente na pasta (`src` quebrado é falha crítica L5). Atributos
`alt`. Scripts e tags de rastreamento exigidos pelo briefing presentes.
*Verificação **estática**: existência e coerência. Não se testa se o link responde.*

### 11. Erros visuais, acabamento e requisitos técnicos — 4
Sobreposição, corte ou estouro visível em screenshot. Imagens esticadas. Elementos
desalinhados. Requisitos técnicos escritos no briefing (fontes, favicon, meta tags,
título da página, Open Graph) — verificáveis no código.

*Dimensão de screenshot e de imagens da pasta é medida, não estimada:*
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 <arquivo>
```
*Serve para confirmar que o screenshot mobile é de fato mobile antes de avaliar
responsividade com ele.*

---

## 3. Não avaliável nesta fase

**Não há navegador.** Declarar em "Limitações", nunca pontuar, nunca reportar como falha:

- renderização real da página;
- responsividade sem screenshots das duas larguras;
- hover, foco, animação, transição, scroll, menu, carrossel, acordeão;
- envio real de formulário e validação de campos;
- se um link **responde** (só se verifica se ele existe e para onde aponta);
- velocidade de carregamento, peso da página, Core Web Vitals;
- comportamento de JavaScript, conteúdo renderizado no cliente;
- acessibilidade além do que o HTML estático revela (`alt`, hierarquia, `label`);
- compatibilidade entre navegadores;
- SEO além das meta tags presentes no código.

**Página entregue apenas como URL:** o HTML pode ser buscado, mas **sem execução de
JavaScript** — páginas React/Next/Vue renderizadas no cliente retornam praticamente
vazias. Nesse caso, não concluir "página vazia": reportar como **não verificável** e
pedir código-fonte ou screenshots.

> **Recomendação operacional:** exigir do squad, junto da entrega, screenshots de
> desktop e mobile da página completa. Resolve a maior parte desta limitação sem
> instalar nada.

---

## 4. Notas de calibração

- Página revisada **só por código** tem no máximo confiança Média, e a nota sai de um
  conjunto reduzido de critérios — dizer isso no resumo executivo.
- Página revisada **só por screenshot** não permite avaliar links, formulário nem
  requisitos técnicos. Também dizer.
- Não penalizar escolhas de implementação (framework, nomes de classe, organização do
  CSS) — isso é Classe 5, e o revisor não é revisor de código.
