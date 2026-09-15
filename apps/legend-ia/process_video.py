#!/usr/bin/env python3
"""Motor Legend.IA: vídeo de entrada + operações opcionais (subtitles, text,
headline, cta) + estilo -> MP4 final.

O agente/skill interpreta o pedido do usuário e traduz para estes parâmetros
objetivos; o motor só executa. Operações são independentes e combináveis —
nenhuma combinação nova exige código novo.

Modos de uso:
    # Legenda automática + CTA (padrão)
    venv/bin/python process_video.py 01.mp4 --cta "CLIQUE NO BOTÃO ABAIXO"

    # Sem legenda, só uma headline no topo
    venv/bin/python process_video.py 02.mp4 --no-subtitles \\
        --headline "TRANSFORME O QUARTO DELES" --headline-style impact \\
        --headline-position topo --headline-start 0 --headline-duration 4

    # Headline + CTA, estilos independentes
    venv/bin/python process_video.py 03.mp4 --no-subtitles \\
        --headline "OFERTA ESPECIAL" --headline-style impact \\
        --cta "SAIBA MAIS" --cta-style impact

    # Legenda em estilo editorial + frase manual
    venv/bin/python process_video.py 04.mp4 --preset editorial \\
        --text "Feito à mão" --text-position inferior
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from faster_whisper import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "entrada de vídeo"
OUTPUT_DIR = PROJECT_ROOT / "entrega"
# Fontes que acompanham o projeto (não dependem do que está instalado no SO).
# Carregadas via "fontsdir" do filtro ass do FFmpeg — funciona em qualquer
# máquina/servidor sem precisar instalar nada no sistema.
FONTS_DIR = PROJECT_ROOT / "fonts"

WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_LANGUAGE = "pt"

POSITIONS = ("topo", "centro", "inferior", "acima-legenda")
DEFAULT_POSITION = "centro"

DEFAULT_CTA_DURATION = 3.0
DEFAULT_TEXT_DELAY = 0.0
DEFAULT_TEXT_HIDE_BEFORE = 0.0
DEFAULT_HEADLINE_START = 0.0

DEFAULT_PRESET = "classic"

# ---------------------------------------------------------------------------
# PRESETS: cada preset é uma linguagem visual completa. Um "role" (subtitle /
# text / headline / cta) dentro do preset controla, junto: fonte, peso,
# itálico, escala, contorno, sombra/blur e animação de entrada/saída. Um
# preset NÃO é só trocar a fonte — muda o conjunto inteiro por papel.
#
# CLASSIC preserva, valor por valor, o comportamento que já estava em
# produção antes deste recurso existir. Nunca altere os números de
# "classic" para ajustar outro preset.
# ---------------------------------------------------------------------------
PRESETS = {
    "classic": {
        "animation_kind": "none",
        "margin_lr_ratio": 0.07,
        "max_caption_chars": 44, "max_caption_duration": 4.0, "max_caption_gap": 0.6,
        "block_overlap_ms": 0,
        "roles": {
            "subtitle": {
                "font": "DejaVu Sans", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.056, "outline": 2, "shadow": 1, "blur": 0,
                "fade_in_ms": 0, "fade_out_ms": 0, "pop_ms": 0,
            },
            "text": {
                "font": "DejaVu Sans", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.056, "outline": 2, "shadow": 1, "blur": 0,
                "fade_in_ms": 0, "fade_out_ms": 0, "pop_ms": 0,
            },
            "headline": {
                "font": "DejaVu Sans", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.084, "outline": 2.4, "shadow": 1.2, "blur": 0,
                "fade_in_ms": 0, "fade_out_ms": 0, "pop_ms": 0,
            },
            "cta": {
                "font": "DejaVu Sans", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.059, "outline": 2.2, "shadow": 1, "blur": 0,
                "fade_in_ms": 0, "fade_out_ms": 0, "pop_ms": 0,
            },
        },
    },
    # PRO V1: primeira tentativa de preset "mais moderno", anterior à
    # referência visual real. Mantido apenas por preservação — não é mais a
    # direção do produto (superado por EDITORIAL/IMPACT). Não usar por
    # padrão; segue selecionável via --preset pro só por compatibilidade.
    "pro": {
        "animation_kind": "soft",
        "margin_lr_ratio": 0.07,
        "max_caption_chars": 30, "max_caption_duration": 2.6, "max_caption_gap": 0.5,
        "block_overlap_ms": 90,
        "roles": {
            "subtitle": {
                "font": "Ubuntu Sans", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.056, "outline": 2, "shadow": 1, "blur": 0,
                "fade_in_ms": 140, "fade_out_ms": 110, "pop_ms": 160,
            },
            "text": {
                "font": "Ubuntu Sans", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.056, "outline": 2, "shadow": 1, "blur": 0,
                "fade_in_ms": 0, "fade_out_ms": 0, "pop_ms": 0,
            },
            "headline": {
                "font": "Ubuntu Sans ExtraBold", "bold": 0, "italic": 0,
                "fontsize_ratio": 0.081, "outline": 2, "shadow": 1, "blur": 0,
                "fade_in_ms": 160, "fade_out_ms": 120, "pop_ms": 180,
            },
            "cta": {
                "font": "Ubuntu Sans ExtraBold", "bold": 0, "italic": 0,
                "fontsize_ratio": 0.062, "outline": 2.2, "shadow": 1, "blur": 0,
                "fade_in_ms": 220, "fade_out_ms": 0, "pop_ms": 220,
            },
        },
    },
    # EDITORIAL: linguagem sofisticada/elegante. Serifada, com suporte a
    # itálico, sombra suave (blur) no lugar de contorno grosso, movimento
    # discreto (só fade, sem "pop" de escala, sem crossfade entre blocos).
    # Fonte: Lora (Google Fonts, OFL) — Bold e Bold Italic embutidas em
    # fonts/. Pesquisada especificamente por ser serifada, com itálico real
    # e alta legibilidade em tamanhos de legenda.
    "editorial": {
        "animation_kind": "soft",
        "margin_lr_ratio": 0.07,
        "max_caption_chars": 26, "max_caption_duration": 2.0, "max_caption_gap": 0.35,
        "block_overlap_ms": 0,
        "roles": {
            "subtitle": {
                "font": "Lora", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.058, "outline": 1, "shadow": 1, "blur": 0.6,
                "fade_in_ms": 90, "fade_out_ms": 90, "pop_ms": 0,
            },
            "text": {
                "font": "Lora", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.058, "outline": 1, "shadow": 1, "blur": 0.6,
                "fade_in_ms": 90, "fade_out_ms": 90, "pop_ms": 0,
            },
            # Headline em itálico: reforça a linguagem "editorial" sem
            # depender só de tamanho/cor para se diferenciar do texto comum.
            "headline": {
                "font": "Lora", "bold": -1, "italic": -1,
                "fontsize_ratio": 0.087, "outline": 1.2, "shadow": 1, "blur": 0.5,
                "fade_in_ms": 160, "fade_out_ms": 120, "pop_ms": 0,
            },
            "cta": {
                "font": "Lora", "bold": -1, "italic": 0,
                "fontsize_ratio": 0.062, "outline": 1.4, "shadow": 1, "blur": 0.4,
                "fade_in_ms": 140, "fade_out_ms": 0, "pop_ms": 0,
            },
        },
    },
    # IMPACT: linguagem forte/publicitária. Sans-serif condensada muito
    # bold, entrada com "overshoot" de escala (90% -> 103% -> 100%) + fade +
    # leve deslocamento percebido pelo próprio overshoot. Sem itálico (não
    # combina com a linguagem). Fonte: Anton (Google Fonts, OFL) — pesquisada
    # por ser condensada, ultra-bold e muito usada em headlines/CTAs de
    # anúncio em vídeo vertical.
    "impact": {
        "animation_kind": "overshoot",
        "margin_lr_ratio": 0.07,
        "max_caption_chars": 34, "max_caption_duration": 3.0, "max_caption_gap": 0.5,
        "block_overlap_ms": 0,
        "roles": {
            "subtitle": {
                "font": "Anton", "bold": 0, "italic": 0,
                "fontsize_ratio": 0.052, "outline": 1.5, "shadow": 2, "blur": 0,
                "fade_in_ms": 70, "fade_out_ms": 70, "pop_ms": 140,
            },
            "text": {
                "font": "Anton", "bold": 0, "italic": 0,
                "fontsize_ratio": 0.052, "outline": 1.5, "shadow": 2, "blur": 0,
                "fade_in_ms": 70, "fade_out_ms": 70, "pop_ms": 140,
            },
            "headline": {
                "font": "Anton", "bold": 0, "italic": 0,
                "fontsize_ratio": 0.088, "outline": 1.5, "shadow": 2, "blur": 0,
                "fade_in_ms": 90, "fade_out_ms": 80, "pop_ms": 180,
            },
            "cta": {
                "font": "Anton", "bold": 0, "italic": 0,
                "fontsize_ratio": 0.065, "outline": 1.5, "shadow": 2, "blur": 0,
                "fade_in_ms": 90, "fade_out_ms": 0, "pop_ms": 170,
            },
        },
    },
}

# Cores por papel (semânticas, não fazem parte do preset): legenda/texto/
# headline em branco, CTA em amarelo/dourado — mantém a identidade "isto é
# clicável/acionável" estável entre presets. A diferença entre headline e
# texto é escala/peso/composição/animação, não cor.
ROLE_COLOR = {
    "subtitle": "&H00FFFFFF",
    "text": "&H00FFFFFF",
    "headline": "&H00FFFFFF",
    "cta": "&H0000FFFF",
}

# Setas reconhecidas para o efeito opcional de piscar no CTA (--cta-blink-arrows).
ARROW_CHARS = "↓⬇⇓▼▽"
TRAILING_ARROWS_RE = re.compile(
    r"\s*([" + re.escape(ARROW_CHARS) + r"](?:\s*[" + re.escape(ARROW_CHARS) + r"])*)\s*$"
)

# Correções de alta confiança para erros fonéticos comuns do Whisper em pt-BR,
# limitadas a nomes de marca/plataforma bem conhecidos. Nunca reescreve o
# conteúdo livre da fala.
TERM_CORRECTIONS = [
    (re.compile(r"\btim[ae]\s*zap\b", re.IGNORECASE), "WhatsApp"),
    (re.compile(r"\bwats?\s*app\b", re.IGNORECASE), "WhatsApp"),
    (re.compile(r"\bwhats\s*app\b", re.IGNORECASE), "WhatsApp"),
    (re.compile(r"\binsta\s*gram\b", re.IGNORECASE), "Instagram"),
    (re.compile(r"\bface\s*book\b", re.IGNORECASE), "Facebook"),
    (re.compile(r"\btik\s*tok\b", re.IGNORECASE), "TikTok"),
    (re.compile(r"\byou\s*tube\b", re.IGNORECASE), "YouTube"),
    (re.compile(r"\bcatletas?\b", re.IGNORECASE), "Cattleya"),
    (re.compile(r"\bcateleias?\b", re.IGNORECASE), "Cattleya"),
    (re.compile(r"\bval\s*kyrianas?\b", re.IGNORECASE), "Walkeriana"),
    (re.compile(r"\bprototora\b", re.IGNORECASE), "produtora"),
    (re.compile(r"\balias\b", re.IGNORECASE), "Alliance"),
    (re.compile(r"\bperdei a gente estar aqui dentro do\b", re.IGNORECASE), "hoje a gente está aqui neste"),
    (re.compile(r"\bMaravilhoso\b(?=,)"), "evento maravilhoso"),
]

# Correções de espaçamento em números/moeda (não alteram os valores em si).
NUMBER_SPACING_FIXES = [
    (re.compile(r"R\s*\$\s*"), "R$ "),
    (re.compile(r"(\d)\s+([.,])\s+(\d)"), r"\1\2\3"),
]

# Dicionário pequeno e editável de termos conhecidos (nomes próprios, cidades,
# estados, países) cuja capitalização/acentuação correta o Whisper costuma
# errar por sair tudo em minúsculas/sem acento. Chave em minúsculas e sem
# acento não é necessária — use a grafia mais comum que o Whisper produz.
# Adicione novas entradas conforme forem aparecendo nos vídeos do projeto.
KNOWN_TERMS = {
    "sao paulo": "São Paulo",
    "rio de janeiro": "Rio de Janeiro",
    "belo horizonte": "Belo Horizonte",
    "brasilia": "Brasília",
    "brasil": "Brasil",
    "joao": "João",
    "jose": "José",
    "andre": "André",
}
# Ordenado por tamanho decrescente para que frases (ex: "sao paulo") sejam
# testadas antes de qualquer palavra isolada que por acaso seja substring.
KNOWN_TERMS_PATTERNS = [
    (re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE), correct)
    for term, correct in sorted(KNOWN_TERMS.items(), key=lambda kv: -len(kv[0]))
]

# Capitaliza a letra seguinte a um ponto final/interrogação/exclamação
# dentro do próprio texto (fronteiras de frase internas a uma legenda).
MID_TEXT_SENTENCE_RE = re.compile(r"([.!?]\s+)([a-zà-ÿ])")


def capitalize_first_letter(text):
    """Maiusculiza a primeira letra do texto, preservando pontuação/espaços à frente."""
    match = re.search(r"[a-zà-ÿA-ZÀ-ÿ]", text)
    if not match or not text[match.start()].islower():
        return text
    i = match.start()
    return text[:i] + text[i].upper() + text[i + 1 :]


def review_text(text, corrections_log, capitalize_start=True):
    original = text
    for pattern, replacement in TERM_CORRECTIONS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in KNOWN_TERMS_PATTERNS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in NUMBER_SPACING_FIXES:
        text = pattern.sub(replacement, text)
    text = MID_TEXT_SENTENCE_RE.sub(lambda m: m.group(1) + m.group(2).upper(), text)
    if capitalize_start:
        text = capitalize_first_letter(text)
    if text != original:
        corrections_log.append((original, text))
    return text


def resolve_video_path(video_arg):
    arg_path = Path(video_arg).expanduser()
    if arg_path.is_absolute():
        path = arg_path.resolve()
    else:
        candidate = INPUT_DIR / arg_path
        path = (candidate if candidate.is_file() else PROJECT_ROOT / arg_path).resolve()

    if not path.is_file():
        sys.exit(
            f"ERRO: vídeo não encontrado: '{video_arg}' "
            f"(procurado em '{INPUT_DIR / video_arg}' e dentro do projeto)."
        )

    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        sys.exit(
            f"ERRO: '{path}' está fora de {PROJECT_ROOT}. "
            "Esta ferramenta só processa arquivos deste projeto."
        )
    return path


def get_video_info(video_path):
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=width,height:stream_side_data=rotation",
            "-select_streams", "v:0", "-of", "json", str(video_path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(probe.stdout)
    duration = float(data["format"]["duration"])
    stream = data["streams"][0]
    coded_w, coded_h = stream["width"], stream["height"]
    rotation = 0
    for sd in stream.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    if abs(rotation) in (90, 270):
        display_w, display_h = coded_h, coded_w
    else:
        display_w, display_h = coded_w, coded_h
    return duration, display_w, display_h, rotation


def transcribe(video_path):
    model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
    # vad_filter=False e sem initial_prompt: em vídeos reais, tanto o filtro
    # de VAD quanto um initial_prompt de vocabulário genérico já fizeram o
    # Whisper descartar (falso "sem fala") trechos inteiros de fala real,
    # gerando lacunas sem legenda. A correção de vocabulário específico fica
    # a cargo de TERM_CORRECTIONS, aplicada depois da transcrição.
    segments, info = model.transcribe(
        str(video_path),
        language=WHISPER_LANGUAGE,
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
    )
    words = []
    for seg in segments:
        for w in seg.words:
            if w.word.strip():
                words.append((w.start, w.end, w.word))
    return words, info.language


def build_captions(words, corrections_log, preset=PRESETS[DEFAULT_PRESET]):
    max_chars = preset["max_caption_chars"]
    max_duration = preset["max_caption_duration"]
    max_gap = preset["max_caption_gap"]

    raw_captions = []
    current = []
    for w in words:
        start, end, raw = w
        if not current:
            current = [w]
            continue
        cand_len = len("".join(x[2] for x in current) + raw)
        cand_duration = end - current[0][0]
        gap = start - current[-1][1]
        if cand_len > max_chars or cand_duration > max_duration or gap > max_gap:
            raw_captions.append(current)
            current = [w]
        else:
            current.append(w)
    if current:
        raw_captions.append(current)

    captions = []
    capitalize_start = True  # início do vídeo conta como início de frase
    for cap in raw_captions:
        start = cap[0][0]
        end = cap[-1][1]
        text = "".join(w[2] for w in cap).strip()
        text = review_text(text, corrections_log, capitalize_start=capitalize_start)
        # Se este bloco de legenda terminou em ./!/?, o próximo bloco começa
        # uma nova frase; caso contrário é uma continuação (não capitalizar).
        capitalize_start = bool(re.search(r"[.!?]$", text))
        captions.append((start, end, text))
    return captions


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def stack_above(base_marginv, block_fontsize, gap_fontsize):
    """MarginV de um elemento posicionado logo acima de outro, proporcional à fonte."""
    block_height = round(block_fontsize * 2.6)
    gap = round(gap_fontsize * 0.5)
    return base_marginv + block_height + gap


def apply_arrow_blink(cta_text, cta_duration, half_cycle_ms=350):
    """Aplica um efeito de piscar (alpha alternando) apenas às setas no fim do CTA.

    Se o texto não terminar com setas conhecidas (ARROW_CHARS), retorna o
    texto original sem alterações.
    """
    match = TRAILING_ARROWS_RE.search(cta_text)
    if not match:
        return cta_text
    base = cta_text[: match.start()].rstrip()
    arrows = match.group(1)

    total_ms = int(cta_duration * 1000)
    segments = []
    t = 0
    target = "FF"
    while t < total_ms:
        nxt = min(t + half_cycle_ms, total_ms)
        segments.append(f"\\t({t},{nxt},\\alpha&H{target}&)")
        target = "00" if target == "FF" else "FF"
        t = nxt
    blink_tag = "{" + "".join(segments) + "}"

    return f"{base} {blink_tag}{arrows}" if base else f"{blink_tag}{arrows}"


def build_entrance_tag(kind, fade_in_ms, fade_out_ms, pop_ms, blur=0):
    """Override tag ASS de entrada/saída, de acordo com a linguagem do preset:

    - "none": corte seco, sem tag nenhuma (CLASSIC).
    - "soft": fade (+ blur opcional), com "pop" de escala suave se pop_ms>0
      (EDITORIAL / PRO).
    - "overshoot": fade + escala que passa do 100% e volta (90% -> 103% ->
      100%), para uma entrada mais "hero"/publicitária (IMPACT).

    Retorna string vazia quando nada está ativo — nesse caso o texto da
    linha fica idêntico ao de antes deste recurso existir.
    """
    if not blur and fade_in_ms == 0 and fade_out_ms == 0 and pop_ms == 0:
        return ""
    parts = []
    if blur:
        parts.append(f"\\blur{blur}")
    if kind == "overshoot" and pop_ms > 0:
        p1 = max(1, int(pop_ms * 0.6))
        parts.append("\\fscx90\\fscy90")
        parts.append(f"\\fad({fade_in_ms},{fade_out_ms})")
        parts.append(f"\\t(0,{p1},\\fscx103\\fscy103)")
        parts.append(f"\\t({p1},{pop_ms},\\fscx100\\fscy100)")
    elif pop_ms > 0:
        parts.append("\\fscx90\\fscy90")
        parts.append(f"\\fad({fade_in_ms},{fade_out_ms})")
        parts.append(f"\\t(0,{pop_ms},\\fscx100\\fscy100)")
    else:
        parts.append(f"\\fad({fade_in_ms},{fade_out_ms})")
    return "{" + "".join(parts) + "}"


def balance_two_lines(text, max_chars_per_line):
    """Composição tipográfica simples: se o texto não couber numa linha,
    quebra em duas linhas o mais equilibradas possível (sem alterar
    nenhuma palavra). Usada só pela HEADLINE — legenda/texto continuam
    deixando o libass fazer o auto-wrap natural, priorizando leitura.
    """
    words = text.split()
    if len(words) < 2 or len(text) <= max_chars_per_line:
        return text
    candidates = [(i, " ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    valid = [c for c in candidates if len(c[1]) <= max_chars_per_line and len(c[2]) <= max_chars_per_line]
    pool = valid or candidates
    _, line1, line2 = min(pool, key=lambda c: abs(len(c[1]) - len(c[2])))
    return f"{line1}\\N{line2}"


def main():
    parser = argparse.ArgumentParser(
        description="Motor Legend.IA: transcrição opcional + legenda/texto/headline/CTA, com estilo por operação."
    )
    parser.add_argument("video", help="Nome do arquivo em 'entrada de vídeo/' (ex: 01.mp4) ou caminho dentro do projeto")
    parser.add_argument(
        "--preset", choices=list(PRESETS), default=DEFAULT_PRESET,
        help=f"Preset visual padrão para operações sem estilo próprio informado: {', '.join(PRESETS)} "
             f"(padrão: {DEFAULT_PRESET}, comportamento igual ao original)",
    )
    parser.add_argument(
        "--subtitles", dest="subtitles", action=argparse.BooleanOptionalAction, default=True,
        help="Transcrever e gerar legendas automáticas (padrão: ativado). Use --no-subtitles para pular o Whisper "
             "— também é o que fazer se o vídeo já tiver legenda queimada (o Legend não detecta nem remove legenda existente).",
    )
    parser.add_argument("--subtitles-style", default=None, choices=list(PRESETS), help="Estilo só da legenda (padrão: --preset)")

    parser.add_argument("--cta", default=None, help="Texto exato do CTA (opcional)")
    parser.add_argument("--cta-style", default=None, choices=list(PRESETS), help="Estilo só do CTA (padrão: --preset)")
    parser.add_argument(
        "--cta-position", default="acima-legenda", choices=POSITIONS,
        help="Posição do CTA (padrão: acima-legenda — empilha acima da legenda quando ela existe, "
             "ou na região inferior/safe-zone quando não existe; igual ao comportamento original)",
    )
    parser.add_argument(
        "--cta-start", type=float, default=None,
        help="Segundo em que o CTA começa. Se omitido, usa o padrão: aparece nos últimos --cta-duration segundos do vídeo.",
    )
    parser.add_argument(
        "--cta-duration", type=float, default=DEFAULT_CTA_DURATION,
        help=f"Duração do CTA em segundos — contados do final do vídeo se --cta-start não for informado, "
             f"ou a partir de --cta-start caso contrário (padrão: {DEFAULT_CTA_DURATION})",
    )
    parser.add_argument(
        "--cta-blink-arrows", action="store_true",
        help="Se o CTA terminar com setas (ex: '↓ ↓'), faz só as setas piscarem. Sem efeito se não houver setas.",
    )

    parser.add_argument(
        "--text", action="append", default=[],
        help="Frase adicional exata para sobrepor ao vídeo (opcional; repita --text para mais de uma frase, "
             "casando por ordem com --text-style/--text-position/--text-delay/--text-hide-before)",
    )
    parser.add_argument("--text-style", action="append", default=[], choices=list(PRESETS), help="Estilo da frase correspondente (padrão: --preset)")
    parser.add_argument(
        "--text-position", action="append", default=[], choices=POSITIONS,
        help=f"Posição da frase correspondente: {', '.join(POSITIONS)} (padrão: {DEFAULT_POSITION})",
    )
    parser.add_argument(
        "--text-delay", action="append", default=[], type=float,
        help=f"Segundos de vídeo antes da frase correspondente aparecer (padrão: {DEFAULT_TEXT_DELAY})",
    )
    parser.add_argument(
        "--text-hide-before", action="append", default=[], type=float,
        help=f"Segundos antes do fim do vídeo em que a frase deve desaparecer (padrão: {DEFAULT_TEXT_HIDE_BEFORE} = fica até o fim)",
    )

    parser.add_argument(
        "--headline", action="append", default=[],
        help="Chamada visual de maior hierarquia (não é legenda, não depende do Whisper). Repita --headline para "
             "mais de uma, casando por ordem com --headline-style/--headline-position/--headline-start/--headline-duration",
    )
    parser.add_argument("--headline-style", action="append", default=[], choices=list(PRESETS), help="Estilo da headline correspondente (padrão: --preset)")
    parser.add_argument(
        "--headline-position", action="append", default=[], choices=POSITIONS,
        help=f"Posição da headline correspondente (padrão: {DEFAULT_POSITION})",
    )
    parser.add_argument(
        "--headline-start", action="append", default=[], type=float,
        help=f"Segundo em que a headline correspondente começa (padrão: {DEFAULT_HEADLINE_START})",
    )
    parser.add_argument(
        "--headline-duration", action="append", default=[], type=float,
        help="Duração em segundos da headline correspondente (padrão: fica até o fim do vídeo)",
    )
    args = parser.parse_args()

    if not args.subtitles and not args.cta and not args.text and not args.headline:
        parser.error(
            "nada a fazer: mantenha a legenda (padrão) ou informe --cta, --text e/ou --headline."
        )

    video_path = resolve_video_path(args.video)
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{video_path.stem}_final.mp4"

    print(f"Lendo vídeo: {video_path}")
    duration, display_w, display_h, rotation = get_video_info(video_path)
    print(f"  duração={duration:.2f}s resolução_exibição={display_w}x{display_h} rotação={rotation}")
    print(f"  preset padrão: {args.preset}")

    captions = []
    subtitles_style = args.subtitles_style or args.preset
    if args.subtitles:
        print(f"Transcrevendo (faster-whisper, modelo={WHISPER_MODEL}, device=cpu)...")
        t0 = time.time()
        words, language = transcribe(video_path)
        print(f"  idioma detectado={language} tempo={time.time() - t0:.2f}s")

        print(f"Revisando transcrição e gerando legendas (estilo: {subtitles_style})...")
        corrections_log = []
        captions = build_captions(words, corrections_log, preset=PRESETS[subtitles_style])
        if corrections_log:
            print(f"  {len(corrections_log)} correção(ões) aplicada(s):")
            for before, after in corrections_log:
                print(f"    '{before}' -> '{after}'")
        else:
            print("  nenhuma correção necessária")
    else:
        print(
            "Legenda desativada (--no-subtitles): pulando transcrição, o Whisper não será executado. "
            "Se o vídeo já tiver legenda queimada, ela é preservada como está."
        )

    texts = []
    for i, content in enumerate(args.text):
        texts.append({
            "content": content,
            "style": args.text_style[i] if i < len(args.text_style) else args.preset,
            "position": args.text_position[i] if i < len(args.text_position) else DEFAULT_POSITION,
            "delay": args.text_delay[i] if i < len(args.text_delay) else DEFAULT_TEXT_DELAY,
            "hide_before": args.text_hide_before[i] if i < len(args.text_hide_before) else DEFAULT_TEXT_HIDE_BEFORE,
        })

    headlines = []
    for i, content in enumerate(args.headline):
        headlines.append({
            "content": content,
            "style": args.headline_style[i] if i < len(args.headline_style) else args.preset,
            "position": args.headline_position[i] if i < len(args.headline_position) else DEFAULT_POSITION,
            "start": args.headline_start[i] if i < len(args.headline_start) else DEFAULT_HEADLINE_START,
            "duration": args.headline_duration[i] if i < len(args.headline_duration) else None,
        })

    cta_style = args.cta_style or args.preset

    overlay_desc = []
    if args.cta:
        blink_note = " com setas piscando" if args.cta_blink_arrows else ""
        start_note = f"a partir de {args.cta_start:.1f}s" if args.cta_start is not None else f"últimos {args.cta_duration:.1f}s"
        overlay_desc.append(f"CTA='{args.cta}' (estilo: {cta_style}, {start_note}, {args.cta_duration:.1f}s{blink_note})")
    for h in headlines:
        dur_note = f"{h['duration']:.1f}s" if h["duration"] is not None else "até o fim"
        overlay_desc.append(
            f"headline='{h['content']}' (estilo: {h['style']}, posição: {h['position']}, "
            f"início: {h['start']:.1f}s, duração: {dur_note})"
        )
    for t in texts:
        hide_note = f", some {t['hide_before']:.1f}s antes do fim" if t["hide_before"] > 0 else ""
        overlay_desc.append(
            f"texto='{t['content']}' (estilo: {t['style']}, posição: {t['position']}, aparece em {t['delay']:.1f}s{hide_note})"
        )
    print(f"Montando operações: {'; '.join(overlay_desc) if overlay_desc else 'nenhuma'}...")

    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tmp:
        ass_path = Path(tmp.name)
    try:
        build_ass(
            args.subtitles, captions, subtitles_style,
            args.cta, args.cta_start, args.cta_duration, args.cta_blink_arrows, cta_style, args.cta_position,
            texts, headlines,
            duration, display_w, display_h, ass_path,
        )

        print(f"Renderizando vídeo final: {output_path}")
        render(video_path, ass_path, output_path)
    finally:
        ass_path.unlink(missing_ok=True)

    ok, msg = validate_output(output_path)
    if not ok:
        sys.exit(f"ERRO: validação do arquivo final falhou: {msg}")

    print(f"\nOK: vídeo final salvo em {output_path}")


def build_ass(
    subtitles_enabled, captions, subtitles_style,
    cta_text, cta_start_arg, cta_duration, cta_blink_arrows, cta_style, cta_position,
    texts, headlines,
    duration, display_w, display_h, ass_path,
):
    """texts / headlines: listas de dicts {content, style, position, ...} —
    zero ou mais itens cada, cada um com seu próprio preset/posição/tempo."""
    is_vertical = display_h > display_w
    if is_vertical:
        # Tráfego pago (Reels/Stories) reserva a faixa inferior para os
        # controles nativos do Instagram/Facebook: mantemos os ~20% mais
        # baixos do quadro livres de texto.
        base_marginv = round(display_h * 0.22)
    else:
        base_marginv = round(display_h * 0.095)

    styles = []
    dialogues = []
    style_names = set()

    def unique_style_name(base):
        name = base
        n = 1
        while name in style_names:
            n += 1
            name = f"{base}{n}"
        style_names.add(name)
        return name

    def add_style(role, preset_name, fontsize, alignment, marginv, margin_lr):
        preset = PRESETS[preset_name]
        r = preset["roles"][role]
        name = unique_style_name(role.capitalize())
        styles.append(
            f"Style: {name},{r['font']},{fontsize},{ROLE_COLOR[role]},{ROLE_COLOR[role]},"
            f"&H00000000,&H00000000,{r['bold']},{r['italic']},0,0,100,100,0,0,1,"
            f"{r['outline']},{r['shadow']},{alignment},{margin_lr},{margin_lr},{marginv},1"
        )
        return name

    def role_fontsize(preset_name, role):
        r = PRESETS[preset_name]["roles"][role]
        return round(min(display_w, display_h) * r["fontsize_ratio"])

    def entrance(preset_name, role, blur_override=None):
        preset = PRESETS[preset_name]
        r = preset["roles"][role]
        blur = r["blur"] if blur_override is None else blur_override
        return build_entrance_tag(preset["animation_kind"], r["fade_in_ms"], r["fade_out_ms"], r["pop_ms"], blur=blur)

    def position_layout(position, margin_lr_ratio):
        """Alinhamento ASS + MarginV para topo/centro/inferior. "acima-legenda"
        é tratado à parte (ver stack_over_ref), pois depende do que já foi
        posicionado antes (legenda e/ou CTA)."""
        margin_lr = round(display_w * margin_lr_ratio)
        if position == "topo":
            return 8, round(display_h * 0.08), margin_lr
        if position == "centro":
            return 5, 0, margin_lr
        return 2, base_marginv, margin_lr  # "inferior"

    # ---- SUBTITLES -------------------------------------------------------
    sub_marginv = base_marginv
    sub_fontsize = role_fontsize(subtitles_style, "subtitle")
    margin_lr_sub = round(display_w * PRESETS[subtitles_style]["margin_lr_ratio"])
    if subtitles_enabled and captions:
        style_name = add_style("subtitle", subtitles_style, sub_fontsize, 2, sub_marginv, margin_lr_sub)
        tag = entrance(subtitles_style, "subtitle")
        preset = PRESETS[subtitles_style]
        overlap_s = preset["block_overlap_ms"] / 1000.0
        last_idx = len(captions) - 1
        for i, (start, end, text) in enumerate(captions):
            if overlap_s > 0 and i < last_idx:
                end = end + overlap_s
            dialogues.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style_name},,0,0,0,,{tag}{text}")

    # Referência de empilhamento para "acima-legenda": começa na legenda (se
    # ativa) ou na posição-base/safe zone (senão) — igual ao comportamento
    # original. Depois que o CTA é posicionado, ele passa a ser a nova
    # referência para TEXT/HEADLINE que peçam "acima-legenda" (evita colisão
    # também quando o CTA está em outra posição).
    if subtitles_enabled and captions:
        stack_ref_marginv, stack_ref_fontsize = sub_marginv, sub_fontsize
    else:
        stack_ref_marginv, stack_ref_fontsize = base_marginv, 0

    def stack_over_ref(own_fontsize):
        if stack_ref_fontsize:
            return stack_above(stack_ref_marginv, stack_ref_fontsize, own_fontsize)
        return stack_ref_marginv

    # ---- CTA ---------------------------------------------------------
    if cta_text:
        cta_fontsize = role_fontsize(cta_style, "cta")
        cta_margin_lr = round(display_w * PRESETS[cta_style]["margin_lr_ratio"])
        if cta_position == "acima-legenda":
            cta_alignment, cta_marginv = 2, stack_over_ref(cta_fontsize)
        else:
            cta_alignment, cta_marginv, cta_margin_lr = position_layout(cta_position, PRESETS[cta_style]["margin_lr_ratio"])
        if cta_start_arg is not None:
            cta_start = max(0.0, min(cta_start_arg, duration))
            cta_end = min(duration, cta_start + cta_duration)
        else:
            cta_start = max(0.0, duration - cta_duration)
            cta_end = duration
        cta_render_text = (
            apply_arrow_blink(cta_text, cta_end - cta_start) if cta_blink_arrows else cta_text
        )
        style_name = add_style("cta", cta_style, cta_fontsize, cta_alignment, cta_marginv, cta_margin_lr)
        tag = entrance(cta_style, "cta")
        dialogues.append(
            f"Dialogue: 1,{ass_time(cta_start)},{ass_time(cta_end)},{style_name},,0,0,0,,{tag}{cta_render_text}"
        )
        # CTA vira a nova referência de empilhamento para TEXT/HEADLINE.
        stack_ref_marginv, stack_ref_fontsize = cta_marginv, cta_fontsize

    # ---- TEXT (camada genérica, sem composição especial) ------------------
    for t in texts:
        style_pn = t["style"]
        fontsize = role_fontsize(style_pn, "text")
        if t["position"] == "acima-legenda":
            alignment, marginv = 2, stack_over_ref(fontsize)
            margin_lr = round(display_w * PRESETS[style_pn]["margin_lr_ratio"])
        else:
            alignment, marginv, margin_lr = position_layout(t["position"], PRESETS[style_pn]["margin_lr_ratio"])
        style_name = add_style("text", style_pn, fontsize, alignment, marginv, margin_lr)
        tag = entrance(style_pn, "text")
        text_start = min(max(0.0, t["delay"]), duration)
        text_end = max(text_start, duration - max(0.0, t["hide_before"]))
        dialogues.append(
            f"Dialogue: 2,{ass_time(text_start)},{ass_time(text_end)},{style_name},,0,0,0,,{tag}{t['content']}"
        )

    # ---- HEADLINE (composição tipográfica própria: escala maior + quebra
    # de linha balanceada em até 2 linhas) ----------------------------------
    for h in headlines:
        style_pn = h["style"]
        fontsize = role_fontsize(style_pn, "headline")
        if h["position"] == "acima-legenda":
            alignment, marginv = 2, stack_over_ref(fontsize)
            margin_lr = round(display_w * PRESETS[style_pn]["margin_lr_ratio"])
        else:
            alignment, marginv, margin_lr = position_layout(h["position"], PRESETS[style_pn]["margin_lr_ratio"])
        style_name = add_style("headline", style_pn, fontsize, alignment, marginv, margin_lr)
        tag = entrance(style_pn, "headline")
        usable_width = display_w - 2 * margin_lr
        # Aproximação de largura média de glifo -- heurística, não métrica
        # exata da fonte (suficiente para decidir onde balancear a quebra).
        max_chars_per_line = max(6, int(usable_width / (fontsize * 0.52)))
        composed = balance_two_lines(h["content"], max_chars_per_line)
        h_start = min(max(0.0, h["start"]), duration)
        h_end = duration if h["duration"] is None else min(duration, h_start + h["duration"])
        h_end = max(h_start, h_end)
        dialogues.append(
            f"Dialogue: 3,{ass_time(h_start)},{ass_time(h_end)},{style_name},,0,0,0,,{tag}{composed}"
        )

    header = f"""[Script Info]
Title: Legend.IA overlays
ScriptType: v4.00+
PlayResX: {display_w}
PlayResY: {display_h}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{chr(10).join(styles)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(dialogues)}
"""
    ass_path.write_text(header, encoding="utf-8")


def render(video_path, ass_path, output_path):
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"ass={ass_path}:fontsdir={FONTS_DIR}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "copy",
            str(output_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"ERRO: falha ao renderizar vídeo com FFmpeg:\n{result.stderr[-2000:]}")


def validate_output(output_path):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "json", str(output_path)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        return False, "ffprobe falhou ao ler o arquivo final"
    types = {s["codec_type"] for s in json.loads(probe.stdout)["streams"]}
    if "video" not in types or "audio" not in types:
        return False, f"arquivo final não tem os streams esperados (encontrado: {types})"
    return True, "OK"


if __name__ == "__main__":
    main()
