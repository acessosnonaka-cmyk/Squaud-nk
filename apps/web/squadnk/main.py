"""Squad NK Web — aplicação.

O web não executa motor: ele autentica, valida, enfileira e mostra. Quem executa
é o worker (docs/arquitetura-web.md §7).

Segurança do download: o arquivo é servido por **id de artefato**, nunca por caminho
vindo do navegador, e só ao dono do job. É o oposto do `lp-serve` na 8090, que expõe
a carteira inteira de clientes sem autenticação — esse problema não é reproduzido aqui.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import shutil
import subprocess

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import (FileResponse, HTMLResponse, PlainTextResponse,
                               RedirectResponse, StreamingResponse)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import auth, config, db, registry, runner

app = FastAPI(title="Squad NK Web", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(config.APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(config.APP_DIR / "templates"))

STATUS_LABEL = {"queued": "Na fila", "running": "Processando", "done": "Concluído",
                "failed": "Falhou", "canceled": "Cancelado"}
templates.env.globals["status_label"] = lambda s: STATUS_LABEL.get(s, s)
templates.env.globals["mb"] = lambda b: f"{(b or 0) / 1_048_576:.1f} MB"


@app.on_event("startup")
def _startup() -> None:
    config.ensure_dirs()
    db.init()
    criado = auth.bootstrap()
    if criado:
        print(f"[web] primeiro usuário criado a partir do ambiente: {criado}", flush=True)
    if auth.count_users() == 0:
        print("[web] AVISO: nenhum usuário existe. Crie um com:\n"
              "      python -m squadnk.cli adduser voce@empresa.com", flush=True)


# --------------------------------------------------------------- sessão

def current_user(request: Request):
    uid = request.session.get("uid")
    return auth.get_user(uid) if uid else None


def _redirect_login(request: Request) -> RedirectResponse:
    destino = request.url.path
    sufixo = f"?next={destino}" if destino not in ("/", "/login") else ""
    return RedirectResponse(f"/login{sufixo}", status_code=303)


@app.middleware("http")
async def exigir_login(request: Request, call_next):
    """Nada é público exceto o login e os estáticos. Fechado por padrão."""
    caminho = request.url.path
    if caminho.startswith("/static") or caminho in ("/login", "/healthz"):
        return await call_next(request)
    if request.session.get("uid") is None:
        return _redirect_login(request)
    return await call_next(request)


# A sessão precisa existir ANTES do guard de login rodar. O Starlette aplica os
# middlewares na ordem inversa da adição, então o SessionMiddleware é registrado
# depois do guard para ficar por fora dele.
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.require_secret(),
    max_age=config.SESSION_MAX_AGE,
    same_site="lax",
    https_only=config.COOKIE_SECURE,
)


@app.get("/healthz", response_class=PlainTextResponse)
def healthz() -> str:
    return "ok"


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/"):
    if request.session.get("uid"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html",
                                      {"next": next, "erro": None})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                 next: str = Form("/")):
    user = auth.authenticate(email, password)
    if user is None:
        return templates.TemplateResponse(
            request, "login.html",
            {"next": next, "erro": "E-mail ou senha incorretos."},
            status_code=401,
        )
    request.session.clear()
    request.session["uid"] = user["id"]
    destino = next if next.startswith("/") and not next.startswith("//") else "/"
    return RedirectResponse(destino, status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# --------------------------------------------------------------- telas

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = current_user(request)
    tools = registry.load_all()
    agentes = registry.load_agents()
    for agente in agentes:
        agente["disponivel"] = bool(agente.get("tool")) and agente.get("tool") in tools
    recentes = db.list_jobs(user["id"], limit=5)
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"user": user, "agentes": agentes, "recentes": recentes},
    )


@app.get("/tools/{tool_id}", response_class=HTMLResponse)
def tool_form(request: Request, tool_id: str, erro: str | None = None):
    try:
        tool = registry.get(tool_id)
    except registry.SpecError:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request, "tool_form.html",
        {"user": current_user(request), "tool": tool,
         "erro": erro, "max_mb": config.MAX_UPLOAD_MB},
    )


def _validar_video(caminho: pathlib.Path) -> str | None:
    """Confirma que o arquivo é mesmo um vídeo decodificável.

    Extensão não prova nada: um .mp4 pode ser qualquer coisa. O ffprobe é a
    verificação real, e é a mesma ferramenta que o motor usa depois.
    """
    if not shutil.which("ffprobe"):
        return None  # sem ffprobe, o motor avisa por conta própria
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(caminho)],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return "Não foi possível ler o arquivo (tempo esgotado)."
    if proc.returncode != 0 or not proc.stdout.strip():
        return "O arquivo não é um vídeo válido ou está corrompido."
    return None


async def _salvar_upload(upload: UploadFile, destino: pathlib.Path) -> int:
    """Grava em disco com teto de tamanho, sem carregar o arquivo na memória."""
    total = 0
    with destino.open("wb") as saida:
        while True:
            pedaco = await upload.read(1024 * 1024)
            if not pedaco:
                break
            total += len(pedaco)
            if total > config.MAX_UPLOAD_BYTES:
                saida.close()
                destino.unlink(missing_ok=True)
                raise ValueError(f"Arquivo maior que o limite de {config.MAX_UPLOAD_MB} MB.")
            saida.write(pedaco)
    return total


@app.post("/tools/{tool_id}")
async def tool_submit(request: Request, tool_id: str):
    user = current_user(request)
    try:
        tool = registry.get(tool_id)
    except registry.SpecError:
        return RedirectResponse("/", status_code=303)

    form = await request.form()

    def falhou(mensagem: str):
        return templates.TemplateResponse(
            request, "tool_form.html",
            {"user": user, "tool": tool, "erro": mensagem,
             "max_mb": config.MAX_UPLOAD_MB},
            status_code=400,
        )

    try:
        params = registry.clean_params(tool, form)
    except registry.SpecError as exc:
        return falhou(str(exc))

    job_id = db.new_job_id()
    workdir = config.JOBS_DIR / job_id
    paths = runner.prepare_workdir(workdir)

    titulo = tool.label
    try:
        for spec in tool.inputs:
            if spec["type"] != "file":
                continue
            upload = form.get(spec["name"])
            if upload is None or not getattr(upload, "filename", ""):
                raise ValueError(f"{spec.get('label', spec['name'])}: envie um arquivo.")
            extensao = pathlib.Path(upload.filename).suffix.lower()
            if extensao not in spec["accept"]:
                raise ValueError(
                    f"Formato {extensao or '(sem extensão)'} não aceito. "
                    f"Use: {', '.join(spec['accept'])}."
                )
            destino = paths["input"] / f"{spec['name']}{extensao}"
            await _salvar_upload(upload, destino)
            if spec.get("verify") == "video":
                problema = _validar_video(destino)
                if problema:
                    raise ValueError(problema)
            params[f"_{spec['name']}_nome"] = upload.filename
            titulo = f"{tool.label} · {upload.filename}"
    except ValueError as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        return falhou(str(exc))

    db.create_job(job_id=job_id, user_id=user["id"], tool_id=tool.id, title=titulo,
                  params=params, workdir=workdir, concurrency_key=tool.concurrency_key,
                  timeout_s=tool.timeout_s)
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


def _job_do_usuario(request: Request, job_id: str):
    job = db.get_job(job_id)
    user = current_user(request)
    if job is None or job["user_id"] != user["id"]:
        return None, user
    return job, user


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: str):
    job, user = _job_do_usuario(request, job_id)
    if job is None:
        return RedirectResponse("/historico", status_code=303)
    return templates.TemplateResponse(
        request, "job.html",
        {"user": user, "job": job,
         "artefatos": db.list_artifacts(job_id),
         "params": json.loads(job["params_json"])},
    )


@app.get("/jobs/{job_id}/log", response_class=PlainTextResponse)
def job_log(request: Request, job_id: str):
    job, _ = _job_do_usuario(request, job_id)
    if job is None:
        return PlainTextResponse("não encontrado", status_code=404)
    caminho = runner.job_paths(job["workdir"])["log"]
    if not caminho.is_file():
        return PlainTextResponse("(ainda sem saída)")
    return PlainTextResponse(caminho.read_text(encoding="utf-8", errors="replace"))


@app.get("/jobs/{job_id}/events")
async def job_events(request: Request, job_id: str):
    """SSE: status e log ao vivo. O funcionário precisa ver movimento durante
    os minutos de ffmpeg — recarregar a página não pode ser a única opção."""
    job, _ = _job_do_usuario(request, job_id)
    if job is None:
        return PlainTextResponse("não encontrado", status_code=404)
    caminho_log = runner.job_paths(job["workdir"])["log"]

    async def stream():
        posicao, ultimo_status = 0, None
        while True:
            if await request.is_disconnected():
                return
            atual = db.get_job(job_id)
            if atual is None:
                return
            if caminho_log.is_file():
                with caminho_log.open("r", encoding="utf-8", errors="replace") as fh:
                    fh.seek(posicao)
                    novo = fh.read()
                    posicao = fh.tell()
                for linha in novo.splitlines():
                    yield f"event: log\ndata: {linha}\n\n"
            if atual["status"] != ultimo_status:
                ultimo_status = atual["status"]
                yield f"event: status\ndata: {ultimo_status}\n\n"
            if atual["status"] in db.TERMINAL:
                yield "event: fim\ndata: fim\n\n"
                return
            await asyncio.sleep(1.0)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/artifacts/{artifact_id}")
def download(request: Request, artifact_id: int):
    """Download por id registrado no banco, nunca por caminho do navegador.

    Duas travas: o artefato tem de pertencer a um job do usuário logado, e o
    caminho resolvido tem de estar dentro do diretório `out/` daquele job.
    """
    artefato = db.get_artifact(artifact_id)
    user = current_user(request)
    if artefato is None or artefato["user_id"] != user["id"]:
        return PlainTextResponse("não encontrado", status_code=404)

    base = (pathlib.Path(artefato["workdir"]) / "out").resolve()
    caminho = (base / artefato["rel_path"]).resolve()
    if not str(caminho).startswith(str(base) + "/") or not caminho.is_file():
        return PlainTextResponse("não encontrado", status_code=404)

    return FileResponse(caminho, filename=caminho.name,
                        media_type="application/octet-stream")


@app.get("/historico", response_class=HTMLResponse)
def historico(request: Request):
    user = current_user(request)
    return templates.TemplateResponse(
        request, "history.html",
        {"user": user, "jobs": db.list_jobs(user["id"], limit=200)},
    )
