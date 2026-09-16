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
# Os agentes com prompt próprio, do roster de squad.yaml. Revisor de Arte e Gestor
# de Tráfego não entram: são plugins, instalados pelo marketplace (passo final).
link "$CLAUDE_HOME/agents/diretor-de-operacoes.md" "$REPO/agents/diretor-operacoes/agents/diretor-de-operacoes.md"
link "$CLAUDE_HOME/agents/copywriter.md"           "$REPO/agents/copywriter/agents/copywriter.md"
link "$CLAUDE_HOME/agents/designer.md"             "$REPO/agents/design-ia/agents/designer.md"
link "$CLAUDE_HOME/agents/lp-builder.md"           "$REPO/apps/lp-builder/agents/lp-builder.md"
link "$CLAUDE_HOME/agents/legend-ia.md"            "$REPO/apps/legend-ia/agents/legend-ia.md"
link "$CLAUDE_HOME/agents/revisor-de-criacao.md"   "$REPO/agents/revisor-arte/agents/revisor-de-criacao.md"

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
# ffmpeg/ffprobe não vêm na imagem de um container novo, e sem eles o Legend IA
# não roda e o Revisor não mede vídeo. Detecta antes, instala pelo pacote oficial
# da distro quando há permissão, e falha declarando quando não há — nunca finge.
instalar_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    ok "ffmpeg/ffprobe já presentes"; return 0
  fi
  local APT=""
  if [ "$(id -u)" = "0" ]; then APT="apt-get"
  elif sudo -n true 2>/dev/null; then APT="sudo apt-get"; fi
  if [ -z "$APT" ] || ! command -v apt-get >/dev/null 2>&1; then
    warn "ffmpeg AUSENTE e sem permissão para instalar — rode: sudo apt install ffmpeg"
    return 1
  fi
  $APT install -y ffmpeg >/dev/null 2>&1 \
    || { $APT update >/dev/null 2>&1; $APT install -y ffmpeg >/dev/null 2>&1; }
  if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    ok "ffmpeg/ffprobe instalados via apt"
  else
    warn "apt rodou mas ffmpeg/ffprobe continuam ausentes — instale manualmente"
    return 1
  fi
}
instalar_ffmpeg || true
if [ -d "$REPO/apps/legend-ia/venv" ]; then
  ok "venv já existe"
elif python3 -m venv "$REPO/apps/legend-ia/venv" >/dev/null 2>&1; then
  "$REPO/apps/legend-ia/venv/bin/pip" install -q -r "$REPO/apps/legend-ia/requirements.txt" \
    && ok "faster-whisper instalado" || warn "pip falhou — instale manualmente"
else
  warn "python3-venv ausente — 'sudo apt install python3-venv'"
fi
mkdir -p "$REPO/apps/legend-ia/entrada de vídeo" "$REPO/apps/legend-ia/entrega"

step "7/8  Venv dos motores de navegador (Design IA e LP Builder)"
# UM venv só, em apps/lp-builder/venv, para os dois motores. O Design IA o
# alcança por shared/pylib/squadnk_browser.py em vez de ter o seu — evita
# duplicar ~130 MB de Playwright e não exige mexer no python3 do sistema.
# O caminho não muda: apps/web/tools/lp.qa.yaml e check.sh continuam valendo.
VENV_MOTORES="$REPO/apps/lp-builder/venv"
if [ ! -x "$VENV_MOTORES/bin/python" ]; then
  python3 -m venv "$VENV_MOTORES" >/dev/null 2>&1 \
    || warn "python3-venv ausente — 'sudo apt install python3-venv'"
fi
if [ -x "$VENV_MOTORES/bin/python" ]; then
  if "$VENV_MOTORES/bin/pip" install -q -r "$REPO/apps/lp-builder/requirements.txt"; then
    ok "playwright + Pillow instalados (venv compartilhado pelos dois motores)"
  else
    warn "pip falhou — 'apps/lp-builder/venv/bin/pip install -r apps/lp-builder/requirements.txt'"
  fi
  # O navegador é resolvido em tempo de execução (plataforma > Playwright >
  # sistema). Só baixamos o do Playwright quando nenhum outro serve, para não
  # puxar ~150 MB à toa num ambiente que já traz Chromium pronto.
  if "$VENV_MOTORES/bin/python" "$REPO/shared/pylib/squadnk_browser.py" 2>/dev/null \
       | grep -q '^  OK .*chrom'; then
    ok "Chromium utilizável já disponível no ambiente"
  else
    "$VENV_MOTORES/bin/python" -m playwright install chromium >/dev/null 2>&1 \
      && ok "chromium do Playwright baixado" \
      || warn "nenhum Chromium disponível — 'apps/lp-builder/venv/bin/python -m playwright install chromium'"
  fi
fi

step "8/8  Libs do Chromium headless (libnss3/libnspr4)"
bash "$REPO/scripts/chromium-libs.sh" || warn "sem as libs o render do Design IA não roda"

step "9/10  Hook PreToolUse (portão de autonomia no Bash)"
# Sem este registro o policy.yaml não vale nada no Bash: o hook existe, passa
# nos testes, e nunca é chamado. O merge preserva qualquer hook já configurado
# e é idempotente — reconhece o nosso pelo nome do script.
SETTINGS="$CLAUDE_HOME/settings.json"
mkdir -p "$CLAUDE_HOME"
if HOOK_MSG="$(python3 - "$SETTINGS" <<'PY'
import json, pathlib, shutil, sys, time

destino = pathlib.Path(sys.argv[1])
COMANDO = 'python3 "$HOME/.claude/squad-nk/scripts/hook-pretooluse.py"'
MARCA = "hook-pretooluse.py"

dados = {}
if destino.is_file():
    try:
        dados = json.loads(destino.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        print("settings.json ilegível — NÃO foi tocado; registre o hook à mão")
        raise SystemExit(1)
    if not isinstance(dados, dict):
        print("settings.json não é um objeto — NÃO foi tocado")
        raise SystemExit(1)

hooks = dados.setdefault("hooks", {})
if not isinstance(hooks, dict):
    print("chave 'hooks' com formato inesperado — NÃO foi tocada")
    raise SystemExit(1)
pretool = hooks.setdefault("PreToolUse", [])

# Já registrado? Não duplica em execução nenhuma.
for grupo in pretool:
    for h in (grupo or {}).get("hooks", []) or []:
        if MARCA in str(h.get("command", "")):
            print("já registrado")
            raise SystemExit(0)

if destino.is_file():
    backup = destino.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(destino, backup)
    aviso = f"registrado (backup em {backup.name})"
else:
    aviso = "registrado (settings.json criado)"

pretool.append({
    "matcher": "Bash",
    "hooks": [{"type": "command", "command": COMANDO, "timeout": 15}],
})
destino.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(aviso)
PY
)"; then ok "hook PreToolUse: $HOOK_MSG"; else warn "hook PreToolUse: $HOOK_MSG"; fi

step "10/10  Plugins do Squad (Revisor de Arte e Gestor de Tráfego)"
# Gratuitos, vêm do marketplace do próprio repositório, sem autenticação extra.
# Os agentes NÃO dependem disto: sem plugin, ambos caem no monorepo.
if command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add "$REPO" >/dev/null 2>&1 \
    || claude plugin marketplace update squad-legend-ai >/dev/null 2>&1 || true
  for p in revisor-de-criacao gestor-de-trafego; do
    if claude plugin list 2>/dev/null | grep -q "$p"; then
      ok "plugin $p já instalado"
    elif claude plugin install "$p@squad-legend-ai" >/dev/null 2>&1; then
      ok "plugin $p instalado"
    else
      warn "plugin $p não instalou — o agente usa o monorepo como fallback"
    fi
  done
else
  warn "CLI 'claude' fora do PATH — os agentes usam o monorepo como fallback"
fi

printf '\n\033[1mSetup concluído.\033[0m Confira com: bash scripts/check.sh\n'
printf 'Dados de trabalho ficam em %s e em %s (fora do git).\n' "$CLAUDE_HOME/art-builder" "$CLAUDE_HOME/lp-builder"
