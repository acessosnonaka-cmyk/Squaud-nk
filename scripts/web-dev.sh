#!/usr/bin/env bash
# ---------------------------------------------------------------
# Squad NK Web — desenvolvimento local, sem Docker.
#
#   bash scripts/web-dev.sh start|stop|status|logs
#
# Para produção use o Docker Compose. Este script existe para quem está
# mexendo no código e quer ciclo rápido. Lê o .env da raiz do repositório.
# ---------------------------------------------------------------
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$REPO/apps/web"
RUN="${SQUAD_RUN_DIR:-$APP/.run}"
PY="$APP/.venv/bin/python"
UVICORN="$APP/.venv/bin/uvicorn"
# PORTA e BIND são resolvidos DEPOIS de carregar o .env — senão o valor do
# arquivo nunca é usado e o servidor sobe numa porta diferente da configurada.
PORTA="" ; BIND=""

mkdir -p "$RUN"
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

carregar_env() {
  if [ -f "$REPO/.env" ]; then set -a; . "$REPO/.env"; set +a; fi
  PORTA="${SQUAD_WEB_PORT:-8000}"
  BIND="${SQUAD_WEB_BIND:-127.0.0.1}"
  export SQUAD_REPO_ROOT="${SQUAD_REPO_ROOT:-$REPO}"
  export SQUAD_DATA_HOME="${SQUAD_DATA_HOME:-$HOME/.squad-nk}"
  export PYTHONPATH="$APP"
}

vivo() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

start() {
  carregar_env
  [ -x "$PY" ] || { warn "venv ausente. Rode: python3 -m venv apps/web/.venv && apps/web/.venv/bin/pip install -r apps/web/requirements.txt"; exit 1; }
  [ -n "${SQUAD_WEB_SESSION_SECRET:-}" ] || { warn "SQUAD_WEB_SESSION_SECRET não definido. Veja .env.example."; exit 1; }

  # Sem subshell: dentro de `( ... & echo $! )` o $! é do processo filho do
  # subshell, não do servidor — e o pidfile apontava para um pid que já morreu,
  # deixando o servidor real órfão em toda parada.
  if vivo "$RUN/web.pid"; then
    ok "web já rodando (pid $(cat "$RUN/web.pid"))"
  else
    nohup "$UVICORN" squadnk.main:app --app-dir "$APP" \
        --host "$BIND" --port "$PORTA" >"$RUN/web.log" 2>&1 &
    echo $! > "$RUN/web.pid"
    ok "web  -> http://$BIND:$PORTA  (pid $(cat "$RUN/web.pid"))"
  fi
  if vivo "$RUN/worker.pid"; then
    ok "worker já rodando (pid $(cat "$RUN/worker.pid"))"
  else
    nohup "$PY" -m squadnk.worker >"$RUN/worker.log" 2>&1 &
    echo $! > "$RUN/worker.pid"
    ok "worker (pid $(cat "$RUN/worker.pid"))"
  fi
  printf '  dados em %s\n' "$SQUAD_DATA_HOME"
}

stop() {
  carregar_env
  for nome in web worker; do
    if vivo "$RUN/$nome.pid"; then
      kill "$(cat "$RUN/$nome.pid")" 2>/dev/null && ok "$nome parado"
    else
      warn "$nome não estava rodando"
    fi
    rm -f "$RUN/$nome.pid"
  done
  # Rede de segurança: se sobrou alguém segurando a porta (pidfile perdido num
  # crash, por exemplo), derruba pelo dono do socket.
  local orfao
  orfao="$(ss -lptn "sport = :$PORTA" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)"
  if [ -n "$orfao" ]; then
    kill "$orfao" 2>/dev/null && warn "web órfão na porta $PORTA encerrado (pid $orfao)"
  fi
  # Worker órfão não segura porta nenhuma, então é procurado pelo argumento do
  # módulo. Um worker velho sobrevivendo ao stop roda código desatualizado e
  # dá erro que não existe mais no fonte.
  for velho in $(ps -eo pid,args | grep -F -- "-m squadnk.worker" | grep -v grep | awk '{print $1}'); do
    kill "$velho" 2>/dev/null && warn "worker órfão encerrado (pid $velho)"
  done
}

status() {
  carregar_env
  for nome in web worker; do
    if vivo "$RUN/$nome.pid"; then ok "$nome rodando (pid $(cat "$RUN/$nome.pid"))"
    else warn "$nome parado"; fi
  done
}

case "${1:-start}" in
  start)  start ;;
  stop)   stop ;;
  restart) stop; sleep 1; start ;;
  status) status ;;
  logs)   tail -n 40 -F "$RUN/web.log" "$RUN/worker.log" ;;
  *) echo "uso: $0 start|stop|restart|status|logs"; exit 2 ;;
esac
