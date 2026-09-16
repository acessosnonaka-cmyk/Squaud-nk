# video-editor

Pipeline simples: pega um vídeo MP4 + um texto de CTA, transcreve o áudio,
revisa a transcrição, queima legendas e o CTA no vídeo.

## Requisitos

- FFmpeg com libx264 e subtitles (libass) — uma única passagem de render usa o filtro `ass`
- Python 3.11+ em `venv/` na raiz do projeto, criado por `scripts/setup.sh`
- `faster-whisper` instalado no venv (modelo `base`, CPU, `int8`, idioma fixo em `pt`)

## Uso

```bash
venv/bin/python process_video.py 01.mp4 --cta "CLIQUE NO BOTÃO ABAIXO E FAÇA SEU PEDIDO"
```

- Coloque o vídeo de entrada em `entrada de vídeo/`.
- O resultado sai em `entrega/<nome>_final.mp4`.
- `--cta-duration N` define quantos segundos do final do vídeo mostram o CTA (padrão: 3).

O vídeo original em `entrada de vídeo/` nunca é alterado.

## Padrões do pipeline

- Transcrição: `faster-whisper`, modelo `base`, CPU, português, timestamps por palavra.
- Revisão: corrige apenas erros de alta confiança (ex.: "Timazap" → "WhatsApp",
  espaçamento de valores em R$ e de casas decimais). Não reescreve a fala.
- Legenda: branca, negrito, contorno preto, centralizada, região inferior,
  no máx. ~2 linhas. Dimensionamento respeita a resolução real de exibição
  (inclusive vídeos verticais com metadados de rotação).
- CTA: amarelo/dourado, negrito, contorno preto, acima da legenda, sem sobreposição,
  visível nos últimos segundos do vídeo (padrão: 3s).

## Presets visuais (`--preset`)

São **quatro**, e cada um é uma linguagem visual completa: por papel (legenda, texto,
headline, CTA) define fonte, peso, itálico, escala, contorno, sombra, blur e animação.
Preset não é "trocar a fonte".

```bash
venv/bin/python process_video.py 01.mp4 --cta "COMPRE AGORA" --cta-style impact
```

- `classic` (padrão) — DejaVu Sans, sem animação. Comportamento original, preservado
  valor por valor. Usado quando `--preset` não é informado. **Nunca altere os números
  de `classic` para ajustar outro preset.**
- `editorial` — Lora (serifada, OFL), headline em itálico real, sombra suave com blur no
  lugar de contorno grosso, movimento discreto (só fade). Para algo elegante/refinado.
- `impact` — Anton (condensada ultra-bold, OFL), entrada com *overshoot* de escala
  (90% → 103% → 100%). Para algo chamativo/publicitário. É o padrão de headline.
- `pro` — legado, anterior à referência visual atual. Ubuntu Sans, com crossfade entre
  blocos de legenda. Mantido só por compatibilidade; não use por padrão.

A safe zone (posições/margens) é a mesma em todos. Cada operação aceita estilo próprio —
`--subtitles-style`, `--cta-style`, `--text-style`, `--headline-style` — e isso é
preferível a mudar o `--preset` global.
