"""Worker da fila: um processo separado do web.

Job de vídeo leva minutos. Preso a uma request HTTP, o navegador expira, o usuário
recarrega e o trabalho se perde. Aqui o web só enfileira; quem executa é este loop.
"""
from __future__ import annotations

import signal
import sys
import time

from . import config, db, runner

_parar = False


def _sinal(signum, _frame):
    global _parar
    _parar = True
    print(f"[worker] sinal {signum} recebido; encerrando após o job atual.", flush=True)


def main() -> int:
    signal.signal(signal.SIGTERM, _sinal)
    signal.signal(signal.SIGINT, _sinal)

    db.init()
    orfaos = db.requeue_orphans()
    if orfaos:
        print(f"[worker] {orfaos} job(s) marcados como falha: worker reiniciado no meio.",
              flush=True)

    print(f"[worker] pronto. dados em {config.DATA_HOME}", flush=True)
    while not _parar:
        try:
            job = db.claim_next_job()
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] erro ao ler a fila: {exc}", flush=True)
            time.sleep(config.WORKER_POLL_S * 5)
            continue

        if job is None:
            time.sleep(config.WORKER_POLL_S)
            continue

        print(f"[worker] executando {job['id']} ({job['tool_id']})", flush=True)
        status, codigo, erro = runner.run(job)
        db.finish_job(job["id"], status=status, exit_code=codigo, error_summary=erro)
        print(f"[worker] {job['id']} -> {status}", flush=True)

    print("[worker] encerrado.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
