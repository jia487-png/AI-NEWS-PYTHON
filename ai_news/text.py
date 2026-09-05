from __future__ import annotations

import html
import re


_TAG_PATTERN = re.compile(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", re.I | re.S)
_MARKUP_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_FIRST_SENTENCE_PATTERN = re.compile(r"(?<=[.!?\u3002\uff01\uff1f])\s+")


def clean_text(value: str) -> str:
    """Strip HTML/entity noise and collapse whitespace."""
    if not value:
        return ""
    without_script = _TAG_PATTERN.sub(" ", value)
    without_tags = _MARKUP_PATTERN.sub(" ", without_script)
    decoded = html.unescape(without_tags)
    return _WHITESPACE_PATTERN.sub(" ", decoded).strip()


def first_sentence(value: str) -> str:
    clean = clean_text(value)
    if not clean:
        return ""
    return _FIRST_SENTENCE_PATTERN.split(clean, maxsplit=1)[0].strip()


def make_summary(value: str, title: str) -> str:
    """Return the first sentence of body copy, falling back to the title."""
    sentence = first_sentence(value)
    return sentence or title


def escape_markdown_link_text(value: str) -> str:
    return value.replace("[", r"\[").replace("]", r"\]")
