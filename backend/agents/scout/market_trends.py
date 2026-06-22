"""Job Market Trend Analyzer: curated skill demand data and market fit scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.parsers.schemas import Resume


@dataclass
class SkillTrend:
    skill: str
    demand_level: str
    yoy_change: float
    median_salary_premium: float
    top_companies_hiring: list[str]
    complementary_skills: list[str]


@dataclass
class MarketSnapshot:
    role_type: str
    hot_skills: list[SkillTrend]
    declining_skills: list[SkillTrend]
    avg_salary_trend: str
    remote_percentage: float
    top_hiring_companies: list[str]
    emerging_requirements: list[str]
    advice: str


@dataclass
class MarketFit:
    hot_skills_you_have: list[str]
    hot_skills_you_lack: list[str]
    declining_skills_you_have: list[str]
    market_fit_score: float
    advice: str


MARKET_DATA: dict[str, dict] = {
    "software_engineer_backend": {
        "hot": [
            SkillTrend("Rust", "hot", 0.35, 0.12, ["Cloudflare", "Discord", "Figma"], ["WebAssembly", "Systems"]),
            SkillTrend("Go", "hot", 0.25, 0.08, ["Google", "Uber", "Twitch"], ["Kubernetes", "gRPC"]),
            SkillTrend("Kubernetes", "growing", 0.20, 0.10, ["Platform teams"], ["Docker", "Terraform"]),
            SkillTrend("AI/ML Integration", "hot", 0.45, 0.15, ["OpenAI", "Anthropic"], ["Python", "LLMs"]),
            SkillTrend("Event-Driven", "growing", 0.18, 0.07, ["Stripe", "Uber"], ["Kafka", "CQRS"]),
        ],
        "declining": [
            SkillTrend("jQuery", "declining", -0.30, -0.05, [], []),
            SkillTrend("PHP (legacy)", "declining", -0.15, -0.03, [], []),
            SkillTrend("SOAP", "declining", -0.25, -0.04, [], []),
        ],
        "remote_pct": 0.45,
        "salary_trend": "Rising",
        "top_companies": ["Google", "Meta", "Stripe", "Anthropic", "OpenAI"],
        "emerging": ["LLM integration", "AI agent development", "Vector databases", "Prompt engineering"],
    },
    "software_engineer_frontend": {
        "hot": [
            SkillTrend("React", "stable", 0.05, 0.05, ["Meta", "Vercel"], ["Next.js", "TypeScript"]),
            SkillTrend("TypeScript", "hot", 0.30, 0.08, ["Everyone"], ["React", "Node.js"]),
            SkillTrend("Next.js", "hot", 0.40, 0.10, ["Vercel", "Startups"], ["React", "TypeScript"]),
        ],
        "declining": [
            SkillTrend("jQuery", "declining", -0.30, -0.05, [], []),
            SkillTrend("AngularJS (v1)", "declining", -0.40, -0.08, [], []),
        ],
        "remote_pct": 0.50,
        "salary_trend": "Stable",
        "top_companies": ["Vercel", "Shopify", "Figma"],
        "emerging": ["Server Components", "Edge computing", "AI-powered UI"],
    },
    "ml_engineer": {
        "hot": [
            SkillTrend("LLMs", "hot", 0.60, 0.20, ["OpenAI", "Anthropic", "Google"], ["Python", "Transformers"]),
            SkillTrend("RAG", "hot", 0.50, 0.15, ["Startups"], ["Vector DBs", "LangChain"]),
            SkillTrend("MLOps", "growing", 0.25, 0.10, ["ML teams"], ["Kubernetes", "MLflow"]),
        ],
        "declining": [
            SkillTrend("Classical ML only", "declining", -0.10, 0, [], []),
        ],
        "remote_pct": 0.40,
        "salary_trend": "Rising",
        "top_companies": ["OpenAI", "Anthropic", "DeepMind", "Google"],
        "emerging": ["AI agents", "Multimodal models", "Fine-tuning"],
    },
}


def get_market_snapshot(role_type: str) -> MarketSnapshot:
    data = MARKET_DATA.get(role_type, MARKET_DATA.get("software_engineer_backend"))
    if not data:
        data = list(MARKET_DATA.values())[0]
    return MarketSnapshot(
        role_type=role_type,
        hot_skills=data["hot"],
        declining_skills=data["declining"],
        avg_salary_trend=data["salary_trend"],
        remote_percentage=data["remote_pct"],
        top_hiring_companies=data["top_companies"],
        emerging_requirements=data["emerging"],
        advice=f"Focus on hot skills for {role_type} — highest salary premium and demand.",
    )


def get_user_market_fit(resume: Resume, role_type: str) -> MarketFit:
    snapshot = get_market_snapshot(role_type)
    resume_skills = set()
    for sl in resume.skills.values():
        resume_skills.update(s.lower() for s in sl)
    for exp in resume.work_experience:
        resume_skills.update(t.lower() for t in exp.technologies)
    resume_text = resume.raw_text.lower()

    hot_have: list[str] = []
    hot_lack: list[str] = []
    for trend in snapshot.hot_skills:
        if trend.skill.lower() in resume_skills or trend.skill.lower() in resume_text:
            hot_have.append(trend.skill)
        else:
            hot_lack.append(trend.skill)

    declining_have: list[str] = []
    for trend in snapshot.declining_skills:
        if trend.skill.lower() in resume_skills or trend.skill.lower() in resume_text:
            declining_have.append(trend.skill)

    total_hot = len(snapshot.hot_skills)
    fit = (len(hot_have) / total_hot * 100) if total_hot else 50
    penalty = len(declining_have) * 5
    score = max(0, min(100, fit - penalty))

    advice_parts: list[str] = []
    if hot_lack:
        advice_parts.append(f"Learn: {', '.join(hot_lack[:3])}")
    if declining_have:
        advice_parts.append(f"Deprioritize: {', '.join(declining_have)}")
    if hot_have:
        advice_parts.append(f"Leverage: {', '.join(hot_have[:3])}")

    return MarketFit(
        hot_skills_you_have=hot_have,
        hot_skills_you_lack=hot_lack,
        declining_skills_you_have=declining_have,
        market_fit_score=round(score, 1),
        advice=" | ".join(advice_parts) or "Your skills align well with the market.",
    )
