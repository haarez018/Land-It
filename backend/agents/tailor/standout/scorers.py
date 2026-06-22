"""
Standout Engine: 8 heuristic scorers that measure what impresses the HUMAN
reader after the ATS robot has already passed.

Each scorer returns: (raw_score: float 0-100, explanation, issues, suggestions)
Same contract as the ATS scorers.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription


# ── Helpers ──────────────────────────────────────────────────────────────────

_METRIC_RE = re.compile(
    r"""
    \$[\d,]+[KMBkmb]?           |   # $2.1M, $500K
    \d+[%]                      |   # 40%
    \d+[xX]\b                   |   # 3x, 10X
    \d+[KMBkmb]\+?\b            |   # 5M, 100K+
    \d{1,3}(?:,\d{3})+          |   # 1,000,000
    \d+\s*(?:users|customers|merchants|requests|events|transactions|engineers|teams?)
    """,
    re.VERBOSE | re.IGNORECASE,
)

_BIG_SCALE_RE = re.compile(
    r"""
    (?:\d+[MBmb]\+?\s*(?:users|customers|events|requests|transactions|revenue|ARR)) |
    (?:\$\d+[MBmb])                                                                  |
    (?:(?:million|billion|hundred\s+thousand)\s+(?:users|customers|events|dollars))   |
    (?:\d{7,})  # 7+ digit raw numbers
    """,
    re.VERBOSE | re.IGNORECASE,
)

_BUILDER_VERBS = {
    "architected", "built", "created", "designed", "developed", "engineered",
    "founded", "implemented", "invented", "launched", "pioneered", "shipped",
    "established", "introduced", "constructed", "authored", "crafted",
    "prototyped", "deployed", "initiated", "spearheaded", "conceived",
}

_MAINTAINER_VERBS = {
    "managed", "maintained", "supported", "assisted", "helped", "monitored",
    "oversaw", "administered", "coordinated", "facilitated", "participated",
    "contributed", "handled", "processed", "reviewed", "updated", "tracked",
}

_PRESTIGIOUS_COMPANIES = {
    "google", "meta", "facebook", "apple", "amazon", "microsoft", "netflix",
    "stripe", "airbnb", "uber", "lyft", "twitter", "x", "linkedin",
    "salesforce", "nvidia", "tesla", "openai", "anthropic", "deepmind",
    "coinbase", "databricks", "snowflake", "palantir", "datadog",
    "figma", "notion", "vercel", "supabase", "twilio", "square", "block",
    "bloomberg", "jpmorgan", "goldman sachs", "morgan stanley",
    "mckinsey", "bain", "bcg",
}

_PRESTIGIOUS_UNIVERSITIES = {
    "stanford", "mit", "harvard", "caltech", "cmu", "carnegie mellon",
    "berkeley", "princeton", "yale", "columbia", "cornell", "upenn",
    "university of pennsylvania", "oxford", "cambridge", "eth zurich",
    "georgia tech", "university of michigan", "university of washington",
    "university of illinois", "waterloo", "iit",
}

_CERTIFICATIONS = {
    "aws certified", "gcp certified", "azure certified", "cka", "ckad",
    "cissp", "ceh", "pmp", "scrum master", "tensorflow certified",
    "kubernetes", "databricks certified",
}


def _all_bullets(resume: Resume) -> list[str]:
    return [b for exp in resume.work_experience for b in exp.bullets]


def parse_scale_number(text: str) -> list[tuple[float, str]]:
    """Extract (number, unit) pairs from text. Handles 5M, 500K, 2.3B, comma notation, written-out."""
    results: list[tuple[float, str]] = []
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}

    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([KMBTkmbt])\+?\s*(?:(\w+))?", text):
        num = float(m.group(1))
        suffix = m.group(2).upper()
        unit = m.group(3) or ""
        actual = num * multipliers.get(suffix, 1)
        results.append((actual, unit.lower()))

    for m in re.finditer(r"(\d{1,3}(?:,\d{3})+)\+?\s*(\w+)?", text):
        num = float(m.group(1).replace(",", ""))
        unit = (m.group(2) or "").lower()
        if num >= 1000:
            results.append((num, unit))

    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(million|billion|trillion|thousand)", text, re.I):
        num = float(m.group(1))
        word = m.group(2).lower()
        word_mult = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
        results.append((num * word_mult[word], ""))

    return results


_RELATIVE_SPIKE_RE = [
    re.compile(r"grew\s+.*?from\s+(\d+)\s+to\s+(\d+)", re.I),
    re.compile(r"increased\s+.*?from\s+(\d+)\s+to\s+(\d+)", re.I),
]


def detect_relative_spikes(text: str) -> list[tuple[float, str]]:
    """Detect impressive RATIOS even when absolute numbers are small."""
    spikes: list[tuple[float, str]] = []
    for pattern in _RELATIVE_SPIKE_RE:
        for m in pattern.finditer(text):
            before = float(m.group(1))
            after = float(m.group(2))
            if before > 0:
                ratio = after / before
                if ratio >= 3.0:
                    spikes.append((ratio, f"{ratio:.0f}x growth"))
    return spikes


def _recent_bullets(resume: Resume, years: int = 3) -> list[str]:
    cutoff = date.today().year - years
    bullets = []
    for exp in resume.work_experience:
        start_year = exp.start_date.year if isinstance(exp.start_date, date) else 2020
        if start_year >= cutoff or exp.end_date is None:
            bullets.extend(exp.bullets)
    return bullets


# ── 1. Spike Factor ─────────────────────────────────────────────────────────

async def spike_factor_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Detects standout 'spikes' — achievements so impressive they alone
    justify an interview.
    """
    score = 0.0
    spikes: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    bullets = _all_bullets(resume)

    # Check for big-scale metrics
    for bullet in bullets:
        if _BIG_SCALE_RE.search(bullet):
            score += 20
            spikes.append(f"Scale spike: {bullet[:80]}...")
            if score >= 40:
                break

    # Check for prestigious company names
    companies = {exp.company.lower() for exp in resume.work_experience}
    prestige_matches = companies & _PRESTIGIOUS_COMPANIES
    if prestige_matches:
        score += min(len(prestige_matches) * 15, 30)
        spikes.append(f"Brand spike: {', '.join(prestige_matches)}")

    # Check for patents, publications, awards
    full_text = resume.raw_text.lower()
    if re.search(r"\bpatent\b", full_text):
        score += 10
        spikes.append("Patent holder")
    if re.search(r"\bpublish(?:ed|ing|cation)\b", full_text):
        score += 10
        spikes.append("Published work")
    if re.search(r"\baward|prize|winner|recognition\b", full_text):
        score += 10
        spikes.append("Awards/recognition")

    # Check for relative spikes (grew from X to Y)
    full_text = " ".join(bullets)
    rel_spikes = detect_relative_spikes(full_text)
    for ratio, desc in rel_spikes:
        score += min(ratio * 5, 20)
        spikes.append(f"Growth spike: {desc}")

    # Check for scale numbers via enhanced parser
    for bullet in bullets:
        for num, unit in parse_scale_number(bullet):
            if num >= 1_000_000:
                score += 15
                spikes.append(f"Million-scale metric: {num:,.0f} {unit}")
                break

    # Cap and generate feedback
    score = min(score, 100)

    if score < 30:
        issues.append("No standout spikes detected — resume blends into the pile")
        suggestions.append("Add at least one jaw-dropping metric (scale, revenue, or impact)")
        suggestions.append("Quantify your biggest achievement with exact numbers")
    elif score < 60:
        suggestions.append("Strengthen your top achievement with more specific scale metrics")

    explanation = (
        f"Found {len(spikes)} spike(s): {'; '.join(spikes[:3])}"
        if spikes else "No clear spikes detected"
    )

    return score, explanation, issues, suggestions


# ── 2. Trajectory Signal ────────────────────────────────────────────────────

async def trajectory_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Detects a visible career arc — is this person accelerating?
    """
    score = 50.0  # Baseline
    signals: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    experiences = resume.work_experience
    if len(experiences) < 2:
        return 40.0, "Not enough experience to show trajectory", \
            ["Only one role — trajectory is unclear"], \
            ["Add earlier roles or projects to show growth"]

    # Title progression check
    _SENIORITY_MAP = {
        "intern": 0, "junior": 1, "associate": 1,
        "software engineer": 2, "engineer": 2, "developer": 2,
        "senior": 3, "lead": 4, "staff": 5, "principal": 6,
        "director": 7, "vp": 8, "cto": 9, "ceo": 10,
    }

    title_levels: list[int] = []
    for exp in experiences:
        title = exp.title.lower()
        level = 2  # default mid
        for keyword, lvl in sorted(_SENIORITY_MAP.items(), key=lambda x: -x[1]):
            if keyword in title:
                level = lvl
                break
        title_levels.append(level)

    # Reverse so oldest first
    title_levels = list(reversed(title_levels))

    # Check if levels are non-decreasing
    upward_moves = sum(1 for i in range(1, len(title_levels)) if title_levels[i] > title_levels[i-1])
    lateral_moves = sum(1 for i in range(1, len(title_levels)) if title_levels[i] == title_levels[i-1])
    downward_moves = sum(1 for i in range(1, len(title_levels)) if title_levels[i] < title_levels[i-1])

    if upward_moves >= 2:
        score += 25
        signals.append(f"{upward_moves} clear promotions/level-ups")
    elif upward_moves == 1:
        score += 15
        signals.append("One level-up detected")

    if downward_moves > 0:
        score -= 15 * downward_moves
        issues.append(f"Apparent step-down in {downward_moves} transition(s)")

    # Scope growth: team sizes, revenue, system scale increasing
    scope_keywords = [
        (r"team\s+of\s+(\d+)", "team_size"),
        (r"(\d+)\s*(?:engineers|developers|reports)", "team_size"),
    ]
    team_sizes: list[int] = []
    for exp in experiences:
        for bullet in exp.bullets:
            for pattern, _ in scope_keywords:
                m = re.search(pattern, bullet)
                if m:
                    team_sizes.append(int(m.group(1)))

    if len(team_sizes) >= 2 and team_sizes[0] > team_sizes[-1]:
        score += 10
        signals.append("Growing scope (team size)")

    # YoE check — long tenure in same level is flat
    if resume.total_yoe > 8 and upward_moves == 0:
        score -= 10
        issues.append("8+ years with no visible progression")
        suggestions.append("Highlight promotions, expanded scope, or leadership growth")

    score = max(0, min(100, score))

    explanation = (
        f"Trajectory: {'; '.join(signals)}" if signals
        else "Career trajectory is flat or unclear"
    )

    if not suggestions and score < 70:
        suggestions.append("Make title progression more visible in your experience section")

    return score, explanation, issues, suggestions


# ── 3. Builder Ratio ────────────────────────────────────────────────────────

async def builder_ratio_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Measures BUILDING vs MAINTAINING verb ratio across resume bullets.
    """
    issues: list[str] = []
    suggestions: list[str] = []

    bullets = _all_bullets(resume)
    if not bullets:
        return 30.0, "No bullets to analyze", ["No experience bullets found"], \
            ["Add achievement bullets to your experience section"]

    builder_count = 0
    maintainer_count = 0
    other_count = 0

    for bullet in bullets:
        first_word = bullet.strip().split()[0].lower().rstrip("ed").rstrip("ing") if bullet.strip() else ""
        words = set(w.lower() for w in bullet.split()[:3])

        if words & _BUILDER_VERBS or any(v in bullet.lower()[:30] for v in _BUILDER_VERBS):
            builder_count += 1
        elif words & _MAINTAINER_VERBS or any(v in bullet.lower()[:30] for v in _MAINTAINER_VERBS):
            maintainer_count += 1
        else:
            other_count += 1

    total = builder_count + maintainer_count + other_count
    ratio = builder_count / total if total else 0

    # Score mapping
    if ratio >= 0.7:
        score = 90 + (ratio - 0.7) * 33
    elif ratio >= 0.5:
        score = 70 + (ratio - 0.5) * 100
    elif ratio >= 0.3:
        score = 40 + (ratio - 0.3) * 150
    else:
        score = ratio * 133

    score = min(100, max(0, score))

    if ratio < 0.3:
        issues.append(f"Builder ratio is only {ratio:.0%} — resume reads as maintenance-heavy")
        suggestions.append("Replace 'managed/maintained' verbs with 'built/designed/shipped'")
    elif ratio < 0.5:
        suggestions.append("Increase builder language — emphasize what you created, not what you maintained")

    explanation = (
        f"Builder ratio: {ratio:.0%} "
        f"({builder_count} build, {maintainer_count} maintain, {other_count} other)"
    )

    return score, explanation, issues, suggestions


# ── 4. Outcome Density ──────────────────────────────────────────────────────

async def outcome_density_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    What fraction of bullets contain a concrete outcome vs pure activity?
    """
    issues: list[str] = []
    suggestions: list[str] = []

    bullets = _all_bullets(resume)
    if not bullets:
        return 20.0, "No bullets to analyze", ["No experience bullets"], \
            ["Add bullet points with measurable outcomes"]

    outcome_count = 0
    activity_only: list[str] = []

    for bullet in bullets:
        has_metric = bool(_METRIC_RE.search(bullet))
        has_result_phrase = bool(re.search(
            r"(?:result(?:ing|ed)|led\s+to|achiev|improv|reduc|increas|sav|generat|deliver|ship)",
            bullet.lower()
        ))

        if has_metric or has_result_phrase:
            outcome_count += 1
        else:
            activity_only.append(bullet[:60])

    density = outcome_count / len(bullets)

    # Score based on seniority expectations
    seniority = resume.seniority_level
    if seniority in ("senior", "staff_principal", "executive"):
        target = 0.6
    elif seniority == "mid":
        target = 0.4
    else:
        target = 0.25

    if density >= target:
        score = 70 + min(30, (density - target) / (1 - target) * 30)
    else:
        score = max(10, density / target * 70)

    if density < target:
        issues.append(
            f"Outcome density {density:.0%} is below {target:.0%} target for {seniority} level"
        )
        suggestions.append(f"Add measurable results to {len(activity_only)} activity-only bullets")

    explanation = f"Outcome density: {density:.0%} ({outcome_count}/{len(bullets)} bullets have outcomes)"

    return min(100, score), explanation, issues, suggestions


# ── 5. Narrative Pull ────────────────────────────────────────────────────────

async def narrative_pull_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    Does this resume tell a coherent story that makes you want to keep reading?
    """
    score = 50.0
    signals: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    # 1. Summary quality (specific vs generic)
    if resume.summary:
        summary_lower = resume.summary.lower()
        generic_phrases = [
            "passionate", "team player", "hard worker", "results-driven",
            "self-motivated", "detail-oriented", "fast learner",
            "seeking a challenging position", "looking for opportunities",
        ]
        generic_count = sum(1 for p in generic_phrases if p in summary_lower)

        if generic_count == 0:
            score += 15
            signals.append("Summary is specific, not generic")
        elif generic_count >= 2:
            score -= 10
            issues.append(f"Summary has {generic_count} generic phrases")
            suggestions.append("Replace generic phrases with specific achievements or expertise areas")

        # Summary mentions a metric?
        if _METRIC_RE.search(resume.summary):
            score += 10
            signals.append("Summary contains a quantified claim")

        # Summary length check
        words = len(resume.summary.split())
        if 20 <= words <= 50:
            score += 5
        elif words > 80:
            issues.append("Summary is too long — should be 2-3 sentences")
    else:
        score -= 15
        issues.append("No summary section — missing the hook")
        suggestions.append("Add a 2-3 sentence summary with your biggest achievement and target role")

    # 2. Career theme coherence — do all roles relate?
    domains = set()
    for exp in resume.work_experience:
        for tech in exp.technologies:
            domains.add(tech.lower())

    if resume.primary_domain:
        score += 5
        signals.append(f"Clear domain focus: {resume.primary_domain}")

    # 3. Role-to-role progression logic
    if len(resume.work_experience) >= 2:
        titles = [exp.title for exp in resume.work_experience]
        # Check if titles share common theme words
        title_words = [set(t.lower().split()) for t in titles]
        common = title_words[0]
        for tw in title_words[1:]:
            common = common & tw
        # Remove noise words
        common -= {"at", "the", "and", "of", "in", "a", "an", "-", "–"}

        if common:
            score += 10
            signals.append(f"Consistent role theme: {', '.join(common)}")
        else:
            # Check for purposeful pivot
            if resume.total_yoe > 5:
                signals.append("Career pivot detected — may need explanation")

    score = max(0, min(100, score))

    explanation = (
        f"Narrative pull: {'; '.join(signals[:3])}" if signals
        else "Resume lacks a compelling narrative thread"
    )

    if not suggestions and score < 60:
        suggestions.append("Strengthen the connection between your roles — show a deliberate career arc")

    return score, explanation, issues, suggestions


# ── 6. Uniqueness Index ──────────────────────────────────────────────────────

async def uniqueness_index_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    How differentiated is this candidate from the typical applicant pool?
    """
    score = 40.0  # Baseline (average)
    signals: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    full_text = resume.raw_text.lower()

    # 1. Unusual skill combinations
    all_skills = set()
    for category, skills in resume.skills.items():
        for s in skills:
            all_skills.add(s.lower())

    cross_domain_pairs = [
        ({"python", "r", "tensorflow", "pytorch"}, {"biology", "bioinformatics", "genomics"}),
        ({"python", "go", "java"}, {"finance", "trading", "quantitative"}),
        ({"react", "typescript"}, {"machine learning", "data science"}),
        ({"design", "figma", "ux"}, {"python", "sql", "data"}),
    ]

    for tech_set, domain_set in cross_domain_pairs:
        if all_skills & tech_set and all_skills & domain_set:
            score += 15
            signals.append(f"Cross-domain: {', '.join(all_skills & tech_set)} + {', '.join(all_skills & domain_set)}")
            break

    # 2. Side projects / open source
    if re.search(r"\b(?:side\s+project|personal\s+project|open\s+source|github|contributed\s+to)\b", full_text):
        score += 10
        signals.append("Side projects or open source contributions")

    # 3. Publications / speaking
    if re.search(r"\b(?:published|paper|conference|spoke\s+at|presentation|talk\s+at|keynote)\b", full_text):
        score += 15
        signals.append("Publications or conference talks")

    # 4. Non-traditional education path
    edu_fields = {e.field.lower() for e in resume.education if e.field}
    non_cs_but_tech = edu_fields - {"computer science", "software engineering", "information technology"}
    if non_cs_but_tech and all_skills & {"python", "javascript", "go", "java", "react"}:
        score += 10
        signals.append(f"Non-traditional background: {', '.join(non_cs_but_tech)}")

    # 5. International / diverse experience
    locations = set()
    for exp in resume.work_experience:
        if exp.location:
            locations.add(exp.location.lower())
    if len(locations) >= 2:
        score += 5
        signals.append(f"Multi-location experience: {len(locations)} locations")

    # 6. Founding / entrepreneurial
    if re.search(r"\b(?:founder|co-?founder|startup|bootstrapped|YC|Y\s*Combinator)\b", full_text):
        score += 15
        signals.append("Entrepreneurial/founding experience")

    score = max(0, min(100, score))

    if score < 50:
        issues.append("Resume doesn't stand out from the typical applicant pool")
        suggestions.append("Highlight what makes you unique — unusual combinations, side projects, or domain expertise")

    explanation = (
        f"Uniqueness signals: {'; '.join(signals[:3])}" if signals
        else "No strong differentiation signals detected"
    )

    return score, explanation, issues, suggestions


# ── 7. Credibility Anchors ───────────────────────────────────────────────────

async def credibility_anchors_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    External proof points that independently verify quality.
    """
    score = 0.0
    anchors: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    full_text = resume.raw_text.lower()

    # 1. Prestigious companies
    companies = {exp.company.lower() for exp in resume.work_experience}
    prestige = companies & _PRESTIGIOUS_COMPANIES
    if prestige:
        score += min(len(prestige) * 15, 30)
        anchors.append(f"Companies: {', '.join(sorted(prestige))}")

    # 2. Prestigious universities
    for edu in resume.education:
        institution = edu.institution.lower()
        for uni in _PRESTIGIOUS_UNIVERSITIES:
            if uni in institution:
                score += 15
                anchors.append(f"University: {edu.institution}")
                break

    # 3. Certifications
    for cert in _CERTIFICATIONS:
        if cert in full_text:
            score += 8
            anchors.append(f"Certification: {cert}")
            if score >= 90:
                break

    # 4. Publications / patents
    if re.search(r"\bpatent\b", full_text):
        score += 12
        anchors.append("Patent holder")
    if re.search(r"\bpublish|journal|paper|arxiv|proceedings\b", full_text):
        score += 10
        anchors.append("Published research")

    # 5. Awards
    if re.search(r"\baward|winner|finalist|scholarship|fellow(?:ship)?\b", full_text):
        score += 8
        anchors.append("Awards/recognition")

    # 6. Open source with stars
    if re.search(r"\b(?:stars?|github|open.?source)\b.*\d+", full_text):
        score += 8
        anchors.append("Open source contributions")

    # 7. Honors
    for edu in resume.education:
        if edu.honors:
            score += 5
            anchors.append(f"Academic honors: {', '.join(edu.honors[:2])}")
            break

    score = max(0, min(100, score))

    if score < 30:
        issues.append("Few external credibility signals — reader has to take claims on faith")
        suggestions.append("Add certifications, link to published work, or highlight prestigious affiliations")

    explanation = (
        f"Credibility anchors: {'; '.join(anchors[:4])}" if anchors
        else "No strong external credibility signals"
    )

    return score, explanation, issues, suggestions


# ── 8. First Impression (6-Second Test) ──────────────────────────────────────

async def first_impression_scorer(
    resume: Resume, jd: JobDescription
) -> tuple[float, str, list[str], list[str]]:
    """
    What a recruiter gleans in the first 6 seconds of scanning.
    """
    score = 50.0  # Baseline
    signals: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    # 1. Name and contact clarity
    if resume.contact.name:
        score += 5
        signals.append("Name visible")
    else:
        score -= 10
        issues.append("Name not clearly parsed")

    if resume.contact.email:
        score += 3

    if resume.contact.linkedin:
        score += 3
        signals.append("LinkedIn linked")

    # 2. Summary exists and is punchy
    if resume.summary:
        words = resume.summary.split()
        if len(words) <= 40 and _METRIC_RE.search(resume.summary):
            score += 15
            signals.append("Summary is concise with a metric")
        elif len(words) <= 40:
            score += 8
            signals.append("Summary is concise")
        elif len(words) > 60:
            score -= 5
            issues.append("Summary too long for 6-second scan")
    else:
        score -= 10
        issues.append("No summary — nothing to hook the reader in 6 seconds")
        suggestions.append("Add a 1-2 sentence summary with your strongest credential")

    # 3. Most recent company/title strength
    if resume.work_experience:
        latest = resume.work_experience[0]
        if latest.company.lower() in _PRESTIGIOUS_COMPANIES:
            score += 10
            signals.append(f"Latest company: {latest.company}")

        # Title clarity
        title = latest.title.lower()
        if any(word in title for word in ("senior", "staff", "principal", "lead", "head", "director")):
            score += 8
            signals.append(f"Strong title: {latest.title}")

    # 4. Top 2 bullets strength
    top_bullets = _all_bullets(resume)[:2]
    strong_top = 0
    for bullet in top_bullets:
        if _METRIC_RE.search(bullet) and len(bullet.split()) >= 8:
            strong_top += 1

    if strong_top == 2:
        score += 12
        signals.append("Top 2 bullets both have metrics")
    elif strong_top == 1:
        score += 6
        signals.append("One strong opening bullet")
    else:
        issues.append("Top bullets lack quantified impact — weak first impression")
        suggestions.append("Make your first 2 bullets your strongest: include metrics and specific outcomes")

    # 5. YoE visibility
    if resume.total_yoe > 0:
        score += 3
        signals.append(f"{resume.total_yoe:.0f} YoE visible")

    score = max(0, min(100, score))

    explanation = (
        f"First impression: {'; '.join(signals[:3])}" if signals
        else "Weak first impression — nothing grabs attention in 6 seconds"
    )

    return score, explanation, issues, suggestions
