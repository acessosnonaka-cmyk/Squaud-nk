#!/usr/bin/env bash
# ---------------------------------------------------------------
# SQUAD NK — diagnóstico. Diz o que está reprodutível e o que falta.
# Só lê. Não altera nada.
# ---------------------------------------------------------------
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
FAIL=0

green() { printf '  \033[32m🟢 %s\033[0m\n' "$1"; }
yellow(){ printf '  \033[33m🟡 %s\033[0m\n' "$1"; }
red()   { printf '  \033[31m🔴 %s\033[0m\n' "$1"; FAIL=1; }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

have()  { command -v "$1" >/dev/null 2>&1; }
file_()  { [ -f "$1" ]; }

head_ "Roster oficial (squad.yaml)"
if file_ "$REPO/squad.yaml"; then
  n=$(grep -cE '^  - id: ' "$REPO/squad.yaml")
  [ "$n" -eq 7 ] && green "7 agentes declarados" || red "squad.yaml tem $n agentes; o roster oficial são 7"
  faltando=0
  for f in $(grep -E '^    prompt: [^n]' "$REPO/squad.yaml" | awk '{print $2}'); do
    file_ "$REPO/$f" || { red "prompt ausente: $f"; faltando=1; }
  done
  [ "$faltando" -eq 0 ] && green "todos os prompts declarados existem"
  grep -q 'agente: conceito' "$REPO/squad.yaml" \
    && yellow "há agente sem implementação — ver squad.yaml"
  # Auditoria completa: roster x prompts x skills x motores x REGISTRY x setup.sh.
  # Sai 2 quando existe agente em estado conceito — bloqueio declarado, não erro.
  if have python3; then
    saida=$(python3 "$REPO/agents/diretor-operacoes/engine/auditoria.py" 2>&1)
    falhas=$(printf '%s' "$saida" | grep -c '✗' || true)
    if [ "$falhas" -gt 0 ]; then
      printf '%s\n' "$saida" | grep '✗' | while read -r l; do red "${l#*✗ }"; done
    else
      green "auditoria do roster: prompts, skills, motores, REGISTRY e setup.sh conferem"
    fi
  fi
else
  red "squad.yaml ausente — o roster oficial não existe"
fi

head_ "Âncora do repositório"
if [ -L "$CLAUDE_HOME/squad-nk" ] && [ -d "$CLAUDE_HOME/squad-nk/agents" ]; then
  green "~/.claude/squad-nk -> $(readlink "$CLAUDE_HOME/squad-nk")"
else
  yellow "âncora ausente — os prompts citam ~/.claude/squad-nk; rode scripts/setup.sh"
fi

head_ "Ferramentas de base"
have git     && green "git"     || red "git ausente"
have python3 && green "python3 $(python3 -V 2>&1 | cut -d' ' -f2)" || red "python3 ausente"
have ffmpeg  && green "ffmpeg"  || yellow "ffmpeg ausente (Legend IA e medição técnica do Revisor)"
have node    && green "node $(node -v)" || yellow "node ausente (opcional)"
have claude  && green "claude code" || yellow "claude code não está no PATH"

head_ "1. LP BUILDER"
for f in publish.py lp_qa.py drive_ingest.py; do
  file_ "$REPO/apps/lp-builder/engine/$f" && green "engine/$f" || red "engine/$f ausente"
done
for s in lp-ingestao lp-design-review lp-qa lp-publicar; do
  file_ "$REPO/apps/lp-builder/skills/$s/SKILL.md" && green "skill $s" || red "skill $s ausente"
done
python3 -c "import playwright" 2>/dev/null && green "playwright (QA/screenshot)" \
  || yellow "playwright ausente — 'pip install playwright && python3 -m playwright install chromium'"
[ -L "$CLAUDE_HOME/skills/lp-qa" ] && green "skills ligadas em $CLAUDE_HOME" || yellow "rode scripts/setup.sh"

head_ "2. DIRETOR DE OPERAÇÕES"
file_ "$REPO/agents/diretor-operacoes/agents/diretor-de-operacoes.md" && green "agente" || red "agente ausente"
file_ "$REPO/agents/diretor-operacoes/REGISTRY.md" && green "REGISTRY.md" || red "REGISTRY.md ausente"
ligados=0
for a in diretor-de-operacoes copywriter designer lp-builder legend-ia revisor-de-criacao; do
  [ -L "$CLAUDE_HOME/agents/$a.md" ] && ligados=$((ligados+1))
done
[ "$ligados" -eq 6 ] && green "6 agentes registrados no Claude Code" \
  || yellow "$ligados/6 agentes registrados — rode scripts/setup.sh"

head_ "2b. DIRETOR — camada operacional"
for f in engine/modelo.py engine/demanda.py engine/policy.py policy.yaml; do
  file_ "$REPO/agents/diretor-operacoes/$f" && green "$f" || red "$f ausente"
done
for sc in demanda job briefing retorno; do
  file_ "$REPO/agents/diretor-operacoes/schemas/$sc.schema.json" || red "schema $sc ausente"
done
green "4 schemas de contrato"
if python3 "$REPO/agents/diretor-operacoes/engine/policy.py" classificar "ler um arquivo" >/dev/null 2>&1; then
  green "portão de autonomia responde"
else
  red "portão de autonomia não executa"
fi
if python3 "$REPO/agents/diretor-operacoes/engine/demanda.py" listar >/dev/null 2>&1; then
  green "CLI de demandas responde"
else
  red "CLI de demandas não executa"
fi
file_ "$REPO/scripts/hook-pretooluse.py" && green "hook PreToolUse presente" || red "hook ausente"
if grep -q "hook-pretooluse" "$CLAUDE_HOME/settings.json" 2>/dev/null; then
  green "hook registrado em settings.json"
else
  yellow "hook não registrado — veja agents/diretor-operacoes/README.md"
fi

head_ "3. DESIGN IA"
for f in render.py brand.py job.py artdirection.py revisor.py validate.py autofix.py assets.py selfcheck.py formats.json; do
  file_ "$REPO/agents/design-ia/engine/$f" && green "engine/$f" || red "engine/$f ausente"
done
[ -d "$REPO/agents/design-ia/engine/templates" ] && green "templates ($(ls "$REPO/agents/design-ia/engine/templates" | wc -l))" || red "templates ausentes"
[ -d "$REPO/agents/design-ia/engine/fonts/pool" ] && green "pool de fontes ($(ls "$REPO/agents/design-ia/engine/fonts/pool" | wc -l))" || red "fontes ausentes"
file_ "$REPO/agents/design-ia/skills/designer-ia/SKILL.md" && green "skill designer-ia" || red "skill ausente"
python3 -c "import playwright" 2>/dev/null && green "playwright (render)" || yellow "playwright ausente — render não roda"
if ldconfig -p 2>/dev/null | grep -q libnspr4 || [ -f "$REPO/shared/runtime/lib/libnspr4.so" ]; then
  green "libs do Chromium (libnss3/libnspr4)"
else
  red "libs do Chromium ausentes — render falha. Rode: bash scripts/chromium-libs.sh"
fi

head_ "4. REVISOR DE ARTE"
file_ "$REPO/agents/revisor-arte/agents/revisor-de-criacao.md" && green "agente" || red "agente ausente"
reg=0
for s in revisao-visual-criativos revisao-textual-criativos revisao-tecnica-criativos revisao-anuncios-criativos; do
  [ -L "$CLAUDE_HOME/skills/$s" ] && reg=$((reg+1))
done
[ "$reg" -eq 4 ] && green "4 skills registradas no Claude Code" \
  || yellow "$reg/4 skills registradas — rode scripts/setup.sh"
[ -d "$REPO/agents/revisor-arte/conhecimento/criterios" ] && green "base de critérios" || red "critérios ausentes"
file_ "$REPO/.claude-plugin/marketplace.json" && green "marketplace do plugin" || red "marketplace ausente"
python3 "$REPO/agents/design-ia/engine/revisor.py" locate >/dev/null 2>&1 \
  && green "plugin localizável na máquina" || yellow "plugin não instalado — 'claude plugin install revisor-de-criacao@squad-legend-ai'"

head_ "5. LEGEND IA"
file_ "$REPO/apps/legend-ia/process_video.py" && green "process_video.py" || red "process_video.py ausente"
file_ "$REPO/apps/legend-ia/requirements.txt" && green "requirements.txt" || red "requirements.txt ausente"
[ -d "$REPO/apps/legend-ia/fonts" ] && green "fontes embarcadas ($(ls "$REPO/apps/legend-ia/fonts" | wc -l))" || red "fontes ausentes"
file_ "$REPO/apps/legend-ia/venv/bin/python" && green "venv pronto" || yellow "venv ausente — rode scripts/setup.sh"
"$REPO/apps/legend-ia/venv/bin/python" -c "import faster_whisper" 2>/dev/null && green "faster-whisper" || yellow "faster-whisper ausente"

head_ "5b. GESTOR DE TRÁFEGO"
file_ "$REPO/agents/gestor-de-trafego/agents/gestor-de-trafego.md" && green "agente" || red "agente ausente"
file_ "$REPO/agents/gestor-de-trafego/skills/gestao-de-trafego/SKILL.md" && green "skill gestao-de-trafego" || red "skill ausente"
[ -d "$REPO/agents/gestor-de-trafego/conhecimento" ] && green "base de conhecimento ($(ls "$REPO/agents/gestor-de-trafego/conhecimento" | wc -l))" || red "conhecimento ausente"
[ -d "$REPO/agents/gestor-de-trafego/modelos/cliente" ] && green "modelos de memória de cliente" || red "modelos/cliente ausente"
file_ "$REPO/agents/gestor-de-trafego/capabilities.json" && green "capabilities.json" || red "capabilities.json ausente"
ls "${SQUAD_DATA_HOME:-$HOME/.squad-nk}"/trafego/clients/*/guardrails.md >/dev/null 2>&1 \
  && green "guardrails preenchidos para ao menos um cliente" \
  || yellow "nenhum guardrails.md — o Gestor recomenda, mas nao executa alteracao financeira"

head_ "6. SQUAD NK WEB"
file_ "$REPO/apps/web/squadnk/main.py" && green "aplicação" || red "apps/web ausente"
for t in legend.editar lp.qa lp.publicar lp.rollback; do
  file_ "$REPO/apps/web/tools/$t.yaml" && green "ferramenta $t" || red "declaração $t.yaml ausente"
done
file_ "$REPO/apps/lp-builder/venv/bin/python" && green "venv do LP Builder" || yellow "venv do LP Builder ausente — rode scripts/setup.sh"
file_ "$REPO/docker-compose.yml" && green "docker-compose.yml" || red "compose ausente"
file_ "$REPO/apps/web/.venv/bin/python" && green "venv da web" || yellow "venv ausente — 'python3 -m venv apps/web/.venv && apps/web/.venv/bin/pip install -r apps/web/requirements.txt'"
if [ -f "$REPO/.env" ]; then
  grep -q '^SQUAD_WEB_SESSION_SECRET=.\{32,\}' "$REPO/.env" \
    && green "SQUAD_WEB_SESSION_SECRET configurado" \
    || yellow "SQUAD_WEB_SESSION_SECRET ausente ou curto — o app recusa subir"
else
  yellow ".env ausente — 'cp .env.example .env' e preencha o segredo de sessão"
fi

head_ "Segredos no repositório"
# Os padroes sao montados em pedacos para o proprio check.sh nao casar com eles.
# docs/ e scripts/ ficam de fora: documentam os padroes, nao carregam segredo.
PAT="(sk""-ant-|gh[pousr]""_[A-Za-z0-9]{20,}|AKI""A[0-9A-Z]{16}|BEGIN .*PRIVATE ""KEY)"
if grep -rIqE "$PAT" "$REPO" --exclude-dir=.git --exclude-dir=venv --exclude-dir=node_modules \
     --exclude-dir=docs --exclude-dir=scripts 2>/dev/null; then
  red "possível segredo encontrado — NÃO faça push"
else
  green "nenhum segredo detectado"
fi

printf '\n'
[ "$FAIL" -eq 0 ] && printf '\033[32mSem bloqueios.\033[0m\n' || printf '\033[31mHá itens 🔴 — veja acima.\033[0m\n'
exit "$FAIL"
