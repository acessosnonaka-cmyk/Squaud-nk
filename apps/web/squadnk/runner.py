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

import os
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


def contexto(job_id: str, paths: dict) -> dict:
    """Valores que a declaração YAML pode referenciar: {job_id}, {job_out}, ..."""
    from . import config
    return {
        "job_id": job_id,
        "job_out": str(paths["out"]),
        "job_input": str(paths["input"]),
        "workdir": str(paths["root"]),
        "data_home": str(config.DATA_HOME),
    }


def _log(handle, message: str) -> None:
    handle.write(message if message.endswith("\n") else message + "\n")
    handle.flush()


def _stage(tool: registry.Tool, job_id: str, paths: dict, ctx: dict, log) -> tuple[dict, list]:
    """Copia as entradas para onde o motor as aceita. Devolve os binds e o que limpar."""
    bindings, temporarios = {}, []
    for rule in tool.stage:
        origem_nome = rule["from"]
        arquivos = sorted(paths["input"].glob(f"{origem_nome}.*"))
        if not arquivos:
            raise FileNotFoundError(f"entrada '{origem_nome}' não encontrada em {paths['input']}")
        origem = arquivos[0]
        # Um dicionário só: `ctx` já traz job_id, e repetir a chave como kwarg
        # explode com "multiple values for keyword argument".
        campos = {**ctx, "filename": origem.name, "stem": origem.stem,
                  "ext": origem.suffix}
        alvo = rule["to"].format(**campos)

        # `to` começando com placeholder de caminho vira destino ABSOLUTO no
        # diretório do job; caso contrário é relativo ao diretório do motor —
        # que é o que o Legend IA exige, porque recusa arquivo de fora.
        absoluto = alvo.startswith("/")
        destino = pathlib.Path(alvo) if absoluto else (tool.abs_cwd / alvo)
        destino.parent.mkdir(parents=True, exist_ok=True)

        if rule.get("unpack") == "zip":
            destino.mkdir(parents=True, exist_ok=True)
            n = _descompactar(origem, destino)
            _log(log, f"[staging] {origem.name} descompactado: {n} arquivo(s) -> {destino}")
        else:
            shutil.copy2(origem, destino)
            _log(log, f"[staging] {origem.name} -> {destino}")

        if not absoluto:
            temporarios.append(destino)  # só o que caiu dentro do repo precisa sumir
        bindings[rule["bind"]] = str(destino) if absoluto else (
            alvo.split("/", 1)[-1] if "/" in alvo else alvo)
    return bindings, temporarios


# Descompactação com trava: um zip pode carregar caminhos absolutos, `..` e
# symlinks apontando para fora. Nada disso é extraído.
_ZIP_MAX_ARQUIVOS = 3000
_ZIP_MAX_BYTES = 300 * 1024 * 1024


def _descompactar(origem: pathlib.Path, destino: pathlib.Path) -> int:
    import zipfile
    raiz = destino.resolve()
    total_bytes = 0
    extraidos = 0
    with zipfile.ZipFile(origem) as zf:
        membros = zf.infolist()
        if len(membros) > _ZIP_MAX_ARQUIVOS:
            raise ValueError(f"O arquivo tem {len(membros)} entradas; o limite é {_ZIP_MAX_ARQUIVOS}.")
        for info in membros:
            nome = info.filename
            if info.is_dir():
                continue
            # symlink dentro do zip: bit de tipo do modo Unix
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"O arquivo contém um link simbólico ({nome}); recusado.")
            if nome.startswith("/") or ".." in pathlib.PurePosixPath(nome).parts:
                raise ValueError(f"O arquivo contém um caminho inseguro ({nome}); recusado.")
            total_bytes += info.file_size
            if total_bytes > _ZIP_MAX_BYTES:
                raise ValueError("O conteúdo descompactado passa do limite de 300 MB.")
            alvo = (raiz / nome).resolve()
            if raiz not in alvo.parents:
                raise ValueError(f"O arquivo tentou escrever fora da pasta ({nome}); recusado.")
            alvo.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, alvo.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extraidos += 1
    if extraidos == 0:
        raise ValueError("O arquivo .zip está vazio.")
    return extraidos


def _collect(tool: registry.Tool, job_id: str, paths: dict, log) -> int:
    """Move os artefatos para fora do repositório e os registra no banco.

    Só o que está registrado aqui pode ser baixado depois — o download é por id de
    artefato, nunca por caminho vindo do navegador.
    """
    total = 0
    for rule in tool.collect:
        padrao = rule["glob"].format(job_id=job_id)
        # `base: out` colhe o que o motor já escreveu direto no diretório do job
        # (o lp_qa recebe --out apontando para lá); o padrão colhe do diretório
        # do motor e move para fora.
        raiz = paths["out"] if rule.get("base") == "out" else tool.abs_cwd
        for encontrado in sorted(raiz.glob(padrao)):
            destino = paths["out"] / encontrado.name
            if encontrado.resolve() != destino.resolve():
                shutil.move(str(encontrado), destino)
            tamanho = destino.stat().st_size
            db.add_artifact(job_id, destino.name,
                            rule.get("kind") or registry.kind_for(destino),
                            rule.get("label", destino.name), tamanho,
                            bool(rule.get("primary")))
            _log(log, f"[artefato] {destino.name} ({tamanho/1_048_576:.1f} MB)")
            total += 1
    return total


def _registrar_stdout(tool: registry.Tool, job_id: str, paths: dict,
                      linhas: list, log) -> None:
    """Guarda a saída legível do motor como artefato próprio.

    O relatório do QA é o entregável — ele não pode existir só no meio do log.
    """
    spec = tool.stdout_artifact
    if not spec:
        return
    destino = paths["out"] / spec.get("path", "saida.txt")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    db.add_artifact(job_id, destino.name, spec.get("kind", "text"),
                    spec.get("label", destino.name), destino.stat().st_size,
                    bool(spec.get("primary")))
    _log(log, f"[artefato] {destino.name} (saída do motor)")


def _cleanup(temporarios: list, log) -> None:
    for caminho in temporarios:
        try:
            caminho.unlink(missing_ok=True)
            _log(log, f"[limpeza] removido {caminho.name}")
        except OSError as exc:
            _log(log, f"[limpeza] não removeu {caminho.name}: {exc}")


def _pos_sucesso(tool: registry.Tool, job: dict, params: dict, log) -> None:
    """Efeitos declarados que só valem se o motor terminou bem.

    Lista fechada, como os derivadores: o YAML nomeia o efeito, o código decide o
    que ele faz. Nada de callback arbitrário vindo de arquivo de configuração.
    """
    acao = tool.on_success
    if not acao:
        return
    if acao.get("do") == "registrar_preview":
        slug = str(params.get(acao.get("slug_field", "slug")) or "").strip()
        if slug:
            db.upsert_preview(slug, job["user_id"], job["id"])
            _log(log, f"[preview] '{slug}' liberado para {job['user_id']} na rota autenticada")
    else:
        _log(log, f"[aviso] efeito desconhecido em on_success: {acao.get('do')!r}")


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

            ctx = contexto(job_id, paths)
            bindings, temporarios = _stage(tool, job_id, paths, ctx, log)
            registry.aplicar_derive(tool, params, ctx)
            argv = registry.build_argv(tool, params, bindings, ctx)
            extra_env = registry.build_env(tool, ctx)
            if extra_env:
                _log(log, "[ambiente] " + " ".join(f"{k}={v}" for k, v in extra_env.items()))
            _log(log, "[comando] " + " ".join(repr(a) if " " in a else a for a in argv))
            _log(log, "")

            inicio = time.time()
            ambiente = dict(os.environ)
            ambiente.update(extra_env)
            proc = subprocess.Popen(
                argv, cwd=str(tool.abs_cwd), env=ambiente, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1,
            )
            ultimas, todas = [], []
            guardar_tudo = bool(tool.stdout_artifact)
            try:
                for linha in proc.stdout:
                    log.write(linha)
                    log.flush()
                    ultimas.append(linha.rstrip())
                    del ultimas[:-30]
                    if guardar_tudo:
                        todas.append(linha.rstrip())
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

            _registrar_stdout(tool, job_id, paths, todas, log)
            _pos_sucesso(tool, job, params, log)
            achados = _collect(tool, job_id, paths, log)
            if achados == 0 and not tool.stdout_artifact:
                return "failed", codigo, "O motor terminou sem erro, mas nenhum resultado foi produzido."
            return "done", codigo, None

        except Exception as exc:  # noqa: BLE001 — qualquer falha vira job falho, com rastro
            _log(log, f"\n[erro] {type(exc).__name__}: {exc}")
            return "failed", None, f"{type(exc).__name__}: {exc}"
        finally:
            _cleanup(temporarios, log)
