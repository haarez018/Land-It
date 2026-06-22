"""
Fetch company context (mission, news, values) for cover letter personalization.

Uses heuristic extraction from the JD text when no external APIs are available.
Future version will use web search + Claude for richer context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import JobDescription


@dataclass
class CompanyContext:
    """Researched context about a company for cover letter personalization."""
    company_name: str
    mission: str = ""
    values: list[str] = field(default_factory=list)
    recent_news: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    culture_signals: list[str] = field(default_factory=list)
    industry: str = ""
    company_size: str = ""  # startup | midsize | large | enterprise
    tone: str = ""  # formal | casual | technical | mission_driven
    funding_stage: str = ""
    key_talking_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "mission": self.mission,
            "values": self.values,
            "recent_news": self.recent_news,
            "products": self.products,
            "culture_signals": self.culture_signals,
            "industry": self.industry,
            "company_size": self.company_size,
            "tone": self.tone,
            "funding_stage": self.funding_stage,
            "key_talking_points": self.key_talking_points,
        }


# ── Known company profiles ─────────────────────────────────────────────────

_KNOWN_COMPANIES: dict[str, dict] = {
    "stripe": {
        "mission": "Increase the GDP of the internet",
        "values": ["Move with urgency", "Be meticulous", "Think rigorously"],
        "products": ["Stripe Payments", "Stripe Connect", "Stripe Atlas", "Stripe Billing"],
        "industry": "fintech",
        "company_size": "large",
        "tone": "technical",
        "culture_signals": ["Engineering-first culture", "Long-term thinking", "Global ambition"],
    },
    "google": {
        "mission": "Organize the world's information and make it universally accessible",
        "values": ["Focus on the user", "It's best to do one thing really well", "Fast is better than slow"],
        "products": ["Search", "Cloud", "Android", "YouTube", "Workspace"],
        "industry": "technology",
        "company_size": "enterprise",
        "tone": "technical",
        "culture_signals": ["Innovation-driven", "Data-informed decisions", "20% time"],
    },
    "notion": {
        "mission": "Make toolmaking ubiquitous",
        "values": ["Craft", "Ambition", "Kindness"],
        "products": ["Notion Workspace", "Notion AI", "Notion Calendar"],
        "industry": "saas",
        "company_size": "midsize",
        "tone": "casual",
        "culture_signals": ["Design-obsessed", "Small team, big impact", "Remote-first"],
    },
    "airbnb": {
        "mission": "Create a world where anyone can belong anywhere",
        "values": ["Be a host", "Champion the mission", "Embrace the adventure"],
        "products": ["Airbnb Stays", "Airbnb Experiences", "AirCover"],
        "industry": "travel",
        "company_size": "large",
        "tone": "mission_driven",
        "culture_signals": ["Design-led", "Community-focused", "Storytelling culture"],
    },
    "meta": {
        "mission": "Give people the power to build community and bring the world closer together",
        "values": ["Move fast", "Be bold", "Focus on long-term impact", "Build awesome things"],
        "products": ["Facebook", "Instagram", "WhatsApp", "Meta Quest", "Threads"],
        "industry": "technology",
        "company_size": "enterprise",
        "tone": "casual",
        "culture_signals": ["Move fast and break things", "Hacker culture", "Impact at scale"],
    },
    "amazon": {
        "mission": "Be Earth's most customer-centric company",
        "values": ["Customer obsession", "Ownership", "Invent and simplify", "Bias for action"],
        "products": ["AWS", "Amazon.com", "Prime", "Alexa", "Kindle"],
        "industry": "technology",
        "company_size": "enterprise",
        "tone": "formal",
        "culture_signals": ["Leadership Principles", "Day 1 mentality", "Working backwards"],
    },
}


# ── JD-based extraction ────────────────────────────────────────────────────

_INDUSTRY_KEYWORDS = {
    "fintech": ["payment", "financial", "banking", "transactions", "compliance"],
    "healthtech": ["health", "clinical", "patient", "medical", "hipaa"],
    "edtech": ["education", "learning", "student", "curriculum"],
    "saas": ["saas", "subscription", "b2b", "enterprise", "platform"],
    "e-commerce": ["e-commerce", "retail", "marketplace", "shopping"],
    "ai_ml": ["machine learning", "ai", "deep learning", "nlp", "model"],
    "gaming": ["game", "gaming", "unity", "multiplayer"],
    "travel": ["travel", "booking", "hospitality"],
    "cybersecurity": ["security", "threat", "vulnerability", "encryption"],
}

_SIZE_SIGNALS = {
    "startup": ["startup", "series a", "series b", "seed", "early-stage", "small team"],
    "midsize": ["growing team", "scaling", "series c", "series d"],
    "large": ["established", "global", "thousands of employees"],
    "enterprise": ["fortune 500", "10,000+", "multinational"],
}

_TONE_SIGNALS = {
    "casual": ["fun", "cool", "awesome", "we're", "you'll", "vibe", "stoked"],
    "formal": ["we seek", "the ideal candidate", "qualifications", "competencies"],
    "mission_driven": ["mission", "impact", "change the world", "make a difference"],
    "technical": ["architecture", "distributed systems", "scalable", "infrastructure"],
}


def _infer_industry(text: str) -> str:
    text_lower = text.lower()
    best_industry = ""
    best_count = 0
    for industry, keywords in _INDUSTRY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_industry = industry
    return best_industry


def _infer_company_size(text: str) -> str:
    text_lower = text.lower()
    for size, signals in _SIZE_SIGNALS.items():
        if any(s in text_lower for s in signals):
            return size
    return "midsize"  # Default


def _infer_tone(text: str) -> str:
    text_lower = text.lower()
    best_tone = "technical"
    best_count = 0
    for tone, signals in _TONE_SIGNALS.items():
        count = sum(1 for s in signals if s in text_lower)
        if count > best_count:
            best_count = count
            best_tone = tone
    return best_tone


def _generate_talking_points(jd: JobDescription, context: CompanyContext) -> list[str]:
    """Generate key talking points for the cover letter."""
    points: list[str] = []

    if context.mission:
        points.append(f"Reference {context.company_name}'s mission: '{context.mission}'")

    if jd.role_priorities:
        points.append(f"Address top priority: {jd.role_priorities[0]}")

    if context.values:
        points.append(f"Align with company values: {', '.join(context.values[:2])}")

    if context.products:
        points.append(f"Mention relevant product: {context.products[0]}")

    if jd.tech_stack:
        points.append(f"Highlight tech stack experience: {', '.join(jd.tech_stack[:3])}")

    return points[:5]


# ── Main research function ──────────────────────────────────────────────────

def research_company(jd: JobDescription) -> CompanyContext:
    """
    Research a company for cover letter personalization.

    Uses known company profiles when available, otherwise extracts
    context from the JD text itself.

    Args:
        jd: Parsed job description

    Returns:
        CompanyContext with relevant company information
    """
    company_lower = jd.company.lower().strip()

    # Check known companies
    known = _KNOWN_COMPANIES.get(company_lower)
    if known:
        context = CompanyContext(
            company_name=jd.company,
            mission=known.get("mission", ""),
            values=known.get("values", []),
            products=known.get("products", []),
            industry=known.get("industry", ""),
            company_size=known.get("company_size", ""),
            tone=known.get("tone", ""),
            culture_signals=known.get("culture_signals", []),
        )
    else:
        # Extract from JD text
        context = CompanyContext(
            company_name=jd.company,
            values=jd.company_values[:5] if jd.company_values else [],
            industry=_infer_industry(jd.raw_text),
            company_size=_infer_company_size(jd.raw_text),
            tone=_infer_tone(jd.raw_text),
            culture_signals=[],
        )

        # Try to extract mission from JD
        mission_patterns = [
            r"(?:our mission|we're on a mission|mission:?)\s*(?:is\s+)?(?:to\s+)?(.{20,100}?)[.\n]",
            r"(?:we believe|our goal|we aim)\s+(.{20,100}?)[.\n]",
        ]
        for pattern in mission_patterns:
            match = re.search(pattern, jd.raw_text, re.IGNORECASE)
            if match:
                context.mission = match.group(1).strip()
                break

    # Generate talking points from JD + context
    context.key_talking_points = _generate_talking_points(jd, context)

    return context
