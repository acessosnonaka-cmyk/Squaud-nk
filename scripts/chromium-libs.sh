#!/usr/bin/env bash
# ---------------------------------------------------------------
# Chromium headless precisa de libnss3/libnspr4. Muita imagem enxuta de
# Debian/Ubuntu (WSL incluso) não traz essas libs, e o render do Design IA falha
# com "error while loading shared libraries: libnspr4.so".
#
# Este script resolve nas três situações, nesta ordem:
#   1. libs já no sistema      -> não faz nada
#   2. sudo sem senha          -> apt install
#   3. sem root                -> baixa os .deb e extrai em engine/runtime/lib,
#                                 que render.py injeta via LD_LIBRARY_PATH só no
#                                 processo do browser. Não altera o sistema.
#
# Idempotente. Sem segredo. Só roda em Debian/Ubuntu (precisa de apt-get e dpkg-deb).
# ---------------------------------------------------------------
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIBDIR="$REPO/shared/runtime/lib"
ENGINE_LINK="$REPO/agents/design-ia/engine/runtime/lib"
PKGS=(libnss3 libnspr4)

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

# Substituição de comando, não pipe: sob `pipefail`, `ldconfig -p | grep -q` leva
# SIGPIPE quando o grep sai antes do ldconfig terminar de escrever, e o teste dá
# falso. Era por isso que este script reinstalava libs já presentes.
tem_lib() { case "$(ldconfig -p 2>/dev/null || true)" in *"$1"*) return 0;; *) return 1;; esac; }

if tem_lib libnspr4; then
  ok "libnss3/libnspr4 já estão no sistema"; exit 0
fi
ligar_engine() {
  # render.py procura as libs em ROOT/runtime/lib. ROOT e o proprio engine/, entao o
  # engine aponta para a copia compartilhada em vez de ter a sua.
  mkdir -p "$(dirname "$ENGINE_LINK")"
  [ -L "$ENGINE_LINK" ] && rm -f "$ENGINE_LINK"
  [ -e "$ENGINE_LINK" ] || ln -s "$LIBDIR" "$ENGINE_LINK"
}

if [ -f "$LIBDIR/libnspr4.so" ]; then
  ligar_engine; ok "libs já extraídas em shared/runtime/lib"; exit 0
fi

if sudo -n true 2>/dev/null; then
  sudo apt-get install -y "${PKGS[@]}" >/dev/null 2>&1 \
    && { ok "instaladas via apt"; exit 0; } || warn "apt falhou, tentando sem root"
fi

command -v apt-get >/dev/null 2>&1 && command -v dpkg-deb >/dev/null 2>&1 || {
  warn "sem apt-get/dpkg-deb — instale libnss3 e libnspr4 pelo gerenciador do seu sistema"
  exit 1
}

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
( cd "$TMP" && apt-get download "${PKGS[@]}" >/dev/null 2>&1 ) || {
  warn "não consegui baixar os pacotes — sem rede ou sem índice do apt ('apt-get update')"
  exit 1
}
mkdir -p "$LIBDIR"
for d in "$TMP"/*.deb; do dpkg-deb -x "$d" "$TMP/ex"; done
find "$TMP/ex" -name '*.so*' -o -name '*.chk' | while read -r f; do cp -f "$f" "$LIBDIR/"; done

if [ -f "$LIBDIR/libnspr4.so" ]; then
  ligar_engine
  ok "libs extraídas em shared/runtime/lib ($(ls "$LIBDIR" | wc -l) arquivos, sem root)"
else
  warn "extração falhou — instale libnss3 e libnspr4 manualmente"; exit 1
fi
