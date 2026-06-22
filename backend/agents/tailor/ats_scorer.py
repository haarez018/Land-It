"""
All 14 individual ATS scorer functions.
Each returns (score: float, explanation: str, issues: list[str], suggestions: list[str]).
Score range: 0-100 for every function.

Day 2: keyword_density, skill_depth, quantified_impact, action_verb, bullet_quality
Day 3: tech_stack, experience_relevance, semantic_similarity, ats_parsability
Day 4: section_ordering, seniority_calibration, domain_knowledge, education_relevance, voice_alignment
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _stem(word: str) -> str:
    """Minimal suffix-stripping stemmer. Good enough for tech keyword matching."""
    w = word.lower().strip()
    for suffix in ("tion", "ing", "ment", "ness", "ence", "ance", "ity", "ous",
                    "ive", "ful", "less", "able", "ible", "ised", "ized",
                    "ises", "izes", "ers", "ors", "ies", "ed", "ly", "er", "es", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


# ── Protected terms that should NOT be stemmed (Problem 3 fix) ──────────

PROTECTED_TERMS = {
    "python", "go", "c", "c++", "c#", "r", "rust", "swift", "dart", "ruby",
    "java", "scala", "julia", "elixir", "crystal", "perl", "lua", "kotlin",
    "react", "vue", "angular", "svelte", "solid", "next.js",
    "spring", "flask", "django", "express", "rails", "fastapi",
    "kafka", "redis", "spark", "airflow", "dbt",
    "docker", "kubernetes", "terraform", "ansible",
    "aws", "gcp", "azure",
    "git", "linux", "sql", "graphql", "grpc",
}

SHORT_TERM_PATTERNS: dict[str, re.Pattern] = {
    "c": re.compile(r"\bC\b(?!\+\+|#)"),
    "r": re.compile(r"\bR\b(?!\s+&\s+D)"),
    "go": re.compile(r"\bGo(?:lang)?\b"),
}


def match_keyword(keyword: str, text: str) -> int:
    """Count keyword matches with protected-term and short-term awareness."""
    keyword_lower = keyword.lower().strip()

    if keyword_lower in SHORT_TERM_PATTERNS:
        return len(SHORT_TERM_PATTERNS[keyword_lower].findall(text))

    if keyword_lower in PROTECTED_TERMS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return len(re.findall(pattern, text, re.IGNORECASE))

    stemmed = _stem(keyword_lower)
    pattern = r"\b" + re.escape(stemmed) + r"\w*\b"
    return len(re.findall(pattern, text.lower()))


def keyword_stuffing_penalty(count: int) -> float:
    """Penalty for repeating same keyword too many times."""
    if count <= 3:
        return 0
    if count <= 5:
        return (count - 3) * 3
    return 6 + (count - 5) * 5


# ── Tiered tech similarity (Problem 4 fix) ─────────────────────────────

CATEGORY_SIMILARITY: dict[tuple[str, str], float] = {
    ("aws", "gcp"): 0.40, ("aws", "azure"): 0.40, ("gcp", "azure"): 0.40,
    ("react", "vue"): 0.35, ("react", "angular"): 0.25, ("react", "svelte"): 0.30,
    ("vue", "angular"): 0.25, ("vue", "svelte"): 0.35,
    ("django", "flask"): 0.50, ("django", "fastapi"): 0.45, ("flask", "fastapi"): 0.55,
    ("express", "fastapi"): 0.30, ("spring", "django"): 0.20,
    ("postgres", "mysql"): 0.60, ("postgresql", "mysql"): 0.60,
    ("postgres", "sqlite"): 0.50, ("postgresql", "sqlite"): 0.50,
    ("mongodb", "dynamodb"): 0.40, ("redis", "memcached"): 0.65,
    ("postgres", "mongodb"): 0.15, ("postgresql", "mongodb"): 0.15,
    ("python", "ruby"): 0.35, ("python", "javascript"): 0.25,
    ("go", "rust"): 0.30, ("java", "kotlin"): 0.55, ("java", "scala"): 0.45,
    ("javascript", "typescript"): 0.80, ("c", "c++"): 0.50, ("c++", "rust"): 0.30,
    ("docker", "podman"): 0.70, ("kubernetes", "docker_swarm"): 0.35,
    ("kafka", "rabbitmq"): 0.35, ("kafka", "pulsar"): 0.50, ("sqs", "rabbitmq"): 0.30,
    ("tensorflow", "pytorch"): 0.50, ("scikit-learn", "xgboost"): 0.45,
    ("terraform", "pulumi"): 0.50, ("terraform", "cloudformation"): 0.35,
    ("ansible", "terraform"): 0.20,
}


def tech_similarity(tech_a: str, tech_b: str) -> float:
    """Returns similarity score 0.0-1.0 between two technologies."""
    a, b = tech_a.lower().strip(), tech_b.lower().strip()
    if a == b:
        return 1.0

    score = CATEGORY_SIMILARITY.get((a, b)) or CATEGORY_SIMILARITY.get((b, a))
    if score is not None:
        return score

    for _cat, members in _TECH_CATEGORIES.items():
        members_lower = {m.lower() for m in members}
        if a in members_lower and b in members_lower:
            return 0.20
    return 0.0


# ── Verb normalization (Problem 6 fix) ──────────────────────────────────

_IRREGULAR_VERBS = {
    "led": "lead", "built": "build", "drove": "drive", "ran": "run",
    "wrote": "write", "grew": "grow", "spoke": "speak", "won": "win",
    "taught": "teach", "brought": "bring", "thought": "think",
    "made": "make", "set": "set", "cut": "cut", "put": "put",
}

PHRASAL_VERBS = {
    "set up": 2, "stood up": 2, "rolled out": 2, "scaled up": 1,
    "cut down": 2, "turned around": 1, "built out": 1, "ramped up": 2,
    "phased out": 2,
}

ROLE_VERB_ADJUSTMENTS: dict[str, dict[str, int]] = {
    "product_manager": {"managed": 2, "coordinated": 2, "prioritized": 2, "facilitated": 2},
    "research_scientist": {"researched": 1, "investigated": 1, "analyzed": 2, "studied": 2},
    "design_ux": {"designed": 1, "prototyped": 1, "wireframed": 2, "iterated": 2},
}


def normalize_verb(verb: str) -> str:
    """Reduce verb to base form for tier matching."""
    v = verb.lower().strip()
    if v in _IRREGULAR_VERBS:
        return _IRREGULAR_VERBS[v]
    if v.endswith("ed") and len(v) > 4:
        base = v[:-2] if v[-3] == v[-4] else v[:-1] if v[-2] == "e" else v[:-2]
        return base if len(base) > 2 else v
    return v


def _get_all_resume_text(resume: Resume) -> str:
    parts = [resume.raw_text]
    if resume.summary:
        parts.append(resume.summary)
    for exp in resume.work_experience:
        parts.extend(exp.bullets)
    return " ".join(parts)


def _get_all_bullets(resume: Resume) -> list[str]:
    bullets: list[str] = []
    for exp in resume.work_experience:
        bullets.extend(exp.bullets)
    return bullets


def _get_experience_text(resume: Resume) -> str:
    parts: list[str] = []
    for exp in resume.work_experience:
        parts.extend(exp.bullets)
    return " ".join(parts)


def _get_skills_section_text(resume: Resume) -> str:
    parts: list[str] = []
    for cat, skills in resume.skills.items():
        parts.extend(skills)
    return " ".join(parts)


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return float(max(lo, min(hi, val)))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. KEYWORD DENSITY & COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════

def keyword_density_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Measures what % of JD required/preferred keywords appear in the resume.
    Required keywords weighted 2x. Penalizes stuffing (>4 occurrences).
    """
    resume_text = _get_all_resume_text(resume).lower()
    resume_stems = set(_stem(w) for w in re.findall(r"\b\w+\b", resume_text))
    resume_word_counts = Counter(re.findall(r"\b\w+\b", resume_text))

    required_kws = jd.required_skills + [r.extracted_keyword for r in jd.requirements if r.category == "must_have"]
    preferred_kws = jd.preferred_skills + [r.extracted_keyword for r in jd.requirements if r.category == "nice_to_have"]

    # Deduplicate
    required_kws = list(dict.fromkeys(kw.strip() for kw in required_kws if kw.strip()))
    preferred_kws = list(dict.fromkeys(kw.strip() for kw in preferred_kws if kw.strip()))

    if not required_kws and not preferred_kws:
        return (75.0, "No specific keywords extracted from JD to compare.", [], [])

    required_found = 0
    required_missing: list[str] = []
    for kw in required_kws:
        kw_stem = _stem(kw)
        if kw.lower() in resume_text or kw_stem in resume_stems:
            required_found += 1
        else:
            required_missing.append(kw)

    preferred_found = 0
    preferred_missing: list[str] = []
    for kw in preferred_kws:
        kw_stem = _stem(kw)
        if kw.lower() in resume_text or kw_stem in resume_stems:
            preferred_found += 1
        else:
            preferred_missing.append(kw)

    # Score: required count 2x, preferred 1x
    total_weighted = len(required_kws) * 2 + len(preferred_kws)
    found_weighted = required_found * 2 + preferred_found
    raw_score = (found_weighted / total_weighted * 100) if total_weighted > 0 else 75

    # Stuffing penalty: -5 per keyword appearing >4 times
    stuffing_penalties = 0
    stuffed_words: list[str] = []
    all_kws = required_kws + preferred_kws
    for kw in all_kws:
        count = resume_word_counts.get(kw.lower(), 0)
        if count > 4:
            stuffing_penalties += 5
            stuffed_words.append(f"'{kw}' appears {count}x")

    final_score = _clamp(raw_score - stuffing_penalties)

    issues: list[str] = []
    suggestions: list[str] = []

    if required_missing:
        issues.append(f"Missing {len(required_missing)} required keywords: {', '.join(required_missing[:5])}")
        suggestions.append(f"Add these required keywords naturally in experience bullets: {', '.join(required_missing[:3])}")
    if preferred_missing:
        issues.append(f"Missing {len(preferred_missing)} preferred keywords: {', '.join(preferred_missing[:5])}")
    if stuffed_words:
        issues.append(f"Keyword stuffing detected: {'; '.join(stuffed_words[:3])}")
        suggestions.append("Reduce repeated keyword usage to 3 or fewer occurrences each")

    explanation = (
        f"Found {required_found}/{len(required_kws)} required keywords (2x weight) "
        f"and {preferred_found}/{len(preferred_kws)} preferred keywords."
    )

    return (round(final_score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SKILL DEPTH & DEMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def skill_depth_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Checks if skills are demonstrated in experience bullets (full credit)
    vs just listed in skills section (50% credit).
    Skills with quantified outcomes get +10 bonus.
    """
    target_skills = list(dict.fromkeys(
        jd.required_skills + jd.preferred_skills + jd.tech_stack
    ))
    if not target_skills:
        return (70.0, "No target skills to evaluate depth for.", [], [])

    experience_text = _get_experience_text(resume).lower()
    skills_text = _get_skills_section_text(resume).lower()

    metric_re = re.compile(r"\d+[%KMBkmb$]|\$\d+|reduced|increased|improved|saved", re.IGNORECASE)

    total_points = 0
    max_points = 0
    skills_only_listed: list[str] = []
    skills_demonstrated: list[str] = []
    skills_missing: list[str] = []

    for skill in target_skills:
        skill_lower = skill.lower()
        max_points += 100

        in_experience = skill_lower in experience_text
        in_skills = skill_lower in skills_text

        if in_experience:
            # Check if there's a quantified outcome near this skill mention
            for bullet in _get_all_bullets(resume):
                if skill_lower in bullet.lower() and metric_re.search(bullet):
                    total_points += 110  # Full + bonus
                    skills_demonstrated.append(skill)
                    break
            else:
                total_points += 100
                skills_demonstrated.append(skill)
        elif in_skills:
            total_points += 50
            skills_only_listed.append(skill)
        else:
            skills_missing.append(skill)

    score = _clamp((total_points / max_points * 100) if max_points > 0 else 70)

    issues: list[str] = []
    suggestions: list[str] = []

    if skills_only_listed:
        issues.append(f"{len(skills_only_listed)} skills listed but not demonstrated: {', '.join(skills_only_listed[:4])}")
        suggestions.append(f"Add bullets showing these skills in action: {', '.join(skills_only_listed[:3])}")
    if skills_missing:
        issues.append(f"{len(skills_missing)} target skills not found anywhere: {', '.join(skills_missing[:4])}")
        suggestions.append(f"Add these skills to relevant experience bullets: {', '.join(skills_missing[:3])}")

    explanation = (
        f"{len(skills_demonstrated)} skills demonstrated in experience, "
        f"{len(skills_only_listed)} only listed in skills section, "
        f"{len(skills_missing)} missing entirely."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TECH STACK ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════════════

_TECH_CATEGORIES = {
    "languages": {"python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
                   "ruby", "php", "swift", "kotlin", "scala", "r", "perl", "elixir", "dart"},
    "frontend_frameworks": {"react", "vue", "angular", "next.js", "svelte", "nuxt", "gatsby",
                             "remix", "tailwindcss", "bootstrap"},
    "backend_frameworks": {"django", "flask", "fastapi", "spring", "spring boot", "express",
                            "node.js", "rails", "laravel", "nestjs", "gin", "actix"},
    "databases": {"postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb",
                   "cassandra", "sqlite", "neo4j", "cockroachdb"},
    "cloud": {"aws", "gcp", "azure", "heroku", "vercel", "netlify", "digitalocean"},
    "devops": {"docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions",
               "circleci", "gitlab ci", "argocd", "helm"},
    "data_ml": {"tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "spark",
                 "hadoop", "airflow", "dbt", "mlflow", "hugging face", "langchain"},
    "messaging": {"kafka", "rabbitmq", "sqs", "pubsub", "nats"},
    "protocols": {"rest", "graphql", "grpc", "websocket"},
    "observability": {"datadog", "grafana", "prometheus", "sentry", "new relic", "splunk"},
}


def _find_tech_category(tech: str) -> Optional[str]:
    tech_lower = tech.lower()
    for category, techs in _TECH_CATEGORIES.items():
        if tech_lower in techs:
            return category
    return None


def tech_stack_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Compares JD tech stack against resume. Exact match=100%, category match=50-70%, no match=0%.
    """
    jd_techs = jd.tech_stack
    if not jd_techs:
        return (75.0, "No specific tech stack mentioned in JD.", [], [])

    resume_text = _get_all_resume_text(resume).lower()
    resume_skills_flat = []
    for skills in resume.skills.values():
        resume_skills_flat.extend(s.lower() for s in skills)
    for exp in resume.work_experience:
        resume_skills_flat.extend(t.lower() for t in exp.technologies)

    total_points = 0
    max_points = len(jd_techs) * 100
    exact_matches: list[str] = []
    category_matches: list[str] = []
    missing: list[str] = []

    for tech in jd_techs:
        tech_lower = tech.lower()

        # Exact match
        if tech_lower in resume_text or tech_lower in resume_skills_flat:
            total_points += 100
            exact_matches.append(tech)
            continue

        # Category match — does resume have something in the same category?
        jd_cat = _find_tech_category(tech)
        if jd_cat:
            cat_techs = _TECH_CATEGORIES[jd_cat]
            found_in_cat = any(t in resume_text or t in resume_skills_flat for t in cat_techs)
            if found_in_cat:
                total_points += 60
                category_matches.append(tech)
                continue

        missing.append(tech)

    score = _clamp((total_points / max_points * 100) if max_points > 0 else 70)

    issues: list[str] = []
    suggestions: list[str] = []

    if missing:
        issues.append(f"Missing {len(missing)} tech stack items: {', '.join(missing[:5])}")
        suggestions.append(f"Add experience with or mention: {', '.join(missing[:3])}")
    if category_matches:
        issues.append(f"{len(category_matches)} partial matches (same category, different tool): {', '.join(category_matches[:4])}")
        suggestions.append("Consider mentioning the exact tools from the JD if you have experience with them")

    explanation = (
        f"{len(exact_matches)} exact matches, {len(category_matches)} category matches, "
        f"{len(missing)} missing out of {len(jd_techs)} JD technologies."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EXPERIENCE RELEVANCE
# ═══════════════════════════════════════════════════════════════════════════════

def experience_relevance_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Keyword-overlap proxy for semantic similarity between JD requirements
    and experience bullets. Recency-weighted: last 2y=1.0, 2-5y=0.8, 5+=0.5.
    Falls back to keyword overlap when embeddings unavailable.
    """
    requirements = [r.text for r in jd.requirements if r.text.strip()]
    if not requirements:
        requirements = jd.role_priorities[:5] if jd.role_priorities else []
    if not requirements:
        return (60.0, "No specific requirements to match against.", [], [])

    today = date.today()
    scored_matches: list[float] = []

    for req in requirements:
        req_words = set(w.lower() for w in re.findall(r"\b\w{3,}\b", req))
        best_match = 0.0

        for exp in resume.work_experience:
            # Recency weight
            years_ago = (today - (exp.end_date or today)).days / 365.25
            if years_ago <= 2:
                recency = 1.0
            elif years_ago <= 5:
                recency = 0.8
            else:
                recency = 0.5

            for bullet in exp.bullets:
                bullet_words = set(w.lower() for w in re.findall(r"\b\w{3,}\b", bullet))
                if not req_words:
                    continue
                overlap = len(req_words & bullet_words) / len(req_words)
                weighted = overlap * recency
                best_match = max(best_match, weighted)

        scored_matches.append(best_match)

    avg_score = (sum(scored_matches) / len(scored_matches)) * 100 if scored_matches else 50
    score = _clamp(avg_score)

    weak_reqs = [requirements[i] for i, s in enumerate(scored_matches) if s < 0.3]
    issues: list[str] = []
    suggestions: list[str] = []

    if weak_reqs:
        issues.append(f"{len(weak_reqs)} requirements have weak experience match")
        for req in weak_reqs[:2]:
            suggestions.append(f"Add a bullet demonstrating: '{req[:60]}...'")

    explanation = (
        f"Average requirement-to-experience match: {avg_score:.0f}% "
        f"across {len(requirements)} requirements."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. QUANTIFIED IMPACT
# ═══════════════════════════════════════════════════════════════════════════════

_METRIC_PATTERNS = [
    (r"\$[\d,]+[KMBkmb]?", "currency", 5),
    (r"\d+\s*%", "percentage", 4),
    (r"\d+[KMBkmb]\+?\s*(?:users|requests|records|customers|transactions|events|rows|documents)",
     "scale", 4),
    (r"(?:reduced|decreased|cut|lowered)\s+.{0,40}?(?:by\s+)?\d+", "reduction", 3),
    (r"(?:increased|grew|improved|boosted|raised)\s+.{0,40}?(?:by\s+)?\d+", "increase", 3),
    (r"team\s+of\s+\d+", "team_size", 3),
    (r"#\d+|top\s+\d+\s*%", "ranking", 2),
    (r"\d+x\s+(?:faster|improvement|increase|growth)", "multiplier", 4),
]

_SENIORITY_BENCHMARKS = {
    "intern": 1, "junior": 2, "mid": 3, "senior": 5, "staff_principal": 7, "executive": 9,
}


def quantified_impact_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Counts measurable outcomes in resume bullets. Benchmarked per seniority level.
    Score based on % of bullets with metrics, plus quality bonus for variety.
    """
    bullets = _get_all_bullets(resume)
    if not bullets:
        return (20.0, "No experience bullets found.", ["No bullets to evaluate"], ["Add quantified achievements"])

    found_metrics: list[str] = []
    metric_types_seen: set[str] = set()
    quantified_count = 0
    unquantified_bullets: list[str] = []

    for bullet in bullets:
        bullet_has_metric = False
        for pattern, metric_type, _points in _METRIC_PATTERNS:
            matches = re.findall(pattern, bullet, re.IGNORECASE)
            if matches:
                bullet_has_metric = True
                metric_types_seen.add(metric_type)
                for match in matches:
                    if match.strip() not in found_metrics:
                        found_metrics.append(match.strip())
        if bullet_has_metric:
            quantified_count += 1
        else:
            unquantified_bullets.append(bullet)

    # Base score: percentage of bullets with at least one metric (0-70 pts)
    pct_quantified = quantified_count / len(bullets)
    base_score = pct_quantified * 70

    # Variety bonus: diverse metric types are better (0-20 pts)
    variety_bonus = min(len(metric_types_seen) * 5, 20)

    # Volume bonus: many distinct metrics (0-10 pts)
    volume_bonus = min(len(found_metrics) * 2, 10)

    raw_score = base_score + variety_bonus + volume_bonus

    # Benchmark against seniority
    benchmark = _SENIORITY_BENCHMARKS.get(resume.seniority_level, 3)
    metric_count = len(found_metrics)
    if metric_count < benchmark:
        penalty = (benchmark - metric_count) * 8
        raw_score = _clamp(raw_score - penalty)
    else:
        raw_score = _clamp(raw_score)

    issues: list[str] = []
    suggestions: list[str] = []

    if metric_count < benchmark:
        issues.append(
            f"Only {metric_count} quantified metrics found; "
            f"{resume.seniority_level}-level resumes should have {benchmark}+"
        )
    if unquantified_bullets:
        vague_examples = [b[:60] + "..." for b in unquantified_bullets[:3]]
        issues.append(f"{len(unquantified_bullets)} bullets lack metrics")
        suggestions.append(f"Add numbers to vague bullets like: '{vague_examples[0]}'")

    if not found_metrics:
        suggestions.append("Add $, %, or scale metrics (users, requests, records) to your top bullets")

    explanation = (
        f"Found {metric_count} quantified metrics across {len(bullets)} bullets "
        f"({quantified_count}/{len(bullets)} bullets quantified). "
        f"Benchmark for {resume.seniority_level}: {benchmark}+ metrics."
    )

    return (round(raw_score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ACTION VERB STRENGTH
# ═══════════════════════════════════════════════════════════════════════════════

_VERB_TIERS: dict[int, set[str]] = {
    1: {"architected", "spearheaded", "orchestrated", "pioneered", "transformed",
        "scaled", "automated", "generated", "revolutionized", "championed",
        "established", "launched", "engineered", "defined"},
    2: {"built", "designed", "implemented", "led", "launched", "reduced",
        "increased", "optimized", "developed", "created", "migrated",
        "integrated", "deployed", "delivered", "drove", "owned",
        "mentored", "streamlined", "consolidated"},
    3: {"created", "managed", "supported", "coordinated", "maintained",
        "configured", "wrote", "updated", "handled", "conducted",
        "prepared", "organized", "tracked", "monitored", "reviewed"},
    4: {"helped", "assisted", "participated", "was", "worked",
        "involved", "contributed", "utilized", "used", "responsible",
        "tasked", "assigned", "served"},
}

_TIER_SCORES = {1: 95, 2: 80, 3: 60, 4: 30}


def action_verb_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """Maps bullet-opening verbs to strength tiers. Score = weighted average."""
    bullets = _get_all_bullets(resume)
    if not bullets:
        return (50.0, "No bullets to evaluate.", ["No experience bullets found"], [])

    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    weak_verbs: list[str] = []
    total_scored = 0

    for bullet in bullets:
        words = bullet.strip().split()
        if not words:
            continue
        first_word = words[0].lower().rstrip("ed").rstrip("ing")
        # Also check the original form
        first_orig = words[0].lower()

        found_tier = 0
        for tier, verbs in _VERB_TIERS.items():
            if first_orig in verbs or first_word in verbs:
                found_tier = tier
                break

        if found_tier == 0:
            # Unknown verb — default to tier 3
            found_tier = 3

        tier_counts[found_tier] += 1
        total_scored += 1

        if found_tier >= 4:
            weak_verbs.append(f"'{words[0]}' in: \"{bullet[:50]}...\"")

    if total_scored == 0:
        return (50.0, "No scorable bullets.", [], [])

    weighted_sum = sum(tier_counts[t] * _TIER_SCORES[t] for t in tier_counts)
    score = _clamp(weighted_sum / total_scored)

    issues: list[str] = []
    suggestions: list[str] = []

    if tier_counts[4] > 0:
        issues.append(f"{tier_counts[4]} bullets start with weak Tier 4 verbs")
        for wv in weak_verbs[:3]:
            suggestions.append(f"Replace weak verb: {wv}")
    if tier_counts[3] > tier_counts[1] + tier_counts[2]:
        issues.append("More average verbs (Tier 3) than strong verbs (Tier 1-2)")
        suggestions.append("Upgrade verbs: 'Created' -> 'Architected', 'Managed' -> 'Led'")

    explanation = (
        f"Verb tiers: {tier_counts[1]} Tier1, {tier_counts[2]} Tier2, "
        f"{tier_counts[3]} Tier3, {tier_counts[4]} Tier4 across {total_scored} bullets."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SECTION ORDERING
# ═══════════════════════════════════════════════════════════════════════════════

_OPTIMAL_ORDERS = {
    "software_engineer_backend": ["experience", "skills", "projects", "education", "certifications"],
    "software_engineer_frontend": ["experience", "skills", "projects", "education", "certifications"],
    "ml_engineer": ["experience", "skills", "projects", "education", "publications"],
    "product_manager": ["experience", "skills", "education", "certifications"],
    "data_scientist": ["experience", "education", "skills", "publications", "projects"],
    "devops_sre": ["experience", "skills", "certifications", "projects", "education"],
    "research_scientist": ["publications", "education", "experience", "skills", "awards"],
    "design_ux": ["experience", "skills", "projects", "education"],
}

_SENIORITY_OVERRIDES = {
    "intern": ["education", "projects", "skills", "experience"],
    "junior": ["education", "experience", "projects", "skills"],
}


def section_ordering_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """Score whether resume sections follow optimal order for the role type."""
    role_type = jd.infer_role_type()

    # Use seniority override for juniors/interns
    if resume.seniority_level in _SENIORITY_OVERRIDES:
        optimal = _SENIORITY_OVERRIDES[resume.seniority_level]
    else:
        optimal = _OPTIMAL_ORDERS.get(role_type, _OPTIMAL_ORDERS["software_engineer_backend"])

    # Detect actual section order from resume raw text
    section_positions: dict[str, int] = {}
    text_lower = resume.raw_text.lower()

    section_keywords = {
        "experience": ["experience", "work experience", "professional experience", "employment"],
        "education": ["education", "academic"],
        "skills": ["skills", "technical skills", "core competencies", "technologies"],
        "projects": ["projects", "personal projects", "side projects"],
        "certifications": ["certifications", "certificates"],
        "publications": ["publications", "papers"],
        "awards": ["awards", "honors"],
    }

    for section, keywords in section_keywords.items():
        for kw in keywords:
            pos = text_lower.find(kw)
            if pos >= 0:
                if section not in section_positions or pos < section_positions[section]:
                    section_positions[section] = pos
                break

    actual_order = sorted(
        [s for s in optimal if s in section_positions],
        key=lambda s: section_positions[s]
    )

    if not actual_order:
        return (70.0, "Could not detect section ordering.", [], [])

    # Count misplacements
    misplacements = 0
    misplaced_sections: list[str] = []
    for i, section in enumerate(actual_order):
        if section in optimal:
            expected_idx = optimal.index(section)
            actual_idx = i
            if actual_idx != expected_idx and abs(actual_idx - expected_idx) > 1:
                misplacements += 1
                misplaced_sections.append(section)

    score = _clamp(100 - misplacements * 8)

    issues: list[str] = []
    suggestions: list[str] = []

    if misplaced_sections:
        issues.append(f"{len(misplaced_sections)} sections out of optimal order: {', '.join(misplaced_sections)}")
        suggestions.append(f"Recommended order for {role_type}: {' > '.join(optimal)}")

    explanation = (
        f"Detected order: {' > '.join(actual_order)}. "
        f"Optimal for {role_type}: {' > '.join(optimal)}. "
        f"{misplacements} misplaced."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. BULLET POINT QUALITY
# ═══════════════════════════════════════════════════════════════════════════════

_CAR_INDICATORS = {
    "context": re.compile(r"\b(?:at|for|during|while|when|within|across)\b", re.IGNORECASE),
    "action": re.compile(r"^[A-Z][a-z]+ed\b|^[A-Z][a-z]+ing\b|^[A-Z][a-z]+d\b", re.IGNORECASE),
    "result": re.compile(
        r"\b(?:resulting|leading to|which|achieving|saving|reducing|increasing|improving|"
        r"enabling|delivering)\b|\d+[%$KMB]",
        re.IGNORECASE,
    ),
}


def bullet_quality_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Score each bullet on 4 sub-criteria (25pts each):
    1. CAR format presence
    2. Length (40-120 chars ideal)
    3. Starts with strong action verb
    4. Contains specific noun (technology, metric, proper name)
    """
    bullets = _get_all_bullets(resume)
    if not bullets:
        return (30.0, "No bullets to evaluate.", ["No experience bullets found"], ["Add bullet points to experience"])

    bullet_scores: list[float] = []
    short_bullets: list[str] = []
    long_bullets: list[str] = []
    weak_starts: list[str] = []
    vague_bullets: list[str] = []

    for bullet in bullets:
        sub_score = 0.0

        # 1. CAR format (25 pts)
        car_parts = sum(1 for ind in _CAR_INDICATORS.values() if ind.search(bullet))
        sub_score += min(car_parts / 3 * 25, 25)

        # 2. Length (25 pts) — ideal 40-120 chars
        blen = len(bullet)
        if 40 <= blen <= 120:
            sub_score += 25
        elif 20 <= blen < 40 or 120 < blen <= 180:
            sub_score += 15
        else:
            sub_score += 5
            if blen < 20:
                short_bullets.append(bullet[:40])
            elif blen > 180:
                long_bullets.append(bullet[:40] + "...")

        # 3. Starts with strong verb (25 pts)
        first_word = bullet.split()[0].lower() if bullet.split() else ""
        verb_tier = 3
        for tier, verbs in _VERB_TIERS.items():
            if first_word in verbs:
                verb_tier = tier
                break
        verb_score = {1: 25, 2: 20, 3: 15, 4: 5}.get(verb_tier, 10)
        sub_score += verb_score
        if verb_tier >= 4:
            weak_starts.append(f"'{first_word}' in: \"{bullet[:40]}...\"")

        # 4. Contains specific noun (25 pts)
        has_tech = bool(re.search(
            r"\b(?:Python|Java|React|AWS|Docker|Kubernetes|PostgreSQL|Redis|Kafka|"
            r"API|SQL|CI/CD|microservice|pipeline|dashboard|platform|system)\b",
            bullet, re.IGNORECASE
        ))
        has_metric = bool(re.search(r"\d+", bullet))
        has_proper = bool(re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", bullet))
        specificity = sum([has_tech, has_metric, has_proper])
        if specificity >= 2:
            sub_score += 25
        elif specificity == 1:
            sub_score += 15
        else:
            sub_score += 5
            vague_bullets.append(bullet[:50] + "...")

        bullet_scores.append(sub_score)

    avg_score = sum(bullet_scores) / len(bullet_scores) if bullet_scores else 50
    score = _clamp(avg_score)

    issues: list[str] = []
    suggestions: list[str] = []

    if short_bullets:
        issues.append(f"{len(short_bullets)} bullets are too short (<20 chars)")
    if long_bullets:
        issues.append(f"{len(long_bullets)} bullets are too long (>180 chars)")
    if weak_starts:
        issues.append(f"{len(weak_starts)} bullets start with weak verbs")
        suggestions.append(f"Fix: {weak_starts[0]}" if weak_starts else "")
    if vague_bullets:
        issues.append(f"{len(vague_bullets)} bullets lack specific nouns or metrics")
        suggestions.append("Add technology names, metrics, or proper nouns to vague bullets")

    explanation = (
        f"Average bullet quality: {avg_score:.0f}/100 across {len(bullets)} bullets. "
        f"Scoring: CAR format, length, verb strength, specificity."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ATS PARSABILITY
# ═══════════════════════════════════════════════════════════════════════════════

_STANDARD_HEADINGS = {
    "experience", "work experience", "professional experience", "employment",
    "education", "skills", "technical skills", "projects", "certifications",
    "summary", "professional summary", "objective", "awards", "publications",
    "languages", "interests", "volunteer",
}


def ats_parsability_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Structural checks for ATS compatibility.
    Proxied through text extraction quality since we can't render the PDF.
    """
    raw = resume.raw_text
    score = 100.0
    issues: list[str] = []
    suggestions: list[str] = []

    # 1. No tables detected (+20) — check for tab-separated columns
    tab_lines = sum(1 for line in raw.split("\n") if "\t" in line and line.count("\t") >= 2)
    if tab_lines > 3:
        score -= 20
        issues.append("Possible table/column layout detected (multiple tab-separated lines)")
        suggestions.append("Use a single-column resume format for ATS compatibility")

    # 2. Standard section headings (+20)
    found_standard = 0
    found_creative = 0
    for line in raw.split("\n"):
        line_clean = line.strip().lower().rstrip(":")
        if line_clean in _STANDARD_HEADINGS:
            found_standard += 1
        elif len(line_clean) < 30 and line_clean.isupper() and len(line_clean) > 3:
            found_creative += 1
    if found_standard < 2:
        score -= 20
        issues.append("Few standard section headings detected")
        suggestions.append("Use standard headings: Experience, Education, Skills, Projects")

    # 3. Contact info in top section (+15)
    first_200 = raw[:200].lower()
    has_email_top = bool(re.search(r"[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z]+", first_200))
    if not has_email_top:
        score -= 15
        issues.append("Email not found in top section")
        suggestions.append("Place contact info (email, phone) at the very top of the resume")

    # 4. Date format consistency (+10)
    dates_mmyyyy = len(re.findall(r"\d{1,2}/\d{4}", raw))
    dates_monthyear = len(re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}", raw))
    if dates_mmyyyy > 0 and dates_monthyear > 0:
        score -= 10
        issues.append("Inconsistent date formats (both MM/YYYY and Month YYYY used)")
        suggestions.append("Use one consistent date format throughout")

    # 5. Readable text extraction (+15) — if raw text is very short relative to a normal resume, parsing failed
    if len(raw) < 200:
        score -= 15
        issues.append("Very little text extracted — possible parsing issue or image-based resume")
        suggestions.append("Ensure resume is text-based, not a scanned image")

    # 6. No graphics/special chars (+10)
    special_chars = sum(1 for c in raw if ord(c) > 127 and c not in "—–''""•●")
    if special_chars > 20:
        score -= 10
        issues.append(f"Many special/unicode characters detected ({special_chars})")
        suggestions.append("Remove decorative characters and icons for ATS compatibility")

    score = _clamp(score)

    explanation = (
        f"ATS parsability score based on structural checks. "
        f"Found {found_standard} standard headings, "
        f"email {'found' if has_email_top else 'missing'} in header."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SENIORITY CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════

_SENIORITY_LEVELS = ["intern", "junior", "mid", "senior", "staff_principal", "executive"]


def seniority_calibration_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Checks if resume signals match JD's expected seniority.
    Overshoot and undershoot both penalized.
    """
    jd_seniority = jd.seniority_level
    resume_seniority = resume.seniority_level

    if jd_seniority not in _SENIORITY_LEVELS:
        jd_seniority = "mid"
    if resume_seniority not in _SENIORITY_LEVELS:
        resume_seniority = "mid"

    jd_idx = _SENIORITY_LEVELS.index(jd_seniority)
    resume_idx = _SENIORITY_LEVELS.index(resume_seniority)
    gap = abs(jd_idx - resume_idx)

    if gap == 0:
        score = 100.0
    elif gap == 1:
        score = 80.0
    elif gap == 2:
        score = 55.0
    else:
        score = max(20.0, 100 - gap * 25)

    issues: list[str] = []
    suggestions: list[str] = []

    if resume_idx > jd_idx + 1:
        issues.append(f"Resume signals {resume_seniority} level, but JD targets {jd_seniority}")
        suggestions.append("Tone down leadership language and focus on IC contributions")
    elif resume_idx < jd_idx - 1:
        issues.append(f"Resume signals {resume_seniority} level, but JD targets {jd_seniority}")
        suggestions.append("Emphasize leadership, scope, and strategic impact in your bullets")

    # Check YoE alignment
    if jd.required_experience_years:
        if resume.total_yoe < jd.required_experience_years * 0.7:
            score = _clamp(score - 15)
            issues.append(
                f"Resume shows {resume.total_yoe:.1f} YoE, JD requires {jd.required_experience_years}+"
            )
        elif resume.total_yoe > jd.required_experience_years * 2:
            score = _clamp(score - 10)
            issues.append(
                f"Resume shows {resume.total_yoe:.1f} YoE, may be overqualified for {jd.required_experience_years}+ requirement"
            )

    explanation = (
        f"Resume seniority: {resume_seniority}, JD target: {jd_seniority}. "
        f"Gap: {gap} level(s). YoE: {resume.total_yoe:.1f}."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. DOMAIN & INDUSTRY KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════════════

_DOMAIN_KEYWORDS = {
    "fintech": ["payments", "banking", "financial", "trading", "compliance", "pci", "kyc", "aml",
                 "transactions", "ledger", "settlement", "fintech"],
    "healthtech": ["healthcare", "hipaa", "clinical", "ehr", "patient", "medical", "fda",
                    "health", "diagnosis", "pharmaceutical"],
    "edtech": ["education", "learning", "curriculum", "lms", "student", "academic", "course",
               "teaching", "edtech"],
    "e-commerce": ["e-commerce", "ecommerce", "retail", "catalog", "inventory", "checkout",
                    "cart", "marketplace", "shopify", "product listing"],
    "saas_b2b": ["saas", "b2b", "enterprise", "subscription", "arr", "churn", "onboarding",
                  "tenant", "multi-tenant"],
    "gaming": ["game", "gaming", "unity", "unreal", "multiplayer", "real-time", "render"],
    "ai_ml": ["machine learning", "deep learning", "nlp", "llm", "ai", "neural network",
              "model training", "inference", "transformer"],
}


def domain_knowledge_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """Score alignment between JD's domain context and resume's domain experience."""
    jd_text = jd.raw_text.lower()
    resume_text = _get_all_resume_text(resume).lower()

    # Detect JD domains
    jd_domains: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in jd_text)
        if count > 0:
            jd_domains[domain] = count

    if not jd_domains:
        return (75.0, "No specific domain detected in JD.", [], [])

    # Check resume for same domains
    resume_domains: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in resume_text)
        if count > 0:
            resume_domains[domain] = count

    matched_domains = set(jd_domains.keys()) & set(resume_domains.keys())
    total_jd_domains = len(jd_domains)

    if total_jd_domains == 0:
        score = 75.0
    elif len(matched_domains) == total_jd_domains:
        score = 95.0
    elif len(matched_domains) > 0:
        score = 60.0 + (len(matched_domains) / total_jd_domains) * 35
    else:
        score = 40.0

    issues: list[str] = []
    suggestions: list[str] = []
    missing_domains = set(jd_domains.keys()) - matched_domains

    if missing_domains:
        issues.append(f"No experience in JD domains: {', '.join(missing_domains)}")
        for d in list(missing_domains)[:2]:
            relevant_kws = _DOMAIN_KEYWORDS.get(d, [])[:3]
            suggestions.append(f"Add {d} domain terminology: {', '.join(relevant_kws)}")

    explanation = (
        f"JD domains: {', '.join(jd_domains.keys())}. "
        f"Resume matches: {', '.join(matched_domains) if matched_domains else 'none'}."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. EDUCATION RELEVANCE
# ═══════════════════════════════════════════════════════════════════════════════

_DEGREE_LEVELS = {"associate": 1, "bachelor": 2, "b.s.": 2, "b.a.": 2, "b.e.": 2,
                   "b.tech": 2, "b.sc": 2, "bs ": 2, "ba ": 2, "be ": 2,
                   "master": 3, "m.s.": 3, "m.a.": 3, "ms ": 3, "ma ": 3,
                   "m.e.": 3, "m.tech": 3, "m.sc": 3, "mba": 3,
                   "ph.d": 4, "phd": 4, "doctorate": 4, "doctor": 4}

_RELEVANT_FIELDS = {
    "software_engineer_backend": ["computer science", "software", "cs", "engineering", "math"],
    "software_engineer_frontend": ["computer science", "software", "cs", "design", "hci"],
    "ml_engineer": ["computer science", "machine learning", "statistics", "math", "data science"],
    "data_scientist": ["statistics", "mathematics", "data science", "computer science", "physics"],
    "product_manager": ["business", "mba", "computer science", "engineering", "economics"],
    "research_scientist": ["computer science", "physics", "mathematics", "statistics"],
    "design_ux": ["design", "hci", "human-computer", "cognitive", "psychology"],
    "devops_sre": ["computer science", "engineering", "information technology", "cs"],
}


def education_relevance_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """Score education relevance only when JD specifies requirements."""
    if not jd.required_education and not any(
        "degree" in r.text.lower() or "education" in r.text.lower()
        for r in jd.requirements
    ):
        # JD doesn't care about education — return neutral
        return (75.0, "JD does not specify education requirements.", [], [])

    if not resume.education:
        return (30.0, "No education found on resume.", ["No education section"], ["Add education details"])

    role_type = jd.infer_role_type()
    relevant_fields = _RELEVANT_FIELDS.get(role_type, ["computer science", "engineering"])

    best_score = 0.0
    issues: list[str] = []
    suggestions: list[str] = []

    for edu in resume.education:
        sub_score = 0.0

        # Degree level (40 pts)
        degree_lower = edu.degree.lower()
        degree_level = 0
        for key, level in _DEGREE_LEVELS.items():
            if key in degree_lower:
                degree_level = max(degree_level, level)
        if degree_level >= 3:
            sub_score += 40
        elif degree_level >= 2:
            sub_score += 30
        elif degree_level >= 1:
            sub_score += 15

        # Field relevance (30 pts)
        field_lower = (edu.field + " " + edu.degree).lower()
        if any(f in field_lower for f in relevant_fields):
            sub_score += 30
        elif any(f in field_lower for f in ["science", "engineering", "technology"]):
            sub_score += 15

        # GPA (10 pts)
        if edu.gpa and edu.gpa >= 3.5:
            sub_score += 10
        elif edu.gpa and edu.gpa >= 3.0:
            sub_score += 5

        # Honors (10 pts)
        if edu.honors:
            sub_score += 10

        # Relevant coursework (10 pts)
        if edu.relevant_courses:
            sub_score += 10

        best_score = max(best_score, sub_score)

    score = _clamp(best_score)

    if score < 50:
        issues.append("Education does not strongly align with role requirements")
        suggestions.append("Add relevant coursework or highlight applicable degree aspects")

    explanation = (
        f"Best education match: {score:.0f}/100. "
        f"Evaluated degree level, field relevance, GPA, honors, coursework."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. CONTENT ALIGNMENT (keyword overlap proxy)
# ═══════════════════════════════════════════════════════════════════════════════

def content_alignment_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Keyword-overlap proxy for content alignment.
    Computes Jaccard-like similarity between resume and JD at 3 levels:
    1. Full text (0.4 weight)
    2. Requirements vs experience (0.4 weight)
    3. Role summary vs resume summary (0.2 weight)
    """
    def _jaccard_words(text_a: str, text_b: str) -> float:
        words_a = set(w.lower() for w in re.findall(r"\b\w{3,}\b", text_a))
        words_b = set(w.lower() for w in re.findall(r"\b\w{3,}\b", text_b))
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    # 1. Full text similarity
    full_sim = _jaccard_words(resume.raw_text, jd.raw_text)

    # 2. Requirements vs experience
    req_text = " ".join(r.text for r in jd.requirements)
    exp_text = _get_experience_text(resume)
    req_sim = _jaccard_words(req_text, exp_text)

    # 3. Summary vs role description
    summary_text = resume.summary or ""
    role_text = " ".join(jd.role_priorities[:3]) if jd.role_priorities else jd.raw_text[:500]
    sum_sim = _jaccard_words(summary_text, role_text)

    weighted = full_sim * 0.4 + req_sim * 0.4 + sum_sim * 0.2
    # Normalize: Jaccard for long texts typically ranges 0.05-0.25
    # Map to 0-100 scale
    score = _clamp(weighted * 400)

    issues: list[str] = []
    suggestions: list[str] = []

    if score < 50:
        issues.append("Low semantic overlap between resume and JD")
        suggestions.append("Mirror more of the JD's language and terminology in your resume")
    if sum_sim < 0.05 and summary_text:
        issues.append("Resume summary has weak connection to role description")
        suggestions.append("Rewrite your summary to directly address the role's top priorities")

    explanation = (
        f"Semantic similarity (keyword overlap): "
        f"full={full_sim:.2f}, req-vs-exp={req_sim:.2f}, summary={sum_sim:.2f}. "
        f"Weighted: {weighted:.2f}."
    )

    return (round(score, 1), explanation, issues, suggestions)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. NARRATIVE VOICE & CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

def voice_alignment_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Score narrative coherence with heuristics based on structural analysis.
    Starts at 50 — points are earned by positive signals, not assumed by default.
    """
    score = 50.0  # Base score — must be earned
    issues: list[str] = []
    suggestions: list[str] = []

    experiences = resume.work_experience

    # 1. Career trajectory — are roles progressing or random?
    if len(experiences) >= 2:
        titles = [e.title.lower() for e in experiences]
        # Check for progression signals
        progression_words = ["senior", "lead", "principal", "staff", "director", "head", "vp", "manager"]
        progression_score = 0
        for i, title in enumerate(titles):
            for pw in progression_words:
                if pw in title:
                    # Later positions should have higher-level titles
                    progression_score += (len(titles) - i)
                    break
        if progression_score > 0:
            score += 10

    # 2. Summary matches experience
    if resume.summary:
        summary_lower = resume.summary.lower()
        exp_techs = set()
        for exp in experiences:
            exp_techs.update(t.lower() for t in exp.technologies)
        summary_techs = set(re.findall(r"\b\w+\b", summary_lower)) & exp_techs
        if len(summary_techs) >= 2:
            score += 5
        elif resume.summary and not summary_techs:
            score -= 5
            issues.append("Summary mentions technologies not found in experience")
            suggestions.append("Align summary with your actual experience and tech stack")

    # 3. Consistent theme
    if experiences:
        all_techs = []
        for exp in experiences:
            all_techs.extend(t.lower() for t in exp.technologies)
        tech_counts = Counter(all_techs)
        if tech_counts:
            most_common = tech_counts.most_common(3)
            if most_common[0][1] >= 2:
                score += 5  # Consistent theme detected

    # 4. YoE consistency check
    if experiences:
        stated_yoe = resume.total_yoe
        if resume.summary and re.search(r"(\d+)\+?\s*years?", resume.summary):
            claimed_match = re.search(r"(\d+)\+?\s*years?", resume.summary)
            if claimed_match:
                claimed = int(claimed_match.group(1))
                if abs(claimed - stated_yoe) > 2:
                    score -= 10
                    issues.append(
                        f"Summary claims {claimed} years but experience totals ~{stated_yoe:.0f} years"
                    )
                    suggestions.append("Ensure your stated years of experience match your actual roles")

    # 5. No jarring transitions
    if len(experiences) >= 2:
        domains_per_role = []
        for exp in experiences:
            role_text = " ".join(exp.bullets).lower()
            detected = []
            for domain, kws in _DOMAIN_KEYWORDS.items():
                if any(kw in role_text for kw in kws):
                    detected.append(domain)
            domains_per_role.append(set(detected))

        # Check for domain consistency
        if len(domains_per_role) >= 2:
            all_domains = set()
            for d in domains_per_role:
                all_domains.update(d)
            if len(all_domains) <= 2:
                score += 5  # Focused career
            elif len(all_domains) >= 5:
                score -= 5
                issues.append("Career spans many different domains — story may seem unfocused")
                suggestions.append("In your summary, frame diverse experience as a strength with a connecting thread")

    score = _clamp(score)

    if not issues:
        explanation = "Resume tells a coherent career story with consistent progression."
    else:
        explanation = f"Narrative coherence scored {score:.0f}/100 based on structural analysis."

    return (round(score, 1), explanation, issues, suggestions)
