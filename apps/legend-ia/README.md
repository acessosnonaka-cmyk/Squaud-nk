# video-editor

Pipeline simples: pega um vídeo MP4 + um texto de CTA, transcreve o áudio,
revisa a transcrição, queima legendas e o CTA no vídeo.

## Requisitos já validados neste ambiente

- FFmpeg com libx264, drawtext e subtitles (libass)
- Python 3.14 em `venv/` na raiz do projeto
- `faster-whisper` instalado no venv (modelo `base`, CPU)

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

```bash
venv/bin/python process_video.py 01.mp4 --cta "COMPRE AGORA" --preset pro
```

- `classic` (padrão) — comportamento original, sem nenhuma alteração visual.
  Usado automaticamente quando `--preset` não é informado.
- `pro` — tipografia Ubuntu Sans (Bold para legenda/texto, ExtraBold para o
  CTA), blocos de legenda menores e mais naturais, entrada curta (fade +
  leve "pop" de escala) e saída curta em cada bloco, transição suave
  (crossfade) entre blocos consecutivos, e uma animação de entrada própria
  para o CTA. A safe zone (posições/margens) é a mesma dos dois presets.
