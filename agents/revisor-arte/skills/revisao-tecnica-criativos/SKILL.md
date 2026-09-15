---
name: revisao-tecnica-criativos
description: Esta skill deve ser usada sempre que for necessário verificar a qualidade técnica do arquivo de uma peça gráfica, criativo, post, banner, anúncio, story ou arte estática — dimensões, proporção, resolução, cortes, distorções, compressão, pixelização, problemas de exportação, elementos cortados e integridade do arquivo. Produz evidências técnicas para o Revisor de Criação; não atribui nota nem decide status.
---

# Revisão Técnica de Criativos

Esta skill **produz evidências**. Ela **não** atribui estrelas, **não** define status e
**não** decide se a peça é aprovada — isso é do Revisor de Criação.

## Medir, não estimar

Dimensões são **fato medido**, confiança Alta. `ffprobe` já está no sistema e lê `.png`,
`.jpg`, `.webp`, `.gif` e `.pdf`:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,pix_fmt -of csv=p=0 <arquivo>
```

## O que verificar

| Item | Como | Vira problema quando |
|---|---|---|
| **Dimensões** | `ffprobe` | divergem de requisito **informado** |
| **Proporção** | calculada | divergir de requisito **informado** |
| **Resolução** | dimensões × uso declarado | pixelização visível no uso pretendido |
| **Integridade** | abrir o arquivo | não decodifica, trunca ou vem vazio |
| **Elementos cortados** | leitura visual | logo, rosto, texto ou produto cortado pela margem |
| **Distorção** | leitura visual | logo ou foto esticados, proporção alterada |
| **Compressão** | leitura visual | blocos, banding ou halo visíveis em tamanho normal |
| **Pixelização** | leitura visual | bordas serrilhadas ou textura degradada |
| **Exportação** | leitura visual | moldura indevida, sobra de canvas, fundo transparente onde deveria ser sólido, guias visíveis |

## A regra do destino não informado

> **Não inventar requisito de plataforma quando o destino não foi informado.**

Uma peça **1156 × 1360** não tem defeito por não ser 1080 × 1350. Ninguém informou que
o destino exige 1080 × 1350.

- **Sem informação de destino:** registrar as dimensões como fato. Se a proporção não
  corresponder a um formato comum, isso pode virar **observação opcional** — nunca
  problema, nunca correção obrigatória.
- **Com destino informado** (briefing, manual, requisito escrito, indicação do usuário):
  aí sim, divergência é problema objetivo, confiança Alta.

O mesmo vale para peso de arquivo, formato de compressão e espaço de cor: sem requisito
informado, não há o que descumprir.

## Não verificável neste ambiente

Declarar como limitação, nunca como problema:

- DPI, CMYK, perfil de cor, sangria e marcas de corte — exigiriam ImageMagick ou
  exiftool, ausentes;
- aparência impressa real;
- comportamento da compressão aplicada pela plataforma de destino;
- `.psd`, `.ai`, `.indd`, `.fig`, `.svg` — não são lidos visualmente.

## Saída esperada

- **Ficha técnica**: arquivo, formato, dimensões, proporção, tamanho — fatos medidos.
- **Achados**: cada um com o quê · onde · evidência · confiança · ação recomendada.
- **Observações opcionais**, separadas dos problemas.
- **Limitações**: o que não foi verificável.

Se o arquivo estiver tecnicamente correto, dizer isso: *"Arquivo íntegro, sem problema
técnico identificado"*, com a ficha técnica anexa.
