"""
Generate role-specific interview questions from a JD.

Uses heuristic-based generation (no LLM required).
Produces 10-12 questions across 5 categories:
  behavioral, technical, situational, system_design, culture_fit
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import JobDescription, Resume


@dataclass
class InterviewQuestion:
    """A single interview question with metadata."""
    id: str
    text: str
    category: str  # behavioral | technical | situational | system_design | culture_fit
    difficulty: str  # easy | medium | hard
    what_good_looks_like: str
    follow_ups: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    targeting: list[str] = field(default_factory=list)  # JD requirements this probes


# ── Question templates ─────────────────────────────────────────────────────

_BEHAVIORAL_TEMPLATES = [
    {
        "text": "Tell me about a time you had to make a technical decision with incomplete information. How did you approach it?",
        "good": "Uses STAR format, names a specific situation, explains the trade-off analysis, shows outcome with metrics.",
        "follow_ups": [
            "What would you do differently knowing what you know now?",
            "How did you get buy-in from stakeholders for your decision?",
        ],
        "red_flags": ["Vague answers with no specific example", "Blames others for the uncertainty"],
        "difficulty": "medium",
    },
    {
        "text": "Describe a project where you had to balance technical debt with feature delivery. What tradeoffs did you make?",
        "good": "Names a real project, explains the debt/feature tension, shows a principled decision with business reasoning.",
        "follow_ups": [
            "How did you communicate the tradeoff to non-technical stakeholders?",
            "Did you ever go back and pay down that debt? How?",
        ],
        "red_flags": ["Claims to never have technical debt", "No awareness of business constraints"],
        "difficulty": "hard",
    },
    {
        "text": "Tell me about a time you disagreed with a teammate or manager on a technical approach. How was it resolved?",
        "good": "Shows respect for the other perspective, explains own reasoning, describes collaborative resolution.",
        "follow_ups": [
            "What did you learn from their perspective?",
            "Would you handle it differently today?",
        ],
        "red_flags": ["Describes winning the argument rather than finding the best solution", "Passive-aggressive behavior"],
        "difficulty": "medium",
    },
    {
        "text": "Describe a time you had to learn a new technology or tool quickly to deliver a project. How did you approach it?",
        "good": "Shows structured learning approach, names specific resources, demonstrates applying new knowledge under pressure.",
        "follow_ups": [
            "What was the hardest part of ramping up?",
            "How do you decide when to go deep vs. learn just enough?",
        ],
        "red_flags": ["Claims to already know everything", "No structured learning approach"],
        "difficulty": "easy",
    },
    {
        "text": "Tell me about a time you identified a significant problem or opportunity that others hadn't noticed. What did you do about it?",
        "good": "Shows proactive thinking, explains discovery process, describes action taken and impact.",
        "follow_ups": [
            "How did you convince others this was worth addressing?",
            "What metrics did you use to validate the impact?",
        ],
        "red_flags": ["Takes credit for obvious observations", "Didn't actually take action on the insight"],
        "difficulty": "hard",
    },
    {
        "text": "Describe a situation where you had to mentor or help a junior engineer grow. What was your approach?",
        "good": "Shows empathy, describes specific teaching methods, mentions the junior's growth outcome.",
        "follow_ups": [
            "How did you adjust your style for different learning needs?",
            "What did you learn from the experience?",
        ],
        "red_flags": ["Describes doing the work for them", "No awareness of different learning styles"],
        "difficulty": "medium",
    },
]

_TECHNICAL_TEMPLATES = [
    {
        "text": "Walk me through how you would design a {system_type} that handles {scale_descriptor}.",
        "good": "Starts with requirements clarification, draws out components, discusses tradeoffs, addresses scaling.",
        "follow_ups": [
            "What happens when this system needs to scale 10x?",
            "How would you handle a failure in {component}?",
        ],
        "red_flags": ["Jumps to implementation without understanding requirements", "No discussion of tradeoffs"],
        "difficulty": "hard",
        "systems": [
            ("notification system", "millions of events per day"),
            ("rate limiter", "100k requests per second"),
            ("real-time feed", "millions of concurrent users"),
            ("job queue", "variable-priority tasks with retries"),
            ("caching layer", "high read throughput with cache invalidation"),
        ],
    },
    {
        "text": "Explain how {concept} works under the hood and when you would or wouldn't use it.",
        "good": "Clear explanation of internals, practical use cases, honest about limitations.",
        "follow_ups": [
            "When has this approach bitten you in production?",
            "What alternatives did you consider?",
        ],
        "red_flags": ["Textbook answer with no practical experience", "Overconfident without acknowledging limitations"],
        "difficulty": "medium",
        "concepts": [
            "database indexing and query optimization",
            "container orchestration with Kubernetes",
            "event-driven architecture with message queues",
            "CI/CD pipelines and deployment strategies",
            "microservices vs. monolith tradeoffs",
            "OAuth 2.0 and token-based authentication",
        ],
    },
    {
        "text": "You discover a critical production bug on a Friday at 5pm that affects {impact}. Walk me through your incident response.",
        "good": "Prioritizes user impact, communicates to stakeholders, systematic debugging, post-mortem planning.",
        "follow_ups": [
            "How do you decide between a quick fix and a proper fix?",
            "How do you prevent similar incidents?",
        ],
        "red_flags": ["No mention of communication", "Cowboy debugging without a plan"],
        "difficulty": "medium",
        "impacts": [
            "10% of users seeing errors",
            "data inconsistency in billing",
            "authentication failures for enterprise customers",
        ],
    },
]

_SITUATIONAL_TEMPLATES = [
    {
        "text": "Your team is behind on a deadline and the PM asks to cut scope. Which features would you cut and why?",
        "good": "Shows framework for prioritization, considers user impact, involves stakeholders.",
        "follow_ups": [
            "How would you communicate this to the team?",
            "What if the PM disagrees with your assessment?",
        ],
        "red_flags": ["Says they'd just work overtime", "No prioritization framework"],
        "difficulty": "medium",
    },
    {
        "text": "You're onboarding and the codebase has no documentation. How do you ramp up effectively?",
        "good": "Shows systematic exploration, asks the right people, contributes docs as they learn.",
        "follow_ups": [
            "How would you improve the onboarding for the next person?",
            "How do you decide what's worth documenting?",
        ],
        "red_flags": ["Waits to be told everything", "Doesn't contribute back"],
        "difficulty": "easy",
    },
    {
        "text": "A stakeholder requests a feature that you believe will create significant technical debt. How do you handle it?",
        "good": "Listens to the business need, quantifies the technical cost, proposes alternatives.",
        "follow_ups": [
            "What if they insist despite your concerns?",
            "How do you document the decision?",
        ],
        "red_flags": ["Simply refuses", "Builds it without raising concerns"],
        "difficulty": "hard",
    },
]

_CULTURE_TEMPLATES = [
    {
        "text": "What's a technology or tool you recently learned? How did you go about learning it?",
        "good": "Shows genuine curiosity, structured learning approach, applied it to something real.",
        "follow_ups": [
            "How do you stay current with the rapidly changing tech landscape?",
            "What's on your learning roadmap for the next 6 months?",
        ],
        "red_flags": ["Hasn't learned anything new recently", "Only learns when forced to"],
        "difficulty": "easy",
    },
    {
        "text": "What kind of engineering culture do you thrive in? Give me a specific example.",
        "good": "Self-awareness about work style, names specific cultural attributes, gives a real example.",
        "follow_ups": [
            "What's a culture you struggled in and why?",
            "How do you contribute to building that culture?",
        ],
        "red_flags": ["Generic answers like 'collaborative'", "No self-awareness"],
        "difficulty": "easy",
    },
]


# ── JD-specific question generators ──────────────────────────────────────


def _generate_tech_stack_questions(jd: JobDescription) -> list[dict]:
    """Generate questions targeting the specific tech stack."""
    questions: list[dict] = []
    for tech in jd.tech_stack[:3]:
        questions.append({
            "text": f"Tell me about a project where you used {tech} in production. What challenges did you face?",
            "good": f"Names a real project with {tech}, describes specific challenges and solutions, shows depth.",
            "follow_ups": [
                f"What are the biggest pitfalls of {tech} at scale?",
                f"If you were starting fresh, would you still choose {tech}? Why or why not?",
            ],
            "red_flags": [f"Only tutorial-level {tech} experience", "Can't discuss tradeoffs"],
            "difficulty": "medium",
            "category": "technical",
            "targeting": [tech],
        })
    return questions


def _generate_requirement_questions(jd: JobDescription) -> list[dict]:
    """Generate questions targeting specific JD requirements."""
    questions: list[dict] = []
    for req in jd.requirements[:2]:
        if req.skill_type == "technical":
            questions.append({
                "text": f"The role requires {req.text.lower().rstrip('.')}. Describe your experience in this area with a specific example.",
                "good": f"Concrete example demonstrating {req.extracted_keyword} expertise with measurable outcomes.",
                "follow_ups": [
                    "What was the most complex aspect of that work?",
                    "How would you approach this differently in our context?",
                ],
                "red_flags": ["No specific example", "Experience doesn't match the requirement depth"],
                "difficulty": "medium",
                "category": "technical",
                "targeting": [req.extracted_keyword],
            })
        elif req.skill_type == "soft":
            questions.append({
                "text": f"This role emphasizes {req.text.lower().rstrip('.')}. Tell me about a time you demonstrated this.",
                "good": f"STAR format example showing {req.extracted_keyword} in action.",
                "follow_ups": [
                    "How did others respond to your approach?",
                    "What did you learn from that experience?",
                ],
                "red_flags": ["Generic claims without examples", "Example doesn't match the skill"],
                "difficulty": "easy",
                "category": "behavioral",
                "targeting": [req.extracted_keyword],
            })
    return questions


def _generate_seniority_questions(jd: JobDescription) -> list[dict]:
    """Generate questions calibrated to seniority level."""
    level = jd.seniority_level.lower()
    questions: list[dict] = []

    if level in ("senior", "staff", "principal", "lead"):
        questions.append({
            "text": "Describe a technical strategy or architectural direction you set for your team. How did you get alignment?",
            "good": "Shows strategic thinking, stakeholder management, and long-term technical vision.",
            "follow_ups": [
                "How did you measure whether the strategy was working?",
                "What pushback did you get and how did you handle it?",
            ],
            "red_flags": ["Only talks about implementation, not strategy", "Didn't involve the team"],
            "difficulty": "hard",
            "category": "behavioral",
            "targeting": ["leadership", "strategy"],
        })
        questions.append({
            "text": "How do you approach code reviews? What do you look for beyond correctness?",
            "good": "Discusses readability, maintainability, testing, knowledge sharing, and mentorship aspects.",
            "follow_ups": [
                "How do you handle a review where you disagree with the approach?",
                "How do you balance thoroughness with velocity?",
            ],
            "red_flags": ["Only checks for bugs", "Adversarial review style"],
            "difficulty": "medium",
            "category": "technical",
            "targeting": ["code review", "mentorship"],
        })
    else:
        questions.append({
            "text": "Walk me through your development workflow from picking up a ticket to deploying the feature.",
            "good": "Shows understanding of the full development lifecycle, testing, and deployment practices.",
            "follow_ups": [
                "How do you decide when something is ready to merge?",
                "What do you do when you're stuck on a problem?",
            ],
            "red_flags": ["No testing mentioned", "No collaboration in workflow"],
            "difficulty": "easy",
            "category": "technical",
            "targeting": ["development workflow"],
        })

    return questions


def _generate_company_culture_questions(jd: JobDescription) -> list[dict]:
    """Generate questions about company values alignment."""
    questions: list[dict] = []
    company = jd.company or "the company"

    if jd.company_values:
        value = jd.company_values[0]
        questions.append({
            "text": f"{company} values \"{value}\". Tell me about a time you demonstrated this value in your work.",
            "good": f"Authentic example connected to \"{value}\", shows genuine alignment.",
            "follow_ups": [
                "How does this value influence your day-to-day decisions?",
                "When has living this value been difficult?",
            ],
            "red_flags": ["Clearly rehearsed without genuine connection", "Misunderstands the value"],
            "difficulty": "easy",
            "category": "culture_fit",
            "targeting": [value],
        })

    return questions


# ── Main generator ────────────────────────────────────────────────────────


async def generate_questions(
    jd: JobDescription,
    resume: Optional[Resume] = None,
    *,
    count: int = 10,
    seed: Optional[int] = None,
) -> list[InterviewQuestion]:
    """
    Generate interview questions tailored to a JD.
    Uses Claude when available; falls back to template-based generation.
    """
    try:
        return await _generate_with_claude(jd, count=count)
    except Exception:
        return _generate_heuristic(jd, resume=resume, count=count, seed=seed)


async def _generate_with_claude(
    jd: JobDescription,
    *,
    count: int = 10,
) -> list[InterviewQuestion]:
    """Generate JD-specific interview questions using Claude."""
    from backend.agents.llm import ask_json

    tech_stack = ", ".join(jd.tech_stack[:8]) if jd.tech_stack else "Not specified"
    reqs_text = "\n".join(f"- {r.text}" for r in jd.requirements[:6]) or "Not specified"
    values_text = (
        ", ".join(jd.company_values[:3])
        if hasattr(jd, "company_values") and jd.company_values
        else "Not specified"
    )

    system = """You are a senior engineering interviewer at a top-tier tech company.
Your questions are probing, specific to the role, and reveal genuine depth.
You avoid generic questions. Every question connects to real requirements."""

    user = f"""Generate exactly {count} interview questions for this role.

ROLE: {jd.title or 'Software Engineer'} at {jd.company or 'the company'}
SENIORITY: {jd.seniority_level or 'mid-level'}
TECH STACK: {tech_stack}
KEY REQUIREMENTS:
{reqs_text}
COMPANY VALUES: {values_text}

Target this mix: behavioral (3), technical (3), situational (2), system_design (1), culture_fit (1).
Calibrate difficulty to seniority. Be specific — no generic "tell me about a time" without connecting to the actual role.

Return a JSON array with exactly {count} objects:
[
  {{
    "text": "The exact question text",
    "category": "behavioral|technical|situational|system_design|culture_fit",
    "difficulty": "easy|medium|hard",
    "what_good_looks_like": "What an excellent answer includes — specific to this role",
    "follow_ups": ["Follow-up question 1", "Follow-up question 2"],
    "red_flags": ["Red flag to watch for in the answer"],
    "targeting": ["skill or requirement this question probes"]
  }}
]"""

    data = await ask_json(system, user, model="claude-haiku-4-5-20251001", max_tokens=3500)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Claude returned unexpected format")

    questions: list[InterviewQuestion] = []
    for i, q in enumerate(data[:count]):
        if not q.get("text"):
            continue
        questions.append(InterviewQuestion(
            id=f"q_{i + 1:02d}",
            text=q["text"],
            category=q.get("category", "behavioral"),
            difficulty=q.get("difficulty", "medium"),
            what_good_looks_like=q.get("what_good_looks_like", ""),
            follow_ups=q.get("follow_ups", []),
            red_flags=q.get("red_flags", []),
            targeting=q.get("targeting", []),
        ))

    if not questions:
        raise ValueError("No valid questions parsed from Claude response")

    return questions


def _generate_heuristic(
    jd: JobDescription,
    resume: Optional[Resume] = None,
    *,
    count: int = 10,
    seed: Optional[int] = None,
) -> list[InterviewQuestion]:
    """Template-based fallback question generation (no LLM required)."""
    rng = random.Random(seed)
    pool: list[dict] = []

    # 1. JD-specific questions
    pool.extend(_generate_tech_stack_questions(jd))
    pool.extend(_generate_requirement_questions(jd))
    pool.extend(_generate_seniority_questions(jd))
    pool.extend(_generate_company_culture_questions(jd))

    # 2. Fill remaining slots from generic templates
    categories_needed = {
        "behavioral": 3,
        "technical": 3,
        "situational": 2,
        "culture_fit": 1,
    }

    # Count what we already have
    for q in pool:
        cat = q.get("category", "behavioral")
        if cat in categories_needed:
            categories_needed[cat] = max(0, categories_needed[cat] - 1)

    # Add behavioral
    behavioral_pool = list(_BEHAVIORAL_TEMPLATES)
    rng.shuffle(behavioral_pool)
    for tmpl in behavioral_pool[: categories_needed.get("behavioral", 0)]:
        pool.append({**tmpl, "category": "behavioral", "targeting": []})

    # Add technical (with substitution)
    tech_pool = list(_TECHNICAL_TEMPLATES)
    rng.shuffle(tech_pool)
    for tmpl in tech_pool[: categories_needed.get("technical", 0)]:
        text = tmpl["text"]
        good = tmpl["good"]
        follow_ups = list(tmpl["follow_ups"])

        if "systems" in tmpl:
            system, scale = rng.choice(tmpl["systems"])
            text = text.format(system_type=system, scale_descriptor=scale)
            follow_ups = [f.format(component="the database") for f in follow_ups]
        elif "concepts" in tmpl:
            concept = rng.choice(tmpl["concepts"])
            text = text.format(concept=concept)
        elif "impacts" in tmpl:
            impact = rng.choice(tmpl["impacts"])
            text = text.format(impact=impact)

        pool.append({
            **tmpl,
            "text": text,
            "good": good,
            "follow_ups": follow_ups,
            "category": "technical",
            "targeting": [],
        })

    # Add situational
    sit_pool = list(_SITUATIONAL_TEMPLATES)
    rng.shuffle(sit_pool)
    for tmpl in sit_pool[: categories_needed.get("situational", 0)]:
        pool.append({**tmpl, "category": "situational", "targeting": []})

    # Add culture
    culture_pool = list(_CULTURE_TEMPLATES)
    rng.shuffle(culture_pool)
    for tmpl in culture_pool[: categories_needed.get("culture_fit", 0)]:
        pool.append({**tmpl, "category": "culture_fit", "targeting": []})

    # 3. Deduplicate and trim to count
    seen_texts: set[str] = set()
    unique_pool: list[dict] = []
    for q in pool:
        key = q["text"][:80]
        if key not in seen_texts:
            seen_texts.add(key)
            unique_pool.append(q)

    # 4. Sort: behavioral first, then technical, situational, system_design, culture_fit
    # Within category, sort by difficulty: easy < medium < hard
    cat_order = {"behavioral": 0, "technical": 1, "situational": 2, "system_design": 3, "culture_fit": 4}
    diff_order = {"easy": 0, "medium": 1, "hard": 2}
    unique_pool.sort(key=lambda q: (
        cat_order.get(q.get("category", "behavioral"), 9),
        diff_order.get(q.get("difficulty", "medium"), 1),
    ))

    # Trim to count
    selected = unique_pool[:count]

    # 5. Convert to InterviewQuestion dataclass
    questions: list[InterviewQuestion] = []
    for i, q in enumerate(selected):
        questions.append(InterviewQuestion(
            id=f"q_{i + 1:02d}",
            text=q["text"],
            category=q.get("category", "behavioral"),
            difficulty=q.get("difficulty", "medium"),
            what_good_looks_like=q.get("good", ""),
            follow_ups=q.get("follow_ups", []),
            red_flags=q.get("red_flags", []),
            targeting=q.get("targeting", []),
        ))

    return questions
