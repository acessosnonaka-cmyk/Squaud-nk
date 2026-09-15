"""Execução de um job: estagia a entrada, roda o motor, coleta o resultado.

O motor NÃO é reescrito nem copiado. Ele é chamado como está, no lugar onde vive
no repositório. O que o runner faz é adaptar o mundo ao contrato dele — e o contrato
do Legend IA é restritivo de propósito: `resolve_video_path()` recusa qualquer
arquivo fora de `apps/legend-ia/`. Por isso a entrada é estagiada lá dentro,
carimbada com o job_id, e o resultado é movido para fora ao final.

O carimbo resolve uma colisão real: `process_video.py` grava
`entrega/<stem>_final.mp4`. Dois funcionários enviando `01.mp4` sobrescreveriam o
vídeo um do outro (docs/arquitetura-web.md §9).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import time

from . import db, registry


def job_paths(workdir: str | pathlib.Path) -> dict:
    root = pathlib.Path(workdir)
    return {"root": root, "input": root / "input", "out": root / "out", "log": root / "job.log"}


def prepare_workdir(workdir: pathlib.Path) -> dict:
    paths = job_paths(workdir)
    paths["input"].mkdir(parents=True, exist_ok=True)
    paths["out"].mkdir(parents=True, exist_ok=True)
    return paths


def _log(handle, message: str) -> None:
    handle.write(message if message.endswith("\n") else message + "\n")
    handle.flush()


def _stage(tool: registry.Tool, job_id: str, paths: dict, log) -> tuple[dict, list]:
    """Copia as entradas para onde o motor as aceita. Devolve os binds e o que limpar."""
    bindings, temporarios = {}, []
    for rule in tool.stage:
        origem_nome = rule["from"]
        arquivos = sorted(paths["input"].glob(f"{origem_nome}.*"))
        if not arquivos:
            raise FileNotFoundError(f"entrada '{origem_nome}' não encontrada em {paths['input']}")
        origem = arquivos[0]
        destino_rel = rule["to"].format(job_id=job_id, filename=origem.name,
                                        stem=origem.stem, ext=origem.suffix)
        destino = tool.abs_cwd / destino_rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        temporarios.append(destino)
        bindings[rule["bind"]] = destino_rel.split("/", 1)[-1] if "/" in destino_rel else destino_rel
        _log(log, f"[staging] {origem.name} -> {tool.cwd}/{destino_rel}")
    return bindings, temporarios


def _collect(tool: registry.Tool, job_id: str, paths: dict, log) -> int:
    """Move os artefatos para fora do repositório e os registra no banco.

    Só o que está registrado aqui pode ser baixado depois — o download é por id de
    artefato, nunca por caminho vindo do navegador.
    """
    total = 0
    for rule in tool.collect:
        padrao = rule["glob"].format(job_id=job_id)
        for encontrado in sorted(tool.abs_cwd.glob(padrao)):
            destino = paths["out"] / encontrado.name
            shutil.move(str(encontrado), destino)
            tamanho = destino.stat().st_size
            db.add_artifact(job_id, destino.name,
                            rule.get("kind") or registry.kind_for(destino),
                            rule.get("label", destino.name), tamanho,
                            bool(rule.get("primary")))
            _log(log, f"[artefato] {destino.name} ({tamanho/1_048_576:.1f} MB)")
            total += 1
    return total


def _cleanup(temporarios: list, log) -> None:
    for caminho in temporarios:
        try:
            caminho.unlink(missing_ok=True)
            _log(log, f"[limpeza] removido {caminho.name}")
        except OSError as exc:
            _log(log, f"[limpeza] não removeu {caminho.name}: {exc}")


def run(job: dict) -> tuple[str, int | None, str | None]:
    """Executa um job. Devolve (status, exit_code, erro)."""
    job_id = job["id"]
    paths = prepare_workdir(pathlib.Path(job["workdir"]))
    temporarios = []

    with paths["log"].open("a", encoding="utf-8", errors="replace") as log:
        try:
            tool = registry.get(job["tool_id"])
            params = __import__("json").loads(job["params_json"])
            _log(log, f"=== {tool.label} · job {job_id} ===")

            bindings, temporarios = _stage(tool, job_id, paths, log)
            argv = registry.build_argv(tool, params, bindings)
            _log(log, "[comando] " + " ".join(repr(a) if " " in a else a for a in argv))
            _log(log, "")

            inicio = time.time()
            proc = subprocess.Popen(
                argv, cwd=str(tool.abs_cwd), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1,
            )
            ultimas = []
            try:
                for linha in proc.stdout:
                    log.write(linha)
                    log.flush()
                    ultimas.append(linha.rstrip())
                    del ultimas[:-30]
                codigo = proc.wait(timeout=job["timeout_s"])
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                _log(log, f"\n[erro] tempo esgotado após {job['timeout_s']}s")
                return "failed", None, f"Tempo esgotado após {job['timeout_s']}s."

            duracao = time.time() - inicio
            _log(log, f"\n[fim] código={codigo} em {duracao:.0f}s")

            if codigo != 0:
                erro = next((l for l in reversed(ultimas) if l.strip()), "")
                return "failed", codigo, erro or f"O motor terminou com código {codigo}."

            achados = _collect(tool, job_id, paths, log)
            if achados == 0:
                return "failed", codigo, "O motor terminou sem erro, mas nenhum resultado foi produzido."
            return "done", codigo, None

        except Exception as exc:  # noqa: BLE001 — qualquer falha vira job falho, com rastro
            _log(log, f"\n[erro] {type(exc).__name__}: {exc}")
            return "failed", None, f"{type(exc).__name__}: {exc}"
        finally:
            _cleanup(temporarios, log)
