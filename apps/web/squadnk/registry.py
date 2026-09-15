"""Motor declarado como dado, não como endpoint.

Cada ferramenta é um YAML em apps/web/tools/. O formulário, a validação, a linha de
comando e a coleta de artefatos saem todos da mesma declaração — então adicionar
ferramenta é escrever um YAML, sem Python e sem HTML novos
(docs/arquitetura-web.md §7).
"""
from __future__ import annotations

import dataclasses
import pathlib

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
    stage: list
    inputs: list
    collect: list
    constraints: list
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
            stage=list(raw.get("stage") or []),
            inputs=list(raw.get("inputs") or []),
            collect=list(raw.get("collect") or []),
            constraints=list(raw.get("constraints") or []),
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


def load_agents() -> list:
    """Cards do dashboard. Status vem do YAML — nenhuma integração é inventada."""
    if not config.AGENTS_FILE.is_file():
        return []
    data = yaml.safe_load(config.AGENTS_FILE.read_text(encoding="utf-8")) or {}
    return list(data.get("agents") or [])


# ------------------------------------------------------------ validação

def _as_bool(value) -> bool:
    return str(value).lower() in ("1", "true", "on", "yes", "sim")


def clean_params(tool: Tool, form: dict) -> dict:
    """Valida o formulário contra a declaração. Levanta SpecError com texto legível."""
    out = {}
    for spec in tool.inputs:
        name, kind = spec["name"], spec["type"]
        if kind == "file":
            continue  # tratado no upload
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
            if value and value not in spec["options"]:
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


def build_argv(tool: Tool, params: dict, bindings: dict) -> list:
    """Monta o argv a partir da declaração. Nenhuma string é concatenada em shell:
    a lista vai direto para subprocess, então não há injeção possível."""
    argv = [resolve_interpreter(tool), tool.script]
    for key, value in bindings.items():
        argv.append(str(value))

    for spec in tool.inputs:
        name, kind = spec["name"], spec["type"]
        if kind == "file":
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
            argv += [spec["flag"], str(value)]
    return argv


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
