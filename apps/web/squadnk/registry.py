"""Motor declarado como dado, não como endpoint.

Cada ferramenta é um YAML em apps/web/tools/. O formulário, a validação, a linha de
comando e a coleta de artefatos saem todos da mesma declaração — então adicionar
ferramenta é escrever um YAML, sem Python e sem HTML novos
(docs/arquitetura-web.md §7).
"""
from __future__ import annotations

import dataclasses
import pathlib
import re

import yaml

from . import config

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


class SpecError(ValueError):
    """Declaração inválida ou entrada que não satisfaz a declaração."""


@dataclasses.dataclass(frozen=True)
class Tool:
    id: str
    label: str
    subtitle: str
    capability: str
    concurrency_key: str
    timeout_s: int
    cwd: str
    interpreter: list
    script: str
    env: dict
    args: list
    derive: list
    stage: list
    inputs: list
    collect: list
    constraints: list
    stdout_artifact: dict | None
    on_success: dict | None
    help: str

    @property
    def abs_cwd(self) -> pathlib.Path:
        return config.REPO_ROOT / self.cwd


def _load_file(path: pathlib.Path) -> Tool:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    engine = raw.get("engine") or {}
    try:
        return Tool(
            id=raw["id"],
            label=raw["label"],
            subtitle=raw.get("subtitle", ""),
            capability=raw.get("capability", ""),
            concurrency_key=raw.get("concurrency_key", "cpu"),
            timeout_s=int(raw.get("timeout_s", 1800)),
            cwd=engine["cwd"],
            interpreter=list(engine.get("interpreter") or ["python3"]),
            script=engine["script"],
            env=dict(engine.get("env") or {}),
            args=list(raw.get("args") or []),
            derive=list(raw.get("derive") or []),
            stage=list(raw.get("stage") or []),
            inputs=list(raw.get("inputs") or []),
            collect=list(raw.get("collect") or []),
            constraints=list(raw.get("constraints") or []),
            stdout_artifact=raw.get("stdout_artifact") or None,
            on_success=raw.get("on_success") or None,
            help=raw.get("help", ""),
        )
    except KeyError as exc:
        raise SpecError(f"{path.name}: campo obrigatório ausente: {exc}") from exc


def load_all() -> dict:
    tools = {}
    if config.TOOLS_DIR.is_dir():
        for path in sorted(config.TOOLS_DIR.glob("*.yaml")):
            tool = _load_file(path)
            tools[tool.id] = tool
    return tools


def get(tool_id: str) -> Tool:
    tool = load_all().get(tool_id)
    if tool is None:
        raise SpecError(f"ferramenta desconhecida: {tool_id}")
    return tool


def opcoes_de(spec: dict, user_id: int | None) -> list:
    """Opções de um enum que não são fixas no YAML.

    Fonte declarada, nunca código arbitrário: o YAML diz `options_from: previews`
    e aqui existe um provedor com esse nome. Nome desconhecido devolve lista vazia
    em vez de explodir.
    """
    fonte = spec.get("options_from")
    if not fonte:
        return list(spec.get("options") or [])
    if fonte == "previews" and user_id is not None:
        from . import db
        return [linha["slug"] for linha in db.list_previews(user_id)]
    return []


def load_agents() -> list:
    """Cards do dashboard. Status vem do YAML — nenhuma integração é inventada."""
    if not config.AGENTS_FILE.is_file():
        return []
    data = yaml.safe_load(config.AGENTS_FILE.read_text(encoding="utf-8")) or {}
    return list(data.get("agents") or [])


# ------------------------------------------------------------ validação

def _as_bool(value) -> bool:
    return str(value).lower() in ("1", "true", "on", "yes", "sim")


def clean_params(tool: Tool, form: dict, user_id: int | None = None) -> dict:
    """Valida o formulário contra a declaração. Levanta SpecError com texto legível."""
    out = {}
    for spec in tool.inputs:
        name, kind = spec["name"], spec["type"]
        if kind == "file":
            continue  # tratado no upload
        if kind == "hidden":
            # Valor fixo da declaração, não do formulário. Resolvido com o
            # contexto do job na hora de montar o comando.
            out[name] = spec.get("value", "")
            continue
        # Checkbox desmarcada não é enviada pelo navegador. O formulário manda um
        # campo oculto com "0" antes dela, então o valor que vale é o ÚLTIMO —
        # sem isso, "sem legenda" nunca chegaria ao motor.
        if hasattr(form, "getlist"):
            valores = form.getlist(name)
            raw = valores[-1] if valores else None
        else:
            raw = form.get(name)
        if kind == "bool":
            out[name] = _as_bool(raw) if raw is not None else bool(spec.get("default", False))
        elif kind == "enum":
            value = (raw or spec.get("default") or "").strip()
            permitidos = opcoes_de(spec, user_id)
            if value and value not in permitidos:
                raise SpecError(f"{spec.get('label', name)}: valor inválido.")
            out[name] = value
        elif kind == "lines":
            linhas = [l.strip() for l in (raw or "").splitlines() if l.strip()]
            out[name] = linhas
        elif kind == "number":
            texto = (raw or "").strip()
            if not texto:
                out[name] = None
            else:
                try:
                    out[name] = float(texto)
                except ValueError as exc:
                    raise SpecError(f"{spec.get('label', name)}: informe um número.") from exc
        else:  # text
            out[name] = (raw or "").strip()
        padrao = spec.get("pattern")
        if padrao and out.get(name) and not re.match(padrao, str(out[name])):
            raise SpecError(spec.get("pattern_erro")
                            or f"{spec.get('label', name)}: formato inválido.")
        if spec.get("required") and not out.get(name):
            raise SpecError(f"{spec.get('label', name)}: campo obrigatório.")
    _check_constraints(tool, out)
    return out


def _check_constraints(tool: Tool, params: dict) -> None:
    for rule in tool.constraints:
        cond = rule.get("if") or {}
        if not all(params.get(k) == v for k, v in cond.items()):
            continue
        alvos = rule.get("require_any") or []
        if alvos and not any(params.get(a) for a in alvos):
            raise SpecError(rule.get("message", "Combinação de campos inválida."))


# ------------------------------------------------------------ derivação

def _derive_preview_ou_url(params: dict, spec: dict, ctx: dict) -> str:
    """Um alvo de QA a partir de duas origens possíveis.

    O motor aceita qualquer URL, inclusive `file://`. Um preview já publicado vira
    o caminho real do `index.html` que o `current` aponta; uma URL digitada vai
    como está, desde que seja http(s). Nada disso vira shell: o resultado é um
    argumento de lista.
    """
    from . import lpbuilder
    slug = (params.get(spec.get("preview_field", "preview")) or "").strip()
    if slug:
        alvo = lpbuilder.resolver_arquivo(slug, "index.html")
        if alvo is None:
            raise SpecError(f"O preview '{slug}' não tem um index.html publicado.")
        return alvo.as_uri()
    url = (params.get(spec.get("url_field", "url")) or "").strip()
    if url.startswith(("http://", "https://")):
        return url
    raise SpecError("Informe uma URL http(s) ou escolha um preview já publicado.")


DERIVADORES = {"preview_ou_url": _derive_preview_ou_url}


def aplicar_derive(tool: Tool, params: dict, ctx: dict) -> dict:
    for spec in tool.derive:
        fn = DERIVADORES.get(spec.get("using"))
        if fn is None:
            raise SpecError(f"{tool.id}: derivador desconhecido: {spec.get('using')!r}")
        ctx[spec["name"]] = fn(params, spec, ctx)
    return ctx


# ------------------------------------------------------------ linha de comando

def resolve_interpreter(tool: Tool) -> str:
    """Primeiro interpretador que existir de fato.

    Nativo: `venv/bin/python` do próprio motor. Em container: `python3` global.
    A mesma declaração serve aos dois, sem `if` espalhado pelo código.
    """
    import shutil
    for candidate in tool.interpreter:
        local = tool.abs_cwd / candidate
        if local.is_file():
            return str(local)
        found = shutil.which(candidate)
        if found:
            return found
    raise SpecError(
        f"{tool.id}: nenhum interpretador encontrado entre {tool.interpreter}. "
        f"Rode scripts/setup.sh ou use a imagem Docker."
    )


def _fmt(valor, ctx: dict) -> str:
    """Substitui {job_id}, {job_out}, {alvo}... em um valor declarado no YAML.

    Só chaves presentes no contexto são substituídas; chave ausente vira erro de
    declaração, não string vazia silenciosa.
    """
    texto = str(valor)
    if "{" not in texto:
        return texto
    try:
        return texto.format(**ctx)
    except KeyError as exc:
        raise SpecError(f"placeholder desconhecido na declaração: {exc}") from exc


def build_argv(tool: Tool, params: dict, bindings: dict, ctx: dict | None = None) -> list:
    """Monta o argv a partir da declaração.

    Os posicionais são explícitos em `args:` — um por item, na ordem em que o motor
    os espera. Cada item pode citar um parâmetro do formulário, um valor estagiado
    ou um derivado. Nada é concatenado em shell: a lista vai direto para subprocess,
    então nenhuma entrada do usuário pode virar comando.
    """
    ctx = {**(ctx or {}), **params, **bindings}
    argv = [resolve_interpreter(tool), tool.script]
    argv += [_fmt(a, ctx) for a in tool.args]

    for spec in tool.inputs:
        name, kind = spec["name"], spec["type"]
        if kind == "file":
            continue
        # Campo sem `flag` não vira opção: ele é consumido como posicional pelo
        # `args:`, ou existe só para alimentar um derivador. Emitir aqui geraria
        # argumento solto no meio da linha de comando.
        if not any(k in spec for k in ("flag", "flag_true", "flag_false")):
            continue
        value = params.get(name)
        if kind == "bool":
            flag = spec.get("flag_true") if value else spec.get("flag_false")
            if flag:
                argv.append(flag)
        elif kind == "lines":
            for item in value or []:
                argv += [spec["flag"], item]
        elif value not in (None, ""):
            if spec.get("depends_on") and not params.get(spec["depends_on"]):
                continue
            argv += [spec["flag"], _fmt(value, ctx)]
    return argv


def build_env(tool: Tool, ctx: dict) -> dict:
    """Variáveis extras para o processo do motor.

    É por aqui que o LP Builder recebe HOME=$SQUAD_DATA_HOME/home e passa a gravar
    fora do repositório, sem uma linha de mudança no motor.
    """
    return {k: _fmt(v, ctx) for k, v in tool.env.items()}


def kind_for(path: pathlib.Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT:
        return "image"
    if ext in (".json",):
        return "json"
    if ext in (".md",):
        return "markdown"
    return "file"
