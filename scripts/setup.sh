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

step "0/8  Âncora do repositório e raiz de dados"
# Um ponto fixo para os agentes citarem o clone sem caminho de máquina no prompt.
# É o mesmo truque de ~/.claude/art-builder: o prompt fala de ~/.claude/squad-nk,
# e quem aponta para o clone é este symlink.
link "$CLAUDE_HOME/squad-nk" "$REPO"
mkdir -p "$DATA_HOME/copywriter/entregas"
# Entregas anteriores à unificação continuam onde estão, e ficam alcançáveis a
# partir da nova raiz. Nada é movido nem apagado.
if [ -d "$HOME/projetos/copywriter/entregas" ] \
   && [ ! -e "$DATA_HOME/copywriter/entregas-legado" ]; then
  ln -s "$HOME/projetos/copywriter/entregas" "$DATA_HOME/copywriter/entregas-legado"
  ok "entregas antigas acessíveis em $DATA_HOME/copywriter/entregas-legado"
fi
ok "dados do Copywriter em $DATA_HOME/copywriter/"

step "1/8  Agentes  ->  $CLAUDE_HOME/agents"
# Os agentes com prompt próprio, do roster de squad.yaml. Symlink, não cópia: o
# arquivo continua único, no clone. Revisor de Arte e Gestor de Tráfego também são
# plugins do marketplace (passo final) e mesmo assim entram aqui: o plugin instala
# skill, conhecimento e modelos, mas quem registra o subagente no Claude Code é o
# link em ~/.claude/agents. Sem ele, Agent(subagent_type: "...") não encontra o
# agente — e o Diretor cria job que ninguém executa.
link "$CLAUDE_HOME/agents/diretor-de-operacoes.md" "$REPO/agents/diretor-operacoes/agents/diretor-de-operacoes.md"
link "$CLAUDE_HOME/agents/copywriter.md"           "$REPO/agents/copywriter/agents/copywriter.md"
link "$CLAUDE_HOME/agents/designer.md"             "$REPO/agents/design-ia/agents/designer.md"
link "$CLAUDE_HOME/agents/lp-builder.md"           "$REPO/apps/lp-builder/agents/lp-builder.md"
link "$CLAUDE_HOME/agents/legend-ia.md"            "$REPO/apps/legend-ia/agents/legend-ia.md"
link "$CLAUDE_HOME/agents/revisor-de-criacao.md"   "$REPO/agents/revisor-arte/agents/revisor-de-criacao.md"
link "$CLAUDE_HOME/agents/gestor-de-trafego.md"    "$REPO/agents/gestor-de-trafego/agents/gestor-de-trafego.md"

step "2/8  Skills  ->  $CLAUDE_HOME/skills"
link "$CLAUDE_HOME/skills/designer-ia"      "$REPO/agents/design-ia/skills/designer-ia"
for s in lp-ingestao lp-design-review lp-qa lp-publicar; do
  link "$CLAUDE_HOME/skills/$s" "$REPO/apps/lp-builder/skills/$s"
done

step "2b/8  Skills do Revisor de Arte"
# Symlink, não cópia: o arquivo continua único, no clone. Se o plugin do Revisor
# também estiver instalado, as dele ficam com prefixo de plugin e não colidem.
for s in revisao-visual-criativos revisao-textual-criativos \
         revisao-tecnica-criativos revisao-anuncios-criativos; do
  link "$CLAUDE_HOME/skills/$s" "$REPO/agents/revisor-arte/skills/$s"
done

step "3/8  Skill externa: humanizer (MIT, blader/humanizer)"
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

step "4/8  Motor do Design IA  ->  $CLAUDE_HOME/art-builder"
mkdir -p "$CLAUDE_HOME/art-builder"
for f in "$REPO"/agents/design-ia/engine/*.py "$REPO"/agents/design-ia/engine/formats.json \
         "$REPO"/agents/design-ia/engine/templates "$REPO"/agents/design-ia/engine/fonts; do
  link "$CLAUDE_HOME/art-builder/$(basename "$f")" "$f"
done
# O motor resolve tudo a partir da propria pasta (ROOT = dirname do .py). Como os .py
# sao symlinks para o repositorio, ROOT cai dentro do clone — e dado de cliente nao pode
# morar no clone. Estas tres pastas do clone apontam de volta para fora do git.
mkdir -p "$CLAUDE_HOME/art-builder/clients" "$CLAUDE_HOME/art-builder/jobs" "$CLAUDE_HOME/art-builder/output"
for d in clients jobs output; do
  link "$REPO/agents/design-ia/engine/$d" "$CLAUDE_HOME/art-builder/$d"
done
ok "dados do Design IA ficam em $CLAUDE_HOME/art-builder/ (fora do git)"

step "5/8  Motor do LP Builder  ->  $CLAUDE_HOME/lp-builder"
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

step "6/8  Legend IA (venv + faster-whisper)"
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

step "7b/8  Motor do LP Builder (venv + Playwright)"
if [ -x "$REPO/apps/lp-builder/venv/bin/python" ]; then
  ok "venv do LP Builder já existe"
elif python3 -m venv "$REPO/apps/lp-builder/venv" >/dev/null 2>&1; then
  "$REPO/apps/lp-builder/venv/bin/pip" install -q -r "$REPO/apps/lp-builder/requirements.txt" \
    && "$REPO/apps/lp-builder/venv/bin/python" -m playwright install chromium >/dev/null 2>&1 \
    && ok "playwright + chromium instalados" || warn "instale manualmente: apps/lp-builder/venv/bin/pip install -r apps/lp-builder/requirements.txt"
else
  warn "python3-venv ausente — 'sudo apt install python3-venv'"
fi

step "7/8  Playwright (Design IA e LP Builder: render, QA e screenshots)"
if python3 -c "import playwright" 2>/dev/null; then
  ok "playwright presente"
  python3 -m playwright install chromium >/dev/null 2>&1 && ok "chromium baixado" \
    || warn "chromium não baixou — 'python3 -m playwright install chromium'"
else
  warn "playwright ausente — 'pip install playwright && python3 -m playwright install chromium'"
fi

step "8/8  Libs do Chromium headless (libnss3/libnspr4)"
bash "$REPO/scripts/chromium-libs.sh" || warn "sem as libs o render do Design IA não roda"

step "Revisor de Arte (plugin do Claude Code)"
cat <<'MSG'
  Rode uma vez, manualmente:
    claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
    claude plugin install revisor-de-criacao@squad-legend-ai
    claude plugin install gestor-de-trafego@squad-legend-ai
MSG

printf '\n\033[1mSetup concluído.\033[0m Confira com: bash scripts/check.sh\n'
printf 'Dados de trabalho ficam em %s e em %s (fora do git).\n' "$CLAUDE_HOME/art-builder" "$CLAUDE_HOME/lp-builder"
