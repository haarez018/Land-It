"""
Relevance ranker for raw scraped jobs.

Uses a weighted token-overlap score (title > tags > description excerpt)
plus a curated synonym map so "python developer" matches jobs tagged
"python", "django", "backend", etc. No external dependencies.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.agents.scout.scrapers.base import ScrapedJob

# ---------------------------------------------------------------------------
# Synonym / expansion map
# Each key is a query token; values are extra tokens that count as matches.
# ---------------------------------------------------------------------------
_SYNONYMS: dict[str, set[str]] = {
    # Role titles
    "developer":    {"dev", "engineer", "programmer", "coder", "developer"},
    "dev":          {"developer", "engineer", "programmer"},
    "engineer":     {"developer", "dev", "engineer", "programmer"},
    "programmer":   {"developer", "dev", "engineer", "coder"},
    # Seniority
    "senior":       {"senior", "sr", "lead", "principal", "staff"},
    "junior":       {"junior", "jr", "entry", "associate", "graduate"},
    "lead":         {"lead", "senior", "principal", "staff", "head"},
    # Frontend
    "frontend":     {"frontend", "front-end", "react", "vue", "angular", "ui", "web"},
    "react":        {"react", "reactjs", "frontend", "next", "nextjs"},
    "vue":          {"vue", "vuejs", "frontend"},
    "angular":      {"angular", "angularjs", "frontend"},
    # Backend
    "backend":      {"backend", "back-end", "api", "server", "node", "django", "rails"},
    "node":         {"node", "nodejs", "javascript", "backend", "express"},
    "django":       {"django", "python", "backend"},
    "flask":        {"flask", "python", "backend"},
    "fastapi":      {"fastapi", "python", "backend", "api"},
    # Languages
    "python":       {"python", "py", "django", "flask", "fastapi", "pandas", "numpy"},
    "javascript":   {"javascript", "js", "typescript", "ts", "node", "react", "vue"},
    "typescript":   {"typescript", "ts", "javascript", "js", "react"},
    "java":         {"java", "spring", "jvm", "kotlin"},
    "kotlin":       {"kotlin", "android", "java"},
    "swift":        {"swift", "ios", "xcode", "apple"},
    "go":           {"go", "golang"},
    "rust":         {"rust"},
    "ruby":         {"ruby", "rails"},
    "php":          {"php", "laravel", "symfony"},
    # Mobile
    "mobile":       {"mobile", "ios", "android", "react native", "flutter"},
    "ios":          {"ios", "swift", "xcode", "apple", "mobile"},
    "android":      {"android", "kotlin", "java", "mobile"},
    # Data / ML / AI  (kept tight — spark/sql alone shouldn't match "data scientist")
    "data":         {"data", "analytics", "analyst", "dataset", "pandas", "numpy"},
    "scientist":    {"scientist", "researcher", "research", "analytics", "ml", "machine learning"},
    "ml":           {"machine learning", "ml", "ai", "deep learning", "nlp", "pytorch", "tensorflow"},
    "ai":           {"ai", "ml", "llm", "gpt", "machine learning", "nlp"},
    # Cloud / DevOps
    "devops":       {"devops", "sre", "infrastructure", "platform", "ops", "cicd", "ci/cd"},
    "cloud":        {"cloud", "aws", "gcp", "azure", "kubernetes", "k8s", "docker"},
    "aws":          {"aws", "amazon", "cloud"},
    "kubernetes":   {"kubernetes", "k8s", "docker", "devops"},
    # Design
    "design":       {"design", "ui", "ux", "figma", "sketch"},
    "ux":           {"ux", "ui", "design", "product"},
    # Product
    "product":      {"product", "pm", "management"},
    "manager":      {"manager", "management", "lead", "director", "head"},
    # QA
    "qa":           {"qa", "quality", "testing", "test", "automation"},
    "testing":      {"testing", "qa", "quality", "automation"},
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w{2,}\b", text.lower())


def _expand(tokens: list[str]) -> set[str]:
    """Expand query tokens with synonyms."""
    expanded: set[str] = set(tokens)
    for t in tokens:
        expanded.update(_SYNONYMS.get(t, set()))
    return expanded


def relevance_score(query: str, job: "ScrapedJob") -> float:
    """
    Returns a 0.0–1.0+ score. Higher = more relevant.
    Weights: exact-title-phrase > title token > tag token > description word.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    expanded_query = _expand(query_tokens)

    title_tokens  = set(_tokenize(job.title or ""))
    tag_tokens    = set(_tokenize(" ".join(job.tags or [])))
    # Use only first 500 chars of description for speed
    desc_tokens   = set(_tokenize((job.description or "")[:500]))

    score = 0.0

    # Exact phrase match in title — big bonus
    if query.lower().strip() in (job.title or "").lower():
        score += len(query_tokens) * 4

    for qt in query_tokens:
        synonyms = _SYNONYMS.get(qt, {qt})
        synonyms.add(qt)

        # Title match (weight 4)
        if title_tokens & synonyms:
            score += 4
        # Tag match (weight 2)
        if tag_tokens & synonyms:
            score += 2
        # Description match (weight 0.5)
        if desc_tokens & synonyms:
            score += 0.5

    # Normalise: max possible score = len(query_tokens) * (4 + 2 + 0.5) + phrase_bonus
    max_score = len(query_tokens) * 6.5 + len(query_tokens) * 4
    return score / max_score if max_score > 0 else 0.0


def rank_jobs(
    query: str,
    jobs: list["ScrapedJob"],
    top_n: int,
    *,
    min_score: float = 0.15,
) -> list["ScrapedJob"]:
    """
    Filter and rank jobs by relevance to query.
    Jobs with score < min_score are dropped entirely.
    """
    scored = [(job, relevance_score(query, job)) for job in jobs]
    scored.sort(key=lambda x: x[1], reverse=True)
    filtered = [(j, s) for j, s in scored if s >= min_score]
    return [j for j, _ in filtered[:top_n]]
