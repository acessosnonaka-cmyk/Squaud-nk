#!/usr/bin/env bash
#
# drive-baixar.sh — converte a saída do Google Drive MCP em arquivo local real.
#
# CONTEXTO
#   O conector autenticado do Google Drive não escreve em disco: `download_file_content`
#   devolve o conteúdo em base64. Quando essa saída passa do teto de tokens, o Claude Code
#   a desvia automaticamente para um arquivo JSON em tool-results/, em vez de colocá-la no
#   contexto do modelo. Como todo criativo real passa desse teto, na prática o base64
#   NUNCA entra no contexto. Este script fecha o último passo: JSON -> arquivo binário.
#
#   Autenticado, sem exposição pública, sem dependência nova. Só python3.
#
# USO
#   drive-baixar.sh id <url-do-drive>
#       Extrai o fileId de um link de arquivo ou de pasta.
#
#   drive-baixar.sh salvar <arquivo-json> <pasta-destino> [nome-base]
#       Decodifica a saída do MCP e grava o arquivo real. Imprime o caminho.
#
#   drive-baixar.sh limpar <pasta-temp>
#       Remove uma pasta temporária de trabalho, com trava de segurança.
#       Só aceita caminhos sob ~/.cache/revisor-de-criacao/ ou .tmp-drive/.
#
# PASTA DE TRABALHO PADRÃO
#   ~/.cache/revisor-de-criacao/<lote>/   — fora da pasta de instalação do plugin,
#   que é sobrescrita a cada atualização.
#
# O script NUNCA escreve no Google Drive. Só lê o que o MCP já entregou.

set -uo pipefail
die() { echo "ERRO: $*" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || die "python3 não encontrado"

CMD="${1:-}"; shift || true

case "$CMD" in

  id)
    URL="${1:-}"; [ -n "$URL" ] || die "uso: $0 id <url-do-drive>"
    python3 - "$URL" <<'PY'
import re, sys
u = sys.argv[1]
# /file/d/<id>/ · /folders/<id> · ?id=<id> · /d/<id>
for pat in (r"/file/d/([A-Za-z0-9_-]{10,})",
            r"/folders/([A-Za-z0-9_-]{10,})",
            r"[?&]id=([A-Za-z0-9_-]{10,})",
            r"/d/([A-Za-z0-9_-]{10,})"):
    m = re.search(pat, u)
    if m:
        print(m.group(1))
        sys.exit(0)
# um id solto também é aceito
if re.fullmatch(r"[A-Za-z0-9_-]{10,}", u.strip()):
    print(u.strip()); sys.exit(0)
sys.exit("nenhum fileId reconhecido nesta URL")
PY
    ;;

  salvar)
    JSON="${1:-}"; OUT="${2:-}"; BASE="${3:-}"
    [ -n "$JSON" ] && [ -n "$OUT" ] || die "uso: $0 salvar <arquivo-json> <pasta-destino> [nome-base]"
    [ -f "$JSON" ] || die "arquivo não encontrado: $JSON"
    mkdir -p "$OUT" || die "não foi possível criar $OUT"
    python3 - "$JSON" "$OUT" "$BASE" <<'PY'
import base64, json, os, re, sys
src, outdir, base = sys.argv[1], sys.argv[2], sys.argv[3]

raw = open(src, "rb").read().decode("utf-8", "replace").strip()
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    d = {"content": raw}          # base64 puro, sem envelope JSON

content = d.get("content") or d.get("base64Content") or d.get("fileContent") or ""
if not content:
    sys.exit("ERRO: nenhum conteúdo base64 encontrado no JSON")

EXT = {"image/png":".png","image/jpeg":".jpg","image/jpg":".jpg","image/webp":".webp",
       "image/gif":".gif","application/pdf":".pdf","video/mp4":".mp4","video/quicktime":".mov"}
mime  = (d.get("mimeType") or "").split(";")[0].strip()
title = d.get("title") or d.get("name") or ""

if not base:
    base = os.path.splitext(title)[0] if title else "arquivo-drive"
base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-") or "arquivo-drive"

ext = EXT.get(mime) or (os.path.splitext(title)[1] if title else "") or ".bin"
dest = os.path.join(outdir, base + ext)
n = 1
while os.path.exists(dest):
    dest = os.path.join(outdir, f"{base}-{n}{ext}"); n += 1

try:
    data = base64.b64decode(content, validate=False)
except Exception as e:
    sys.exit(f"ERRO: base64 inválido: {e}")
if not data:
    sys.exit("ERRO: conteúdo decodificado vazio")

with open(dest, "wb") as f:
    f.write(data)
print(dest)
PY
    ;;

  limpar)
    DIR="${1:-}"; [ -n "$DIR" ] || die "uso: $0 limpar <pasta-temp>"
    case "$DIR" in
      */.cache/revisor-de-criacao/*) : ;;
      */.tmp-drive/*) : ;;
      *) die "recusado: só removo pastas de trabalho do Revisor (~/.cache/revisor-de-criacao/ ou .tmp-drive/) — recebido: $DIR" ;;
    esac
    [ -d "$DIR" ] || { echo "nada a limpar: $DIR"; exit 0; }
    rm -rf -- "$DIR" && echo "removido: $DIR"
    ;;

  *)
    die "uso: $0 {id|salvar|limpar} ...  (veja o cabeçalho do script)"
    ;;
esac
