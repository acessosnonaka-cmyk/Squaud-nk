---
name: editar-video
description: Use quando o usuário pedir para editar, legendar ou processar um vídeo deste projeto (video-editor/Legend.IA), por exemplo "edite o vídeo X.mp4", "adiciona legenda em X.mp4", "sem legenda, só CTA", "coloque a frase Y no vídeo", "coloque uma headline chamativa", "processa esse vídeo com CTA...", "estilo editorial/impact". Executa o motor componível do projeto (transcrição opcional + legenda/texto/headline/CTA opcionais, cada um com estilo próprio) via process_video.py.
---

# Editar vídeo (motor componível do Legend.IA)

Esta skill executa o motor do projeto sobre um vídeo MP4, combinando até
quatro operações independentes, todas opcionais: **legenda automática**
(via transcrição), **texto** (frase manual genérica), **headline**
(chamada visual de maior hierarquia) e **CTA**. Nem todo pedido usa todas
— interprete literalmente o que o usuário pediu.

## Regra fundamental: uma entrega por pedido

**Por padrão, cada pedido do usuário gera UM único vídeo final.** O
agente interpreta o objetivo e escolhe a composição/estilo mais adequados
internamente — não entregue várias versões (ex: uma em EDITORIAL e outra
em IMPACT) para o usuário escolher. Presets são ferramentas internas do
Legend, não opções que precisam ser expostas em cada job.

Só gere mais de uma versão quando o usuário pedir isso explicitamente —
frases como "me dê 3 opções", "quero comparar estilos", "faça um A/B",
"gera em editorial e em impact pra eu ver". Fora isso: **1 entrada → 1
interpretação → 1 render final.**

## Quando usar

O usuário pede para editar/legendar/processar um vídeo deste projeto,
geralmente citando um arquivo (ex: "02.mp4") e algum elemento (CTA, frase,
headline, ou legenda).

## Passo 1 — Identificar o vídeo

O arquivo deve estar em `entrada de vídeo/`. Confirme que existe com
`ls "entrada de vídeo/"`. Se não existir, informe e pare — não procure
vídeos em outros diretórios ou projetos.

## Passo 2 — Interpretar o pedido: qual(is) modo(s)?

**Regra importante: não presuma que todo vídeo precisa de legenda.**
Leia literalmente o que o usuário pediu:

- Se ele disser **"sem legenda"**, **"não legendar"**, **"somente CTA"** ou
  **"só coloque o texto"** → **não rode transcrição/Whisper**. Isso é mais
  rápido porque pula a etapa mais pesada do pipeline.
- Se ele pedir **legenda** (ou não disser nada sobre legenda) → o padrão é
  transcrever e legendar normalmente (comportamento de sempre).
- Se ele pedir para **"escrever"**, **"colocar a frase"** ou **"colocar o
  texto"** X no vídeo → isso é a **frase adicional** (`--text`), diferente
  do CTA e da headline. Pode vir com uma posição (topo / centro / inferior
  / acima da legenda); se não especificar, o padrão é **centro**.
- Se ele pedir uma **"headline"**, **"chamada"**, **"título"** ou algo
  descrito como "chamativo"/"de impacto"/"de destaque" para o vídeo → isso
  é a **headline** (`--headline`), diferente de `--text`. A headline tem
  composição/escala/hierarquia própria (não é só uma legenda maior) — veja
  "Escolha de estilo" abaixo. Se não especificar posição, use **topo** por
  padrão (para não disputar espaço com legenda/CTA na região inferior).
- CTA, frase adicional e headline podem ser combinados livremente entre si
  e com legenda ligada ou desligada, conforme o pedido.

### Escolha de estilo (preset)

Cada operação (legenda/texto/headline/CTA) pode ter seu próprio estilo:
`classic` (visual original, sem animação), `editorial` (sofisticado,
serifado, itálico, movimento discreto — para algo elegante/refinado) ou
`impact` (sans-serif forte, condensada, entrada com "pop" — para algo
chamativo/publicitário/de destaque).

- **Se o usuário pedir um estilo explicitamente** ("estilo editorial",
  "quero impact", "visual mais elegante", "algo chamativo tipo anúncio")
  → use o preset correspondente (`editorial` para elegante/sofisticado,
  `impact` para chamativo/forte/publicitário).
- **Se o usuário não especificar estilo nenhum** para uma legenda/texto
  comum → use `classic` (comportamento padrão, já aprovado).
- **Se o usuário pedir uma HEADLINE sem especificar estilo** → escolha
  `impact` por padrão (headline existe para chamar atenção; é isso que
  IMPACT foi desenhado para fazer), a menos que o pedido descreva algo
  claramente elegante/sofisticado/discreto, caso em que use `editorial`.
- Nunca pergunte ao usuário "qual estilo você quer" só por rotina — decida
  pelo objetivo descrito. Só confirme se o pedido for genuinamente ambíguo.

**Identificar o texto de cada elemento** (CTA, frase adicional e/ou
headline): use exatamente o texto que o usuário informou, sem reescrever
ou "melhorar" a frase (só corrija erro ortográfico óbvio se necessário).
Não invente conteúdo. **Se o usuário pediu CTA, texto ou headline mas não
informou o conteúdo, pergunte antes de continuar.**

### Exemplos de interpretação

| Pedido do usuário | subtitles | cta | text | headline |
|---|---|---|---|---|
| "Edite o vídeo 03.mp4. Legende e coloque o CTA: FAÇA SEU PEDIDO AGORA." | sim (padrão) | "FAÇA SEU PEDIDO AGORA" (classic) | — | — |
| "Edite o vídeo 04.mp4. Sem legenda. CTA: CLIQUE NO BOTÃO ABAIXO." | não | "CLIQUE NO BOTÃO ABAIXO" (classic) | — | — |
| "Edite o vídeo 05.mp4. Sem legenda. Escreva: RESULTADO EM 30 DIAS." | não | — | "RESULTADO EM 30 DIAS" (centro, classic) | — |
| "Coloque uma headline chamativa: TRANSFORME O QUARTO DELES." | sim (padrão, pois não disse "sem legenda") | — | — | "TRANSFORME O QUARTO DELES" (topo, **impact** — pedido é "chamativa") |
| "Vídeo já legendado, não mexa. Quero uma headline elegante no estilo editorial: NOVA COLEÇÃO." | não (vídeo já tem legenda própria) | — | — | "NOVA COLEÇÃO" (topo, **editorial** — pedido explícito) |
| "Coloque HEADLINE e CTA COMPRE AGORA no final." | sim (padrão) | "COMPRE AGORA" (classic) | — | headline (topo, impact — padrão p/ headline sem estilo pedido) |
| "Só adiciona a CTA 'X'." | sim (padrão) | "X" (classic) | — | — |

Uma única chamada ao `process_video.py` já produz o vídeo final combinando
tudo isso — não gere chamadas extras "para comparar" a menos que pedido.

## Passo 3 — Executar o pipeline

```bash
venv/bin/python process_video.py "<arquivo>" [--preset classic|editorial|impact] [--subtitles | --no-subtitles] \
  [--cta "<texto>" --cta-style <preset> --cta-position <pos> --cta-start N --cta-duration N] \
  [--text "<frase>" --text-style <preset> --text-position <pos> --text-delay N --text-hide-before N] \
  [--headline "<frase>" --headline-style <preset> --headline-position <pos> --headline-start N --headline-duration N]
```

- `--preset` é o estilo padrão de fallback quando uma operação não tem
  `--<op>-style` próprio; omitir equivale a `--preset classic`. Prefira
  usar `--cta-style`/`--text-style`/`--headline-style` por operação em vez
  de mudar o `--preset` global, para não afetar operações que deveriam
  ficar no padrão.
- `--subtitles` é o padrão (pode omitir); use `--no-subtitles` quando o
  pedido for "sem legenda"/"vídeo já legendado"/"somente CTA"/"só o texto"
  — o Legend não detecta nem remove legenda já existente no vídeo, só a
  preserva.
- `--cta`, `--text` e `--headline` são independentes e opcionais — use os
  que o pedido exigir. É preciso informar pelo menos um entre legenda
  (padrão), `--cta`, `--text` ou `--headline`.
- `--headline-position` padrão é **topo** (evita disputar espaço com
  legenda/CTA, que ficam na região inferior). `--headline-start`/
  `--headline-duration` padrão é do início até o fim do vídeo — use
  `--headline-duration N` quando o pedido disser algo como "nos primeiros
  N segundos".
- `--cta-position` padrão é `acima-legenda` (empilha acima da legenda
  automaticamente); `--cta-start` só é necessário se o CTA não deve seguir
  o padrão de "últimos N segundos".
- Use `--cta-duration N` somente se o usuário pedir explicitamente uma
  duração diferente do padrão (3 segundos).
- Use `--cta-blink-arrows` somente se o CTA terminar com setas (ex: "↓ ↓")
  e o usuário pedir que elas pisquem.
- Use `--text-position` somente se o usuário indicar uma posição; caso
  contrário deixe o padrão (centro).
- Use `--text-delay N` se o usuário pedir que a frase apareça só depois de
  N segundos de vídeo.
- Use `--text-hide-before N` se o usuário pedir que a frase desapareça N
  segundos antes do fim do vídeo (ex: "tirar faltando 3 segundos").

Quando a legenda está ativa, o script transcreve (faster-whisper, modelo
`base`, CPU), revisa a transcrição (corrige erros fonéticos de alta
confiança como "Timazap" → "WhatsApp", sem inventar conteúdo) e gera as
legendas. Quando `--no-subtitles` é usado, nenhuma dessas etapas roda — o
Whisper não é chamado. Em seguida o script monta o(s) overlay(s) (CTA e/ou
frase) e renderiza o MP4 final, validando o arquivo de saída ao final.

## Passo 4 — Conferir a saída

O script imprime o caminho final (`entrega/<nome>_final.mp4`) e valida que
o arquivo tem vídeo e áudio. Se o script terminar com erro, mostre a
mensagem de erro ao usuário — não tente contornar silenciosamente.

## Passo 5 — Informar o usuário

Diga onde o arquivo final foi salvo, quais elementos foram aplicados
(legenda sim/não, CTA, frase e posição), o idioma detectado (se
transcreveu), e se alguma correção de transcrição foi aplicada (o script
lista as correções no próprio output).

## Regras importantes

- Nunca sobrescreva o vídeo original em `entrada de vídeo/`.
- Nunca processe arquivos fora deste projeto (`~/video-editor`).
- Não use `--device cuda` nem tente GPU — o padrão do projeto é CPU.
- Não use o modelo `small` — o padrão do projeto é `base`.
- Não crie funcionalidades além deste pipeline (sem interface web, API,
  banco de dados ou Docker).

## Safe zone para vídeos verticais (tráfego pago)

Estes vídeos são usados principalmente em anúncios de Reels/Stories no
Instagram/Facebook. Para vídeos verticais (9:16), o `process_video.py` já
mantém automaticamente os ~20% inferiores do quadro livres de legenda/CTA,
para não colidir com os controles nativos desses apps (curtir, comentar,
CTA nativo, etc.). A legenda sobe para essa faixa segura e o CTA continua
acima da legenda, sem sobreposição. Vídeos horizontais mantêm o
posicionamento padrão anterior. Isso é tratado automaticamente pelo script
— não é necessário fazer nada extra ao chamar o pipeline, inclusive nos
modos sem legenda (somente CTA e/ou somente texto).
