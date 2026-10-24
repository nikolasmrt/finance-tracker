"""Funções puras de sanitização de texto de entrada (defesa em profundidade contra XSS/injeção)."""
import re
from collections.abc import Iterable

MAX_TAGS = 10
MAX_TAG_LENGTH = 30

_HTML_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RE = re.compile(r"\s+")
_TAG_INVALID_RE = re.compile(r"[^\w-]", re.UNICODE)
_TAG_SPLIT_RE = re.compile(r"[\s,;]+")


def clean_text(value: str) -> str:
    """Remove marcações HTML e caracteres de controle e normaliza espaços."""
    value = _HTML_TAG_RE.sub("", value)
    value = _CONTROL_RE.sub("", value)
    return _WHITESPACE_RE.sub(" ", value).strip()


def normalize_tag(raw: str) -> str | None:
    """`' #Viagem2026! '` -> `'viagem2026'`. Retorna None quando nada utilizável sobra."""
    tag = _TAG_INVALID_RE.sub("", raw.strip().lstrip("#").lower())[:MAX_TAG_LENGTH]
    return tag or None


def normalize_tags(value: str | Iterable[str] | None) -> list[str]:
    """Aceita lista ou string (`'#a #b, c'`); remove duplicatas preservando a ordem."""
    if value is None:
        return []
    items = _TAG_SPLIT_RE.split(value) if isinstance(value, str) else list(value)
    result: list[str] = []
    for item in items:
        tag = normalize_tag(str(item))
        if tag and tag not in result:
            result.append(tag)
    return result[:MAX_TAGS]


def escape_like(term: str) -> str:
    """Escapa curingas do LIKE para que a busca textual seja literal."""
    return term.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
