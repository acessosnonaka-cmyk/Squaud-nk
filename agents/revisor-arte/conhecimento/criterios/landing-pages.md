# Régua — Landing Pages

**Tipo:** `landing-page`
**Usa nota:** sim
**Escala e faixas de status:** definidas em `regras-gerais.md` §1 — **não redefinir aqui**

Aplica-se a páginas de captura, vendas e campanha, entregues como **código-fonte**,
**screenshots** (desktop/mobile) ou ambos.

> **Existe navegador, e a captura é obrigatória.** Este aviso dizia o contrário até a LP
> da Academia Mergulho ser **aprovada sem ninguém ter visto a página**: sem screenshot, os
> critérios 6, 7 e 8 eram excluídos e renormalizados, e a página saiu com tarja amarela de
> debug sobre o H1 e sem uma única fotografia do cliente. A régua funcionou como escrita —
> a régua estava errada. Ver §0 e §3.

---

## 0. Antes de pontuar: abra a página

`engine/render.py` do LP Builder captura a página **inteira** em desktop (1440) e mobile
(390) e assina a captura contra o hash do arquivo. Toda LP do Squad chega com `render.json`.

```bash
python3 apps/lp-builder/engine/render.py verificar --manifesto <render.json>
```

1. **Rode `verificar` antes de olhar.** Se ele disser que a página mudou depois da captura,
   a captura não serve: peça a recaptura. Parecer sobre a versão anterior é parecer sobre
   uma página que não existe mais.
2. **Abra os dois PNG com `Read`.** Os dois, sempre. O rodapé quebrado no celular nunca
   apareceu numa captura de desktop.
3. **Nomeie no parecer o que você abriu** — caminho do `desktop.png` e do `mobile.png`. O
   gate do Diretor recusa parecer de LP que não cita a captura: parecer que não nomeia o
   que abriu é parecer sobre o HTML, e é assim que se aprova uma tarja de debug.

**Sem captura, o retorno é `BLOQUEADO`, não é parecer com critério excluído.** Esta é a
mudança que mais importa nesta régua: falta de screenshot **não** é mais motivo para
renormalizar peso. Se não há como ver a página, não há como dizer se ela presta — e dizer
"não pude ver" é a resposta honesta, com nota nenhuma.

Vale também o piso do LP Builder (`engine/suficiencia.py`): página com marca de debug, sem
imagem referenciada ou com mobile sem direção própria é **defeito**, não questão de gosto —
e já devia ter sido barrada antes de chegar a você. Chegou assim, reporte como falha
crítica de acabamento e diga que o piso não rodou.

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
² **Não é mais exclusão.** Legibilidade e consistência visual se avaliam na captura, e a
captura é obrigatória (§0). Sem ela o retorno é `BLOQUEADO` — a régua inteira fica de pé,
nada é renormalizado.
³ **Não é mais exclusão**, mesmo motivo: as duas larguras vêm no `render.json`.
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

## 3. Não avaliável nem com a captura

A captura resolve o que é **estático e visível**: composição, hierarquia, legibilidade,
consistência, acabamento, e a página inteira nas duas larguras. Resta o que só existe em
interação. Declarar em "Limitações", nunca pontuar, nunca reportar como falha:

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

> **Isto deixou de ser recomendação e virou pré-requisito:** a entrega chega com as duas
> capturas de página inteira, ou não é revisada. Ver §0.

---

## 4. Notas de calibração

- Página revisada **só por código** não é revisada: é `BLOQUEADO` por falta de captura
  (§0). A confiança "Média com critérios reduzidos" era o caminho pelo qual uma página que
  ninguém viu saía com nota — e saiu.
- Página revisada **só por screenshot** não permite avaliar links, formulário nem
  requisitos técnicos. Também dizer.
- Não penalizar escolhas de implementação (framework, nomes de classe, organização do
  CSS) — isso é Classe 5, e o revisor não é revisor de código.
