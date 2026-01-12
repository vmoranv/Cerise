"""
Knowledge graph extraction helpers.
"""

from __future__ import annotations

import re

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "this",
    "that",
    "it",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
}


def extract_triples(text: str) -> list[tuple[str, str, str]]:
    """Extract lightweight (subject, predicate, object) triples."""
    if not text:
        return []
    cleaned = " ".join(text.strip().split())
    triples: list[tuple[str, str, str]] = []
    for pattern, predicate in _patterns():
        for match in pattern.finditer(cleaned):
            subject = _clean_token(match.group("subject"))
            obj = _clean_token(match.group("object"))
            if not subject or not obj:
                continue
            if subject == obj:
                continue
            triples.append((subject, predicate, obj))
    return _dedupe(triples)


def extract_entities(text: str, *, max_entities: int = 12) -> list[str]:
    """Extract lightweight entities for associative recall."""
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,32}|[\u4e00-\u9fff]{1,6}", text)
    entities: list[str] = []
    seen = set()
    for token in tokens:
        if token.lower() in _STOPWORDS:
            continue
        normalized = _normalize_entity(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        entities.append(normalized)
        if len(entities) >= max_entities:
            break
    return entities


def _patterns() -> list[tuple[re.Pattern, str]]:
    return [
        (
            re.compile(
                r"(?P<subject>[A-Za-z][A-Za-z0-9 _-]{1,32})\s+is\s+(?P<object>[^.?!]{1,40})",
                re.IGNORECASE,
            ),
            "is",
        ),
        (
            re.compile(
                r"(?P<subject>[A-Za-z][A-Za-z0-9 _-]{1,32})\s+likes\s+(?P<object>[^.?!]{1,40})",
                re.IGNORECASE,
            ),
            "likes",
        ),
        (
            re.compile(
                r"(?P<subject>[A-Za-z][A-Za-z0-9 _-]{1,32})\s+has\s+(?P<object>[^.?!]{1,40})",
                re.IGNORECASE,
            ),
            "has",
        ),
        (
            re.compile(
                r"(?P<subject>[A-Za-z][A-Za-z0-9 _-]{1,32})\s+->\s+(?P<object>[^.?!]{1,40})",
                re.IGNORECASE,
            ),
            "related_to",
        ),
        (
            re.compile(r"(?P<subject>[\u4e00-\u9fff]{1,8})是(?P<object>[\u4e00-\u9fff]{1,12})"),
            "是",
        ),
        (
            re.compile(r"(?P<subject>[\u4e00-\u9fff]{1,8})喜欢(?P<object>[\u4e00-\u9fff]{1,12})"),
            "喜欢",
        ),
        (
            re.compile(r"(?P<subject>[\u4e00-\u9fff]{1,8})有(?P<object>[\u4e00-\u9fff]{1,12})"),
            "有",
        ),
    ]


def _clean_token(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[\"'()\\[\\]{}]", "", text)
    return text.strip()


def _normalize_entity(token: str) -> str:
    token = _clean_token(token)
    if not token:
        return ""
    if re.fullmatch(r"[A-Za-z0-9_-]+", token):
        return token.lower()
    return token


def _dedupe(triples: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    seen = set()
    result = []
    for triple in triples:
        key = tuple(token.lower() for token in triple)
        if key in seen:
            continue
        seen.add(key)
        result.append(triple)
    return result
