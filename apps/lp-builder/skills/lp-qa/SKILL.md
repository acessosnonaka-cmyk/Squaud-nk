---
name: lp-qa
description: QA final obrigatório de Landing Page. Use SEMPRE antes de entregar qualquer LP ao usuário, depois de publicar o preview e antes de mandar o link. Roda checks automáticos e força a crítica que só o agente pode fazer.
---

# QA final — nenhuma LP é entregue sem passar por aqui

Regra: **não se entrega a primeira versão que funciona.** Entrega-se a versão que já passou
por crítica, compressão e correção. O QA é silencioso — o usuário recebe só o link e pendências reais.

## Parte automática

```
python3 ~/.claude/lp-builder/lp_qa.py <url> --out /tmp/lp-qa
```

Devolve número para: contagem de seções, CTAs e rótulos repetidos, microtítulos em caixa alta,
cards/pills, palavras repetidas 6x+, alt/labels/dimensões, alvos de toque, contraste WCAG,
teclado nas tabs, validação de formulário, overflow-x e altura em mobile/tablet/desktop.

Gera capturas em `--out`. **Abra as três** — o script não enxerga composição.

## Parte de julgamento (obrigatória, é sua)

**1 · Foco.** Uma oferta, uma conversão. Sem institucional, sem catálogo disfarçado.

**2 · Compactação.** Meta 3–5 seções. Para cada uma: *"se eu remover, a conversão piora?"*
Se não, remove ou funde.

**3 · Anti-IA.** Cards demais, pills, microtítulos em caixa alta, slogans genéricos, grids
previsíveis, simetria, seções com o mesmo ritmo, benefício repetido. O script conta; você corrige.

**4 · Naturalidade.** Especificidade e material real acima de adjetivo e frase de impacto.

**5 · Interatividade.** 1 a 3 interações que resolvam objeção real. Nunca por estética.

**6 · Claims.** Liste **todos** os claims factuais e classifique:
`A` briefing/material · `B` fonte pública confiável · `C` inferência.
**Nenhum `C` vai ao ar como fato.** Na dúvida, suavize ou corte.
Atenção especial a: anos de mercado, nº de clientes, fabricação própria, materiais, garantia,
prazo, região atendida, premiação, evento, preço, economia.

**7 · Prova.** Toda promessa forte tem prova ao lado — foto real, projeto, dado verificável,
detalhe de execução. Prova longe da objeção não trabalha.

**8 · CTA.** Uma conversão principal, texto claro, quantidade adequada, sem repetir o mesmo rótulo.

**9 · Formulário.** Campos mínimos, labels, validação, mobile. **Nunca simular envio.**
Sem backend: fallback explícito e funcional.

**10 · Mobile e 11 · Desktop.** Olhe as capturas. Hero, quebra de título, botões, imagens,
espaçamento, sticky, legibilidade, densidade, excesso de espaço.

**12 · Performance.** Imagem pesada demais, lazy fora da primeira dobra, dimensões declaradas.

**13 · Acessibilidade.** Alt, label, contraste, teclado, `prefers-reduced-motion`.

**14 · Anti-genérico.** *"Trocando logo, nome, cores e fotos, essa LP serviria para outro cliente?"*
Se sim, ainda está genérica.

**15 · Autocrítica.** Responda antes de entregar: o que está mais fraco? o que ainda parece IA?
o que está repetido? o que está grande demais? qual claim está menos sustentado? qual elemento
é mais genérico? o que provavelmente converteria melhor? **Corrija o que for relevante.**

## Entrega

```
Landing Page pronta.

ABRIR LP: [link]

Pendências:
[só bloqueio real que dependa do usuário]
```
