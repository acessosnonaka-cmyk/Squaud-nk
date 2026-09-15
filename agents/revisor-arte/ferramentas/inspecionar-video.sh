#!/usr/bin/env bash
#
# inspecionar-video.sh — extrai MÉTRICAS TÉCNICAS OBJETIVAS e frames de um vídeo.
#
# Uso:  ./inspecionar-video.sh <arquivo-de-video> <pasta-de-saida> [n_frames]
#
# Produz em <pasta-de-saida>/:
#   metricas.txt        resumo legível (é o que deve ser lido pelo revisor)
#   ffprobe.json        saída bruta do ffprobe
#   loudness.txt        saída bruta do ebur128 (só se houver áudio)
#   blackdetect.txt     trechos pretos detectados
#   cortes.txt          timecodes de mudança de cena (ESTIMATIVA)
#   frames/             frames amostrados, nomeados pelo timecode
#
# ESCOPO: este script mede o arquivo. Ele NÃO avalia qualidade percebida.
# Presença e nível de áudio NÃO dizem que o áudio está bom.
# Ver conhecimento/criterios/videos.md §3.
#
# Dependências: ffmpeg e ffprobe (já presentes no sistema). Nada é instalado.

set -uo pipefail

VIDEO="${1:-}"
OUT="${2:-}"
NFRAMES="${3:-12}"

die() { echo "ERRO: $*" >&2; exit 1; }

[ -n "$VIDEO" ] && [ -n "$OUT" ] || die "uso: $0 <arquivo-de-video> <pasta-de-saida> [n_frames]"
[ -f "$VIDEO" ] || die "arquivo não encontrado: $VIDEO"
command -v ffprobe >/dev/null 2>&1 || die "ffprobe não encontrado"
command -v ffmpeg  >/dev/null 2>&1 || die "ffmpeg não encontrado"
case "$NFRAMES" in (*[!0-9]*|'') die "n_frames deve ser inteiro: $NFRAMES";; esac
[ "$NFRAMES" -ge 1 ] || die "n_frames deve ser >= 1"

mkdir -p "$OUT/frames" || die "não foi possível criar $OUT"
M="$OUT/metricas.txt"
: > "$M"

# ---------- ffprobe: dados brutos ----------
if ! ffprobe -v error -print_format json -show_format -show_streams \
     "$VIDEO" > "$OUT/ffprobe.json" 2>"$OUT/ffprobe.err"; then
  die "ffprobe falhou ao ler o arquivo (possível corrupção). Detalhes: $OUT/ffprobe.err"
fi

q() { ffprobe -v error -select_streams "$1" -show_entries "$2" \
      -of default=nw=1:nk=1 "$VIDEO" 2>/dev/null | head -1; }

DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$VIDEO" 2>/dev/null | head -1)
SIZE=$(ffprobe -v error -show_entries format=size -of default=nw=1:nk=1 "$VIDEO" 2>/dev/null | head -1)
FMT=$(ffprobe -v error -show_entries format=format_name -of default=nw=1:nk=1 "$VIDEO" 2>/dev/null | head -1)
BR=$(ffprobe -v error -show_entries format=bit_rate -of default=nw=1:nk=1 "$VIDEO" 2>/dev/null | head -1)

VCODEC=$(q v:0 stream=codec_name)
W=$(q v:0 stream=width)
H=$(q v:0 stream=height)
DAR=$(q v:0 stream=display_aspect_ratio)
RFPS=$(q v:0 stream=r_frame_rate)
VBR=$(q v:0 stream=bit_rate)
PIXFMT=$(q v:0 stream=pix_fmt)
NBF=$(q v:0 stream=nb_frames)

ACODEC=$(q a:0 stream=codec_name)
ASR=$(q a:0 stream=sample_rate)
ACH=$(q a:0 stream=channels)
ACHL=$(q a:0 stream=channel_layout)
ABR=$(q a:0 stream=bit_rate)

[ -n "${DUR:-}" ] || die "não foi possível determinar a duração (arquivo inválido?)"
[ -n "${VCODEC:-}" ] || echo "AVISO: nenhum stream de vídeo encontrado." >&2

# fps e aspect ratio calculados
FPS=$(awk -v r="${RFPS:-0/1}" 'BEGIN{split(r,a,"/"); if(a[2]+0>0) printf "%.3f", a[1]/a[2]; else print "n/d"}')
AR="${DAR:-}"
if [ -z "$AR" ] || [ "$AR" = "N/A" ]; then
  AR=$(awk -v w="${W:-0}" -v h="${H:-0}" 'BEGIN{
    if(h+0>0){ r=w/h;
      if(r>0.99&&r<1.01) print "1:1";
      else if(r>1.76&&r<1.79) print "16:9";
      else if(r>0.55&&r<0.57) print "9:16";
      else if(r>1.32&&r<1.34) print "4:3";
      else if(r>0.79&&r<0.81) print "4:5";
      else printf "%.4f:1 (não padrão)", r;
    } else print "n/d"}')
fi
DURF=$(awk -v d="${DUR:-0}" 'BEGIN{printf "%.3f", d}')
SIZEMB=$(awk -v s="${SIZE:-0}" 'BEGIN{printf "%.2f", s/1048576}')

{
echo "=========================================================="
echo " MÉTRICAS TÉCNICAS VERIFICÁVEIS"
echo " arquivo : $(basename "$VIDEO")"
echo " gerado  : $(date '+%Y-%m-%d %H:%M:%S')"
echo " origem  : ffprobe/ffmpeg — fatos medidos, confiança Alta"
echo "=========================================================="
echo
echo "-- CONTÊINER --"
echo "  Formato          : ${FMT:-n/d}"
echo "  Duração          : ${DURF} s"
echo "  Tamanho          : ${SIZEMB} MB"
echo "  Bitrate total    : ${BR:-n/d} bps"
echo
echo "-- VÍDEO --"
echo "  Codec            : ${VCODEC:-AUSENTE}"
echo "  Resolução        : ${W:-n/d} x ${H:-n/d}"
echo "  Aspect ratio     : ${AR:-n/d}"
echo "  FPS              : ${FPS}  (r_frame_rate: ${RFPS:-n/d})"
echo "  Bitrate vídeo    : ${VBR:-n/d} bps"
echo "  Pixel format     : ${PIXFMT:-n/d}"
echo "  Nº de frames     : ${NBF:-n/d}"
echo
echo "-- ÁUDIO --"
} >> "$M"

if [ -n "${ACODEC:-}" ]; then
  {
  echo "  Faixa de áudio   : PRESENTE"
  echo "  Codec            : ${ACODEC}"
  echo "  Sample rate      : ${ASR:-n/d} Hz"
  echo "  Canais           : ${ACH:-n/d} (${ACHL:-n/d})"
  echo "  Bitrate áudio    : ${ABR:-n/d} bps"
  } >> "$M"

  ffmpeg -hide_banner -nostats -i "$VIDEO" -map a:0 -af ebur128=peak=true \
         -f null - > /dev/null 2>"$OUT/loudness.txt"
  LUFS=$(grep -a -A6 'Summary:' "$OUT/loudness.txt" | grep -a -m1 'I:' | awk '{print $2}')
  LRA=$(grep -a -A12 'Summary:'  "$OUT/loudness.txt" | grep -a -m1 'LRA:' | awk '{print $2}')
  TPK=$(grep -a -A20 'Summary:'  "$OUT/loudness.txt" | grep -a -m1 'Peak:' | awk '{print $2}')
  {
  echo "  Loudness integr. : ${LUFS:-n/d} LUFS"
  echo "  Faixa dinâmica   : ${LRA:-n/d} LU"
  echo "  True peak        : ${TPK:-n/d} dBFS"
  if [ -n "${LUFS:-}" ] && [ "$LUFS" != "-inf" ]; then
    awk -v l="$LUFS" 'BEGIN{ if(l+0 < -50) print "  ALERTA          : nível compatível com áudio praticamente mudo" }'
  elif [ "${LUFS:-}" = "-inf" ]; then
    echo "  ALERTA           : silêncio digital (sem sinal na faixa de áudio)"
  fi
  if [ -n "${TPK:-}" ] && [ "$TPK" != "-inf" ]; then
    awk -v p="$TPK" 'BEGIN{ if(p+0 > -0.1) print "  ALERTA          : pico em/acima de 0 dBFS — possível clipping" }'
  fi
  } >> "$M"
else
  echo "  Faixa de áudio   : AUSENTE" >> "$M"
fi

{
echo
echo "  [ESCOPO] Acima: existência e NÍVEL do áudio. Locução, trilha, mixagem,"
echo "  ruído e equilíbrio voz/música NÃO são avaliáveis por estas métricas."
echo
echo "-- FRAMES PRETOS --"
} >> "$M"

ffmpeg -hide_banner -nostats -i "$VIDEO" -vf blackdetect=d=0.1:pix_th=0.10 -an \
       -f null - > /dev/null 2>"$OUT/blackdetect.raw"
grep -a 'blackdetect' "$OUT/blackdetect.raw" > "$OUT/blackdetect.txt" 2>/dev/null
if [ -s "$OUT/blackdetect.txt" ]; then
  sed 's/^/  /' "$OUT/blackdetect.txt" >> "$M"
else
  echo "  Nenhum trecho preto (>= 0,1 s) detectado." >> "$M"
fi

{
echo
echo "-- CORTES (ESTIMATIVA — confiança Média) --"
} >> "$M"

ffmpeg -hide_banner -nostats -i "$VIDEO" \
       -vf "select='gt(scene,0.3)',metadata=print:file=-" -an -f null - \
       > "$OUT/cortes.raw" 2>/dev/null
grep -a 'pts_time' "$OUT/cortes.raw" | awk '{print $NF}' | sed 's/pts_time://' > "$OUT/cortes.txt" 2>/dev/null
NCUTS=$(wc -l < "$OUT/cortes.txt" 2>/dev/null | tr -d ' ')
{
echo "  Mudanças de cena detectadas : ${NCUTS:-0}  (limiar scene>0.3)"
echo "  ATENÇÃO: estimativa. Não confundir com contagem real de cortes."
echo "  Transições suaves não são detectadas; movimento brusco gera falso positivo."
echo
echo "-- AMOSTRAGEM DE FRAMES --"
} >> "$M"

# frames uniformes + 3 do fecho
TIMES=$(awk -v d="$DUR" -v n="$NFRAMES" 'BEGIN{
  for(i=1;i<=n;i++) printf "%.3f\n", d*i/(n+1);
  if(d>1.5){ printf "%.3f\n", d-1.0 }
  if(d>0.8){ printf "%.3f\n", d-0.4 }
  if(d>0.3){ printf "%.3f\n", d-0.1 }
}' | sort -n -u)

COUNT=0
for t in $TIMES; do
  LBL=$(awk -v t="$t" 'BEGIN{printf "%07.2f", t}' | tr '.' '_')
  if ffmpeg -hide_banner -nostats -loglevel error -ss "$t" -i "$VIDEO" \
       -frames:v 1 -q:v 2 -y "$OUT/frames/t${LBL}s.jpg" >/dev/null 2>&1 \
       && [ -s "$OUT/frames/t${LBL}s.jpg" ]; then
    COUNT=$((COUNT+1))
  else
    rm -f "$OUT/frames/t${LBL}s.jpg"
  fi
done

{
echo "  Frames extraídos : ${COUNT}  ->  ${OUT}/frames/"
echo "  Nome do arquivo  : t<segundos>s.jpg (timecode da amostra)"
echo
echo "  [ESCOPO] A revisão visual do vídeo é feita SOBRE ESTES ${COUNT} FRAMES."
echo "  O vídeo não é assistido. Um problema entre dois frames amostrados não"
echo "  seria detectado. Ritmo e sincronização NÃO são avaliáveis por amostragem."
echo "=========================================================="
} >> "$M"

rm -f "$OUT/blackdetect.raw" "$OUT/cortes.raw" "$OUT/ffprobe.err"
cat "$M"
