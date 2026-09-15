#!/usr/bin/env bash
# ---------------------------------------------------------------
# SQUAD NK — setup a partir de um clone limpo.
#
#   git clone git@github.com:acessosnonaka-cmyk/Squaud-nk.git
#   cd Squaud-nk && bash scripts/setup.sh
#
# Idempotente. Não sobrescreve dado de cliente já existente na máquina.
# Não contém segredo nenhum.
# ---------------------------------------------------------------
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
DATA_HOME="${SQUAD_DATA_HOME:-$HOME/.squad-nk}"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# link <destino> <origem>  — só cria; nunca apaga diretório real com conteúdo
link() {
  local dst="$1" src="$2"
  mkdir -p "$(dirname "$dst")"
  if [ -L "$dst" ]; then rm -f "$dst"
  elif [ -e "$dst" ]; then warn "já existe (mantido, não sobrescrito): $dst"; return 0; fi
  ln -s "$src" "$dst"; ok "$dst -> $src"
}

step "1/7  Agentes  ->  $CLAUDE_HOME/agents"
link "$CLAUDE_HOME/agents/copywriter.md"           "$REPO/agents/copywriter/agents/copywriter.md"
link "$CLAUDE_HOME/agents/diretor-de-operacoes.md" "$REPO/agents/diretor-operacoes/agents/diretor-de-operacoes.md"
link "$CLAUDE_HOME/agents/gestor-de-trafego.md"    "$REPO/agents/gestor-de-trafego/agents/gestor-de-trafego.md"

step "2/7  Skills  ->  $CLAUDE_HOME/skills"
link "$CLAUDE_HOME/skills/designer-ia"      "$REPO/agents/design-ia/skills/designer-ia"
link "$CLAUDE_HOME/skills/gestao-de-trafego" "$REPO/agents/gestor-de-trafego/skills/gestao-de-trafego"
for s in lp-ingestao lp-design-review lp-qa lp-publicar; do
  link "$CLAUDE_HOME/skills/$s" "$REPO/apps/lp-builder/skills/$s"
done

step "3/7  Skill externa: humanizer (MIT, blader/humanizer)"
if [ -d "$REPO/shared/skills/humanizer/.git" ]; then
  ok "humanizer já clonado"
else
  rm -rf "$REPO/shared/skills/humanizer"
  if git clone --depth 1 https://github.com/blader/humanizer.git "$REPO/shared/skills/humanizer" >/dev/null 2>&1; then
    ok "humanizer clonado"
  else
    warn "falha ao clonar humanizer — sem rede? rode de novo depois"
  fi
fi
[ -f "$REPO/shared/skills/humanizer/SKILL.md" ] && link "$CLAUDE_HOME/skills/humanizer" "$REPO/shared/skills/humanizer"

step "4/7  Motor do Design IA  ->  $CLAUDE_HOME/art-builder"
mkdir -p "$CLAUDE_HOME/art-builder"
for f in "$REPO"/agents/design-ia/engine/*.py "$REPO"/agents/design-ia/engine/formats.json \
         "$REPO"/agents/design-ia/engine/templates "$REPO"/agents/design-ia/engine/fonts; do
  link "$CLAUDE_HOME/art-builder/$(basename "$f")" "$f"
done
mkdir -p "$CLAUDE_HOME/art-builder/clients" "$CLAUDE_HOME/art-builder/jobs" "$CLAUDE_HOME/art-builder/output"
ok "pastas de dados preservadas (clients/ jobs/ output/)"

step "5/7  Motor do LP Builder  ->  $CLAUDE_HOME/lp-builder"
mkdir -p "$CLAUDE_HOME/lp-builder"
for f in "$REPO"/apps/lp-builder/engine/*.py; do
  link "$CLAUDE_HOME/lp-builder/$(basename "$f")" "$f"
done
if [ ! -f "$CLAUDE_HOME/lp-builder/publish.conf.json" ]; then
  cp "$REPO/apps/lp-builder/engine/publish.conf.example.json" "$CLAUDE_HOME/lp-builder/publish.conf.json"
  ok "publish.conf.json criado a partir do exemplo (edite para apontar o VPS)"
else
  ok "publish.conf.json já existe (mantido)"
fi
mkdir -p "$CLAUDE_HOME/lp-builder/clients" "$CLAUDE_HOME/lp-builder/previews"

step "6/7  Legend IA (venv + faster-whisper)"
if command -v ffmpeg >/dev/null 2>&1; then ok "ffmpeg encontrado"; else warn "ffmpeg AUSENTE — 'sudo apt install ffmpeg'"; fi
if [ -d "$REPO/apps/legend-ia/venv" ]; then
  ok "venv já existe"
elif python3 -m venv "$REPO/apps/legend-ia/venv" >/dev/null 2>&1; then
  "$REPO/apps/legend-ia/venv/bin/pip" install -q -r "$REPO/apps/legend-ia/requirements.txt" \
    && ok "faster-whisper instalado" || warn "pip falhou — instale manualmente"
else
  warn "python3-venv ausente — 'sudo apt install python3-venv'"
fi
mkdir -p "$REPO/apps/legend-ia/entrada de vídeo" "$REPO/apps/legend-ia/entrega"

step "7/7  Playwright (LP Builder: QA e screenshots)"
if python3 -c "import playwright" 2>/dev/null; then
  ok "playwright presente"
else
  warn "playwright ausente — 'pip install playwright && python3 -m playwright install chromium'"
fi

step "Plugins do Claude Code (Revisor de Arte e Gestor de Tráfego)"
cat <<'MSG'
  Rode uma vez, manualmente:
    claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
    claude plugin install revisor-de-criacao@squad-legend-ai
    claude plugin install gestor-de-trafego@squad-legend-ai
MSG

printf '\n\033[1mSetup concluído.\033[0m Confira com: bash scripts/check.sh\n'
printf 'Dados de trabalho ficam em %s e em %s (fora do git).\n' "$CLAUDE_HOME/art-builder" "$CLAUDE_HOME/lp-builder"
