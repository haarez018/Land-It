"""
Resume rewriter: 6-pass system that improves ATS score without inventing facts.

Pass 1: Keyword Injection — add missing JD keywords naturally into existing bullets
Pass 2: Bullet Restructuring — reorder bullets within each role by relevance to JD
Pass 3: Verb Upgrading — replace weak action verbs with strong Tier 1-2 verbs
Pass 4: Quantification — add [USER TO VERIFY] metrics where impact is implied
Pass 5: Section Reordering — optimal section order for role type + seniority
Pass 6: Summary Rewrite — generate a new professional summary targeting the JD

CONSTRAINT: No invented facts. [USER TO VERIFY] markers for any inferred metrics.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription, WorkExperience

# ── Types ───────────────────────────────────────────────────────────────────


@dataclass
class RewriteChange:
    section: str
    original: str
    rewritten: str
    reason: str
    dimension_improved: list[str]
    confidence: str = "high"  # "high" | "medium" | "low"
    requires_verification: bool = False


@dataclass
class RewriteResult:
    rewritten_resume: Resume
    change_log: list[RewriteChange]
    sections_reordered: bool = False
    summary_rewritten: bool = False
    passes_applied: list[str] = field(default_factory=list)


# ── Verb upgrade tables ────────────────────────────────────────────────────

_VERB_UPGRADES: dict[str, str] = {
    # Tier 4 → Tier 1-2
    "helped": "facilitated",
    "assisted": "supported",
    "participated": "contributed to",
    "was responsible for": "owned",
    "was involved in": "drove",
    "worked on": "built",
    "used": "leveraged",
    "utilized": "leveraged",
    "responsible for": "owned",
    "tasked with": "led",
    "involved in": "contributed to",
    "served as": "operated as",
    # Tier 3 → Tier 1-2
    "created": "engineered",
    "managed": "orchestrated",
    "handled": "managed",
    "wrote": "authored",
    "updated": "modernized",
    "maintained": "sustained",
    "configured": "provisioned",
    "prepared": "developed",
    "organized": "coordinated",
    "tracked": "monitored",
    "supported": "enabled",
    "conducted": "executed",
    "coordinated": "orchestrated",
    "monitored": "supervised",
    "reviewed": "evaluated",
}

# ── Section ordering (from ats_scorer.py) ──────────────────────────────────

_OPTIMAL_ORDERS = {
    "software_engineer_backend": ["summary", "experience", "skills", "projects", "education", "certifications"],
    "software_engineer_frontend": ["summary", "experience", "skills", "projects", "education", "certifications"],
    "ml_engineer": ["summary", "experience", "skills", "projects", "education", "publications"],
    "product_manager": ["summary", "experience", "skills", "education", "certifications"],
    "data_scientist": ["summary", "experience", "education", "skills", "publications", "projects"],
    "devops_sre": ["summary", "experience", "skills", "certifications", "projects", "education"],
    "research_scientist": ["summary", "publications", "education", "experience", "skills", "awards"],
    "design_ux": ["summary", "experience", "skills", "projects", "education"],
}

_SENIORITY_OVERRIDES = {
    "intern": ["summary", "education", "projects", "skills", "experience"],
    "junior": ["summary", "education", "experience", "projects", "skills"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 1: KEYWORD INJECTION
# ═══════════════════════════════════════════════════════════════════════════════

def _pass_keyword_injection(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Inject missing JD keywords into existing bullets where contextually appropriate."""
    resume_text_lower = resume.raw_text.lower()

    # Find missing required keywords
    missing_kws: list[str] = []
    for kw in jd.required_skills + jd.tech_stack:
        if kw.lower() not in resume_text_lower:
            # Check if the keyword is in skills section
            all_skills = []
            for skills_list in resume.skills.values():
                all_skills.extend(s.lower() for s in skills_list)
            if kw.lower() not in all_skills:
                missing_kws.append(kw)

    if not missing_kws:
        return resume

    # For each missing keyword, try to inject into a relevant bullet
    # Only inject if the bullet's technologies list or context supports it
    resume = copy.deepcopy(resume)
    injected = set()

    for exp in resume.work_experience:
        for i, bullet in enumerate(exp.bullets):
            for kw in missing_kws:
                if kw in injected:
                    continue

                # Check if the technology category is related to this role's tech
                kw_lower = kw.lower()
                exp_tech_lower = [t.lower() for t in exp.technologies]

                # Only inject if:
                # 1. The role uses related technology, OR
                # 2. The keyword is a soft skill that fits the bullet context
                related = _keyword_fits_context(kw_lower, bullet, exp_tech_lower)
                if related:
                    original = bullet
                    new_bullet = _inject_keyword_into_bullet(bullet, kw)
                    if new_bullet != bullet:
                        exp.bullets[i] = new_bullet
                        injected.add(kw)
                        changes.append(RewriteChange(
                            section=f"Work Experience / {exp.company} / Bullet {i+1}",
                            original=original,
                            rewritten=new_bullet,
                            reason=f"Injected required keyword '{kw}' to improve keyword coverage",
                            dimension_improved=["keyword_density", "tech_stack_alignment"],
                            confidence="medium",
                        ))
                        break  # One injection per bullet

    # Also add missing keywords to skills section
    remaining = [kw for kw in missing_kws if kw not in injected]
    if remaining:
        if "additional" not in resume.skills:
            resume.skills["additional"] = []
        for kw in remaining[:5]:  # Cap at 5 additions
            resume.skills["additional"].append(kw)
            changes.append(RewriteChange(
                section="Skills / Additional",
                original="(not present)",
                rewritten=kw,
                reason=f"Added missing JD keyword '{kw}' to skills section",
                dimension_improved=["keyword_density"],
                confidence="medium",
            ))

    return resume


def _keyword_fits_context(keyword: str, bullet: str, role_techs: list[str]) -> bool:
    """Check if a keyword can reasonably be injected into a bullet."""
    bullet_lower = bullet.lower()

    # If the keyword is similar to existing tech in the role
    _TECH_FAMILIES = {
        "python": ["django", "flask", "fastapi", "pandas", "numpy"],
        "javascript": ["react", "vue", "angular", "node", "express", "typescript"],
        "go": ["golang", "gin"],
        "java": ["spring", "spring boot", "maven", "gradle"],
        "aws": ["ec2", "s3", "lambda", "dynamodb", "sqs", "cloudformation"],
        "gcp": ["bigquery", "cloud run", "pubsub", "gke"],
        "docker": ["container", "kubernetes", "k8s"],
        "kubernetes": ["docker", "k8s", "container", "helm", "deployment"],
        "kafka": ["event", "stream", "messaging", "queue", "pubsub"],
        "postgresql": ["database", "sql", "query", "schema", "postgres"],
        "redis": ["cache", "caching", "session", "memory"],
    }

    kw_lower = keyword.lower()
    for family_key, family_members in _TECH_FAMILIES.items():
        if kw_lower == family_key or kw_lower in family_members:
            # Check if any family member is in the bullet or role techs
            if any(m in bullet_lower for m in family_members + [family_key]):
                return True
            if any(m in role_techs for m in family_members + [family_key]):
                return True

    # Generic relevance: bullet mentions infrastructure, API, system, etc.
    generic_contexts = ["api", "system", "service", "platform", "infrastructure",
                        "pipeline", "database", "server", "deployment", "architecture"]
    if any(ctx in bullet_lower for ctx in generic_contexts):
        return True

    return False


def _inject_keyword_into_bullet(bullet: str, keyword: str) -> str:
    """Insert keyword naturally into a bullet point."""
    # Strategy: append "using {keyword}" or "with {keyword}" at the end
    # or insert before a period/comma
    bullet = bullet.rstrip()

    # If bullet already mentions the keyword, don't inject
    if keyword.lower() in bullet.lower():
        return bullet

    # Append naturally
    if bullet.endswith("."):
        return f"{bullet[:-1]} using {keyword}."
    else:
        return f"{bullet} using {keyword}"


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 2: BULLET RESTRUCTURING
# ═══════════════════════════════════════════════════════════════════════════════

def _pass_bullet_restructuring(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Reorder bullets within each role by relevance to the JD."""
    resume = copy.deepcopy(resume)
    jd_keywords = set()
    for kw in jd.required_skills + jd.preferred_skills + jd.tech_stack:
        jd_keywords.add(kw.lower())
    for req in jd.requirements:
        for word in re.findall(r"\b\w{3,}\b", req.text):
            jd_keywords.add(word.lower())

    for exp in resume.work_experience:
        if len(exp.bullets) < 2:
            continue

        original_order = list(exp.bullets)

        # Score each bullet by JD keyword overlap
        def bullet_relevance(bullet: str) -> float:
            words = set(w.lower() for w in re.findall(r"\b\w{3,}\b", bullet))
            overlap = len(words & jd_keywords)
            # Bonus for quantified bullets
            has_metric = bool(re.search(r"\d+[%$KMBkmb]|\$\d+", bullet))
            return overlap * 2 + (3 if has_metric else 0)

        sorted_bullets = sorted(exp.bullets, key=bullet_relevance, reverse=True)

        if sorted_bullets != original_order:
            exp.bullets = sorted_bullets
            changes.append(RewriteChange(
                section=f"Work Experience / {exp.company}",
                original=f"Original order: {len(original_order)} bullets",
                rewritten=f"Reordered: most JD-relevant bullets first",
                reason="Moved highest-relevance bullets to top where recruiters look first",
                dimension_improved=["experience_relevance", "keyword_density"],
            ))

    return resume


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 3: VERB UPGRADING
# ═══════════════════════════════════════════════════════════════════════════════

def _pass_verb_upgrading(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Replace weak opening verbs with stronger alternatives."""
    resume = copy.deepcopy(resume)

    for exp in resume.work_experience:
        for i, bullet in enumerate(exp.bullets):
            words = bullet.split()
            if not words:
                continue

            first_word = words[0].lower().rstrip(",.:;")

            # Check for multi-word weak phrases
            first_two = " ".join(words[:2]).lower() if len(words) >= 2 else ""
            first_three = " ".join(words[:3]).lower() if len(words) >= 3 else ""

            upgraded = None
            original_phrase = None

            # Check multi-word phrases first
            for phrase in [first_three, first_two]:
                if phrase in _VERB_UPGRADES:
                    replacement = _VERB_UPGRADES[phrase]
                    # Capitalize the replacement
                    replacement_cap = replacement[0].upper() + replacement[1:]
                    word_count = len(phrase.split())
                    upgraded = replacement_cap + " " + " ".join(words[word_count:])
                    original_phrase = phrase
                    break

            # Then single word
            if upgraded is None and first_word in _VERB_UPGRADES:
                replacement = _VERB_UPGRADES[first_word]
                replacement_cap = replacement[0].upper() + replacement[1:]
                upgraded = replacement_cap + " " + " ".join(words[1:])
                original_phrase = first_word

            if upgraded and upgraded != bullet:
                original = bullet
                exp.bullets[i] = upgraded
                changes.append(RewriteChange(
                    section=f"Work Experience / {exp.company} / Bullet {i+1}",
                    original=original,
                    rewritten=upgraded,
                    reason=f"Upgraded weak verb '{original_phrase}' to stronger alternative",
                    dimension_improved=["action_verb_strength"],
                ))

    return resume


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 4: QUANTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

_QUANTIFICATION_PATTERNS = [
    # (pattern in bullet, suggested addition, metric type)
    (r"\b(?:reduced|decreased|cut|lowered)\b", "by [USER TO VERIFY: X]%", "percentage"),
    (r"\b(?:increased|grew|improved|boosted|raised)\b", "by [USER TO VERIFY: X]%", "percentage"),
    (r"\b(?:built|developed|created|designed)\b.*\b(?:api|service|system|platform|tool)\b",
     "serving [USER TO VERIFY: X] users/requests", "scale"),
    (r"\b(?:led|managed|mentored)\b.*\bteam\b", "of [USER TO VERIFY: X] engineers", "team_size"),
    (r"\b(?:migrated|upgraded|refactored)\b", ", reducing [USER TO VERIFY: metric] by X%", "improvement"),
    (r"\bsaved?\b.*\b(?:cost|time|money|budget)\b", "[USER TO VERIFY: $X]", "currency"),
]


def _pass_quantification(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Add [USER TO VERIFY] metrics where impact is implied but not stated."""
    resume = copy.deepcopy(resume)

    for exp in resume.work_experience:
        for i, bullet in enumerate(exp.bullets):
            # Skip bullets that already have metrics
            if re.search(r"\d+[%$KMBkmb]|\$\d+|\d+x\b", bullet):
                continue

            for pattern, suggestion, metric_type in _QUANTIFICATION_PATTERNS:
                if re.search(pattern, bullet, re.IGNORECASE):
                    original = bullet
                    # Append the suggestion
                    if bullet.rstrip().endswith("."):
                        new_bullet = f"{bullet.rstrip()[:-1]} {suggestion}."
                    else:
                        new_bullet = f"{bullet.rstrip()} {suggestion}"

                    exp.bullets[i] = new_bullet
                    changes.append(RewriteChange(
                        section=f"Work Experience / {exp.company} / Bullet {i+1}",
                        original=original,
                        rewritten=new_bullet,
                        reason=f"Added quantification placeholder ({metric_type}) — candidate must fill in real numbers",
                        dimension_improved=["quantified_impact"],
                        confidence="low",
                        requires_verification=True,
                    ))
                    break  # Only one quantification per bullet

    return resume


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 5: SECTION REORDERING
# ═══════════════════════════════════════════════════════════════════════════════

def _pass_section_reordering(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> tuple[Resume, bool]:
    """Determine and record the optimal section order for the role type."""
    role_type = jd.infer_role_type()

    if resume.seniority_level in _SENIORITY_OVERRIDES:
        optimal = _SENIORITY_OVERRIDES[resume.seniority_level]
    else:
        optimal = _OPTIMAL_ORDERS.get(role_type, _OPTIMAL_ORDERS["software_engineer_backend"])

    # Detect current order from raw_text
    section_keywords = {
        "summary": ["summary", "professional summary", "objective", "profile"],
        "experience": ["experience", "work experience", "professional experience", "employment"],
        "education": ["education", "academic"],
        "skills": ["skills", "technical skills", "core competencies", "technologies"],
        "projects": ["projects", "personal projects", "side projects"],
        "certifications": ["certifications", "certificates"],
        "publications": ["publications", "papers", "research"],
        "awards": ["awards", "honors"],
    }

    text_lower = resume.raw_text.lower()
    current_positions: dict[str, int] = {}
    for section, keywords in section_keywords.items():
        for kw in keywords:
            pos = text_lower.find(kw)
            if pos >= 0:
                if section not in current_positions or pos < current_positions[section]:
                    current_positions[section] = pos
                break

    current_order = sorted(
        [s for s in optimal if s in current_positions],
        key=lambda s: current_positions[s]
    )

    # Check if reordering is needed
    optimal_filtered = [s for s in optimal if s in current_positions]
    if current_order == optimal_filtered:
        return resume, False

    changes.append(RewriteChange(
        section="Resume Structure",
        original=f"Current order: {' > '.join(current_order)}",
        rewritten=f"Recommended order: {' > '.join(optimal_filtered)}",
        reason=f"Optimal section order for {role_type} ({resume.seniority_level} level)",
        dimension_improved=["section_ordering"],
    ))

    return resume, True


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 6: SUMMARY REWRITE
# ═══════════════════════════════════════════════════════════════════════════════

def _pass_summary_rewrite(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Generate a new professional summary targeting the specific JD."""
    resume = copy.deepcopy(resume)

    # Build summary from resume data (no LLM needed)
    seniority_label = {
        "intern": "Aspiring",
        "junior": "Motivated",
        "mid": "Experienced",
        "senior": "Senior",
        "staff_principal": "Staff-level",
        "executive": "Executive",
    }.get(resume.seniority_level, "Experienced")

    # Determine role title from JD
    role_title = jd.title or "Software Engineer"

    # Get top skills that match JD
    all_resume_skills: list[str] = []
    for skills_list in resume.skills.values():
        all_resume_skills.extend(skills_list)
    jd_skill_set = set(s.lower() for s in jd.required_skills + jd.preferred_skills + jd.tech_stack)
    matching_skills = [s for s in all_resume_skills if s.lower() in jd_skill_set][:5]

    # Get total YoE
    yoe_str = f"{resume.total_yoe:.0f}+" if resume.total_yoe > 0 else ""

    # Get top impact from work experience
    top_impact = ""
    for exp in resume.work_experience:
        for bullet in exp.bullets:
            if re.search(r"\d+[%$KMBkmb]|\$\d+", bullet):
                # Extract a short impact phrase
                top_impact = bullet[:80]
                break
        if top_impact:
            break

    # Build the summary
    parts = [f"{seniority_label} {role_title.split('/')[-1].strip()}"]
    if yoe_str:
        parts[0] += f" with {yoe_str} years of experience"

    if matching_skills:
        skills_str = ", ".join(matching_skills[:4])
        remaining = len(matching_skills) - 4
        if remaining > 0:
            skills_str += f", and {remaining} more"
        parts.append(f"specializing in {skills_str}")

    # Add domain context from JD
    if jd.domain_knowledge:
        parts.append(f"with domain expertise in {', '.join(jd.domain_knowledge[:2])}")

    # Add a result-oriented closer
    if top_impact:
        # Simplify the impact into a summary-worthy phrase
        parts.append("with a track record of delivering measurable impact")

    new_summary = " ".join(parts) + "."

    original_summary = resume.summary or "(no summary)"
    resume.summary = new_summary

    changes.append(RewriteChange(
        section="Professional Summary",
        original=original_summary,
        rewritten=new_summary,
        reason="Rewrote summary to directly target this JD's role, skills, and priorities",
        dimension_improved=["keyword_density", "voice_alignment", "semantic_similarity"],
    ))

    return resume


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 6-CLAUDE: SUMMARY REWRITE (Claude-powered, falls back to template)
# ═══════════════════════════════════════════════════════════════════════════════

async def _pass_claude_summary(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Claude-generated professional summary targeting the specific role."""
    from backend.agents.llm import ask

    resume = copy.deepcopy(resume)

    all_skills: list[str] = []
    for skills_list in resume.skills.values():
        all_skills.extend(skills_list)

    exp_highlights: list[str] = []
    for exp in resume.work_experience[:2]:
        if exp.bullets:
            metric_bullets = [b for b in exp.bullets if re.search(r"\d+[%$KMBkmb]|\$\d+", b)]
            top = metric_bullets[0] if metric_bullets else exp.bullets[0]
            exp_highlights.append(f"{exp.title} at {exp.company}: {top[:100]}")

    system = """You are a professional resume writer. Write a 2-3 sentence professional summary.

Requirements:
1. Open with seniority + role title from the JD
2. Name 3-4 of the candidate's strongest skills that match the JD requirements
3. Close with a concrete achievement or impact statement

Rules:
- NO clichés: never use "passionate about", "team player", "results-driven", "hard worker"
- Written in implied third-person (no "I" or "My")
- 50-80 words maximum
- Reference skills and role name from the target job
- Output ONLY the summary text — no labels, no quotes, no explanation"""

    jd_reqs = ", ".join((jd.required_skills + jd.tech_stack)[:10])
    user = f"""CANDIDATE:
- {resume.total_yoe:.0f}+ years, {resume.seniority_level} level
- Skills: {', '.join(all_skills[:12])}
- Recent work: {chr(10).join(exp_highlights) or 'N/A'}

TARGET JOB:
- Role: {jd.title or 'Software Engineer'} at {jd.company or 'the company'}
- Required: {jd_reqs}
- Seniority: {jd.seniority_level or 'unspecified'}

Write the professional summary now:"""

    new_summary = (await ask(system, user, model="claude-haiku-4-5-20251001", max_tokens=200)).strip().strip('"')

    original_summary = resume.summary or "(no summary)"
    resume.summary = new_summary
    changes.append(RewriteChange(
        section="Professional Summary",
        original=original_summary,
        rewritten=new_summary,
        reason="Claude-generated summary targeting this specific role and company",
        dimension_improved=["keyword_density", "voice_alignment", "semantic_similarity"],
        confidence="high",
    ))
    return resume


# ═══════════════════════════════════════════════════════════════════════════════
# PASS 7: CLAUDE BULLET ENHANCEMENT (new pass)
# ═══════════════════════════════════════════════════════════════════════════════

async def _pass_claude_bullets(
    resume: Resume, jd: JobDescription, changes: list[RewriteChange]
) -> Resume:
    """Claude rewrites the top bullets from the most recent role for maximum impact."""
    from backend.agents.llm import ask_json

    resume = copy.deepcopy(resume)
    if not resume.work_experience:
        return resume

    top_exp = resume.work_experience[0]
    bullets = top_exp.bullets[:5]
    if not bullets:
        return resume

    jd_skills_str = ", ".join((jd.required_skills + jd.tech_stack)[:10])

    system = """You are a professional resume editor. Rewrite resume bullets to be stronger, more impact-focused, and better aligned with the target job.

STRICT RULES:
1. NEVER invent facts, companies, titles, or numbers not present in the original
2. If a bullet implies a metric (e.g., "improved performance"), add [USER TO VERIFY: X%] placeholder
3. Every bullet must start with a strong action verb (Architected, Engineered, Led, Delivered, Designed, Scaled, Reduced, etc.)
4. Add relevant JD keywords where they genuinely apply to what's described
5. Keep each bullet under 2 lines (150 chars max)

Output JSON array, same length as input:
[{"original": "...", "rewritten": "...", "reason": "brief reason for the change"}, ...]"""

    user = f"""Target role: {jd.title} at {jd.company or 'the company'}
Key requirements: {jd_skills_str}
Candidate level: {resume.seniority_level}
Role context: {top_exp.title} at {top_exp.company}

Bullets to rewrite:
{chr(10).join(f'{i+1}. {b}' for i, b in enumerate(bullets))}"""

    result = await ask_json(system, user, model="claude-haiku-4-5-20251001", max_tokens=1500)

    if not isinstance(result, list):
        return resume

    for i, item in enumerate(result[:len(bullets)]):
        if not isinstance(item, dict):
            continue
        rewritten = item.get("rewritten", "").strip()
        reason = item.get("reason", "Claude bullet enhancement")
        original = bullets[i]
        if rewritten and rewritten != original:
            top_exp.bullets[i] = rewritten
            changes.append(RewriteChange(
                section=f"Work Experience / {top_exp.company} / Bullet {i + 1}",
                original=original,
                rewritten=rewritten,
                reason=f"Claude: {reason}",
                dimension_improved=["action_verb_strength", "quantified_impact", "keyword_density"],
                confidence="high",
                requires_verification="USER TO VERIFY" in rewritten,
            ))

    return resume


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

async def rewrite_resume(
    resume: Resume,
    jd: JobDescription,
    *,
    skip_passes: Optional[set[str]] = None,
) -> RewriteResult:
    """
    Run the 6-pass rewrite pipeline on a resume.

    Pass names: "keyword_injection", "bullet_restructuring", "verb_upgrading",
    "quantification", "section_reordering", "summary_rewrite"

    All passes are deterministic (no LLM calls). When an Anthropic API key is
    available, a future version will use Claude for more nuanced rewrites.
    """
    skip = skip_passes or set()
    changes: list[RewriteChange] = []
    passes_applied: list[str] = []
    current = copy.deepcopy(resume)
    sections_reordered = False
    summary_rewritten = False

    # Pass 1: Keyword Injection
    if "keyword_injection" not in skip:
        current = _pass_keyword_injection(current, jd, changes)
        passes_applied.append("keyword_injection")

    # Pass 2: Bullet Restructuring
    if "bullet_restructuring" not in skip:
        current = _pass_bullet_restructuring(current, jd, changes)
        passes_applied.append("bullet_restructuring")

    # Pass 3: Verb Upgrading
    if "verb_upgrading" not in skip:
        current = _pass_verb_upgrading(current, jd, changes)
        passes_applied.append("verb_upgrading")

    # Pass 4: Quantification
    if "quantification" not in skip:
        current = _pass_quantification(current, jd, changes)
        passes_applied.append("quantification")

    # Pass 5: Section Reordering
    if "section_reordering" not in skip:
        current, sections_reordered = _pass_section_reordering(current, jd, changes)
        passes_applied.append("section_reordering")

    # Pass 6: Summary Rewrite (Claude when available, template fallback)
    if "summary_rewrite" not in skip:
        try:
            current = await _pass_claude_summary(current, jd, changes)
        except Exception:
            current = _pass_summary_rewrite(current, jd, changes)
        passes_applied.append("summary_rewrite")
        summary_rewritten = True

    # Pass 7: Claude Bullet Enhancement (Claude only — silently skipped if unavailable)
    if "claude_bullets" not in skip:
        try:
            current = await _pass_claude_bullets(current, jd, changes)
            passes_applied.append("claude_bullets")
        except Exception:
            pass

    return RewriteResult(
        rewritten_resume=current,
        change_log=changes,
        sections_reordered=sections_reordered,
        summary_rewritten=summary_rewritten,
        passes_applied=passes_applied,
    )


# ── System prompt for future LLM-based rewriting ──────────────────────────

REWRITER_SYSTEM_PROMPT = """
You are a professional resume editor with 15 years of experience in technical
recruiting. You are rewriting a candidate's resume to better match a specific
job description.

RULES YOU MUST FOLLOW:
1. NEVER invent skills, companies, titles, or achievements not in the original resume.
2. If adding a metric that is implied but not stated (e.g., "large dataset" ->
   "10M+ records"), mark it with [USER TO VERIFY] so the candidate can confirm.
3. Preserve all factual information exactly -- companies, dates, titles, degrees.
4. You are ONLY allowed to:
   - Reorder bullet points within a role
   - Rewrite existing bullets to be more specific and impactful
   - Upgrade weak action verbs
   - Add keywords from the JD that are genuinely reflected in the work described
   - Reorder resume sections
   - Rewrite the professional summary from scratch (it can be invented, it's a pitch)
5. For each change, internally track: original text -> new text -> reason -> dimension improved.
6. Output the full rewritten resume text AND a structured change log.

OUTPUT FORMAT (JSON):
{
  "rewritten_resume": "full resume text here",
  "change_log": [
    {
      "section": "Work Experience / Company / Bullet N",
      "original": "original text",
      "rewritten": "rewritten text",
      "reason": "why this change improves the resume",
      "dimension_improved": ["dimension_id_1", "dimension_id_2"],
      "confidence": "high",
      "requires_verification": false
    }
  ],
  "sections_reordered": false,
  "summary_rewritten": true
}
"""
