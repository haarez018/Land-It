"""Parsing and scoring cache for efficiency. Avoids redundant computation."""

from __future__ import annotations

import hashlib
from typing import Any

from backend.parsers.schemas import Resume, JobDescription


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


_resume_cache: dict[str, Resume] = {}
_jd_cache: dict[str, JobDescription] = {}
_score_cache: dict[str, Any] = {}


def get_or_parse_resume(text: str) -> Resume:
    from backend.parsers.resume_parser import parse_resume_text
    key = _text_hash(text)
    if key not in _resume_cache:
        _resume_cache[key] = parse_resume_text(text)
    return _resume_cache[key]


def get_or_parse_jd(text: str) -> JobDescription:
    from backend.parsers.jd_parser import parse_jd
    key = _text_hash(text)
    if key not in _jd_cache:
        _jd_cache[key] = parse_jd(text)
    return _jd_cache[key]


def get_score_cache_key(
    resume_text: str, jd_text: str,
    role_type: str = "", seniority: str = "", company: str = "",
) -> str:
    return _text_hash(f"{resume_text}|{jd_text}|{role_type}|{seniority}|{company}")


def get_cached_score(key: str) -> Any | None:
    return _score_cache.get(key)


def set_cached_score(key: str, result: Any) -> None:
    _score_cache[key] = result


def clear_all_caches() -> None:
    _resume_cache.clear()
    _jd_cache.clear()
    _score_cache.clear()
