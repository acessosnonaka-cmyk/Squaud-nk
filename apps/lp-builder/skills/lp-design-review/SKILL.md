---
name: lp-design-review
description: Design review de Landing Page. Use depois de implementar e renderizar, antes do QA final. Força uma direção de arte derivada do próprio cliente e mata layout genérico.
---

# Design review — antes do QA, depois do render

Roda junto do QA: `python3 ~/.claude/lp-builder/lp_qa.py <url>` já imprime o bloco **DESIGN**
(escala tipográfica, famílias, ritmo entre seções, proporções de imagem, raios, cores, medida de texto).

Número não decide design. O bloco existe para expor o que costuma denunciar página genérica:
ritmo plano, escala tipográfica curta, uma proporção de imagem só, um raio de canto só.

## 1 · Conceito antes de layout
A direção de arte nasce de algo **físico e específico do cliente**: um elemento da fachada, da
embalagem, do espaço, do logo, de um material, de um processo. Não de tendência nem de segmento.

Pergunta: *"que forma, textura ou gesto só existe neste cliente?"*
Se a resposta for "as cores do logo", ainda não há conceito.

## 2 · Elemento assinatura
Escolha **um** elemento que se repita e organize a página — uma forma, um corte, um enquadramento,
um recurso de composição. Ele deve aparecer em pelo menos três momentos, sempre com função.

## 3 · Ritmo
Seções não podem ter o mesmo peso. Uma visual, uma editorial, uma de conversão, uma curta.
Se `variação de ritmo < 0.28`, a página está monótona.

## 4 · Tipografia
Escala com pelo menos 5 tamanhos distintos e contraste real entre display e corpo.
Nunca repetir o par tipográfico de outra LP da carteira — cada cliente tem o seu.

## 5 · Fotografia
Enquadramento e recorte fazem parte do design. Corte para a emoção, não para o retângulo.
Varie proporções entre seções. Nunca deixar texto queimado de post de rede social.

## 6 · Segunda passagem
Depois de renderizar, olhe desktop e mobile e pergunte:
*"isso parece dirigido ou parece montado?"* Se parecer montado, refaça — não adicione efeito.
Efeito não conserta composição.

Só depois disso siga para `lp-qa`.
