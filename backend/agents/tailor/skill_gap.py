"""Skill Gap Analyzer: identifies missing skills, estimates score impact, generates learning paths."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.parsers.schemas import Resume, JobDescription


@dataclass
class SkillGap:
    skill: str
    category: str
    jd_context: str
    score_impact: float
    difficulty: str
    suggestion: str


@dataclass
class SkillGapAnalysis:
    total_gaps: int
    critical_gaps: list[SkillGap]
    recommended_gaps: list[SkillGap]
    bonus_gaps: list[SkillGap]
    matched_skills: list[str]
    match_percentage: float
    total_potential_score_gain: float
    top_3_highest_impact_gaps: list[SkillGap]
    quick_wins: list[str]
    short_term: list[str]
    long_term: list[str]


SKILL_SYNONYMS: dict[str, list[str]] = {
    "react": ["react.js", "reactjs", "react 18", "react 19"],
    "vue": ["vue.js", "vuejs", "vue 3"],
    "angular": ["angular.js", "angularjs", "angular 17"],
    "node": ["node.js", "nodejs"],
    "next": ["next.js", "nextjs"],
    "python": ["python3", "cpython", "python 3"],
    "postgres": ["postgresql", "psql", "pg"],
    "mongo": ["mongodb", "mongoose"],
    "kubernetes": ["k8s"],
    "aws": ["amazon web services", "amazon aws"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure"],
    "ci/cd": ["cicd", "continuous integration", "continuous deployment", "ci cd"],
    "ml": ["machine learning"],
    "ai": ["artificial intelligence"],
    "dl": ["deep learning"],
    "nlp": ["natural language processing"],
    "cv": ["computer vision"],
    "tf": ["tensorflow"],
    "torch": ["pytorch"],
    "js": ["javascript"],
    "ts": ["typescript"],
    "cpp": ["c++", "cplusplus"],
    "csharp": ["c#"],
    "go": ["golang"],
    "ruby": ["ruby on rails", "ror"],
    "rails": ["ruby on rails", "ror"],
    "docker": ["containerization", "containers"],
    "terraform": ["iac", "infrastructure as code"],
    "redis": ["elasticache"],
    "kafka": ["event streaming", "message queue", "apache kafka"],
    "rabbitmq": ["message broker", "amqp"],
    "graphql": ["graph ql"],
    "grpc": ["g-rpc", "remote procedure call"],
    "spark": ["apache spark", "pyspark"],
    "hadoop": ["hdfs", "mapreduce"],
    "elasticsearch": ["elastic search", "es", "opensearch"],
    "datadog": ["dd", "monitoring"],
    "grafana": ["observability"],
    "prometheus": ["prom"],
    "jenkins": ["ci server"],
    "github actions": ["gh actions", "gha"],
    "circleci": ["circle ci"],
    "airflow": ["apache airflow"],
    "dbt": ["data build tool"],
    "snowflake": ["snowflake db"],
    "bigquery": ["bq", "big query"],
    "dynamodb": ["dynamo db", "dynamo"],
    "cassandra": ["apache cassandra"],
    "sql": ["structured query language"],
    "nosql": ["no-sql"],
    "rest": ["restful", "rest api"],
    "agile": ["scrum", "kanban methodology"],
    "linux": ["unix", "ubuntu", "centos", "debian"],
    "git": ["version control", "github", "gitlab"],
    # DevOps / CI
    "github actions": ["gh actions", "gha"],
    "gitlab ci": ["gitlab-ci", "gitlab ci/cd"],
    "s3": ["amazon s3", "aws s3"],
    "ec2": ["amazon ec2", "aws ec2"],
    "lambda": ["aws lambda", "serverless"],
    "bigquery": ["google bigquery", "bq"],
    # Data
    "etl": ["elt", "data pipeline", "data ingestion"],
    "snowflake": ["snowflake db"],
    "databricks": ["delta lake"],
    "tableau": ["tableau desktop", "tableau server"],
    "power bi": ["powerbi", "power-bi"],
    # Testing
    "pytest": ["py.test"],
    "jest": ["jest testing"],
    "cypress": ["cypress.io"],
    "selenium": ["selenium webdriver"],
    # Methodologies
    "agile": ["scrum", "kanban methodology", "sprint planning"],
    "microservices": ["micro-services", "service-oriented", "soa"],
    "event driven": ["event-driven", "event sourcing", "cqrs"],
    "rest api": ["restful", "restful api"],
    # Soft skills
    "leadership": ["team lead", "tech lead", "people management", "mentoring"],
    "communication": ["stakeholder management", "cross-functional", "presentations"],
}

SKILL_CATEGORIES: dict[str, list[str]] = {
    "spa_framework": ["react", "vue", "angular", "svelte", "solid", "next"],
    "backend_framework": ["fastapi", "django", "flask", "express", "spring", "rails", "gin", "fiber"],
    "cloud_provider": ["aws", "gcp", "azure"],
    "container": ["docker", "kubernetes", "podman"],
    "database_sql": ["postgres", "mysql", "sqlite", "mssql", "sql"],
    "database_nosql": ["mongo", "dynamodb", "cassandra", "redis", "couchdb"],
    "message_queue": ["kafka", "rabbitmq", "sqs", "pulsar", "nats"],
    "language_systems": ["go", "rust", "cpp", "c"],
    "language_scripting": ["python", "javascript", "typescript", "ruby", "php"],
    "ml_framework": ["tensorflow", "pytorch", "jax", "scikit-learn", "torch", "tf"],
    "iac": ["terraform", "pulumi", "cloudformation", "ansible", "chef"],
    "monitoring": ["datadog", "grafana", "prometheus", "new relic", "splunk"],
    "data_pipeline": ["spark", "airflow", "dbt", "hadoop", "flink"],
    "search": ["elasticsearch", "solr", "opensearch"],
    "ci_cd": ["jenkins", "github actions", "circleci", "gitlab ci"],
}


def _normalize(skill: str) -> str:
    return re.sub(r"[^a-z0-9+#/]", "", skill.lower().strip())


def _build_synonym_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for canonical, synonyms in SKILL_SYNONYMS.items():
        norm = _normalize(canonical)
        mapping[norm] = canonical
        for syn in synonyms:
            mapping[_normalize(syn)] = canonical
    return mapping


_SYNONYM_MAP = _build_synonym_map()


def _canonicalize(skill: str) -> str:
    norm = _normalize(skill)
    return _SYNONYM_MAP.get(norm, skill.lower().strip())


def _get_category(skill: str) -> str | None:
    canon = _canonicalize(skill)
    for cat, members in SKILL_CATEGORIES.items():
        if canon in [_canonicalize(m) for m in members]:
            return cat
    return None


def _extract_resume_skills(resume: Resume) -> set[str]:
    skills: set[str] = set()
    for skill_list in resume.skills.values():
        for s in skill_list:
            skills.add(_canonicalize(s))
    for exp in resume.work_experience:
        for t in exp.technologies:
            skills.add(_canonicalize(t))
        for bullet in exp.bullets:
            for known in SKILL_SYNONYMS:
                if re.search(rf"\b{re.escape(known)}\b", bullet, re.IGNORECASE):
                    skills.add(_canonicalize(known))
    if resume.raw_text:
        for known in SKILL_SYNONYMS:
            if re.search(rf"\b{re.escape(known)}\b", resume.raw_text, re.IGNORECASE):
                skills.add(_canonicalize(known))
    return skills


def _extract_jd_skills(jd: JobDescription) -> dict[str, str]:
    """Returns {canonical_skill: category} where category is required/preferred/bonus."""
    skills: dict[str, str] = {}
    for s in jd.required_skills:
        skills[_canonicalize(s)] = "required"
    for s in jd.preferred_skills:
        canon = _canonicalize(s)
        if canon not in skills:
            skills[canon] = "preferred"
    for s in jd.tech_stack:
        canon = _canonicalize(s)
        if canon not in skills:
            skills[canon] = "required"
    for req in jd.requirements:
        canon = _canonicalize(req.extracted_keyword)
        if canon not in skills:
            cat = "required" if req.category == "must_have" else ("preferred" if req.category == "nice_to_have" else "bonus")
            skills[canon] = cat
    return skills


def _is_match(resume_skill: str, jd_skill: str) -> bool:
    return _canonicalize(resume_skill) == _canonicalize(jd_skill)


def _is_category_match(resume_skills: set[str], jd_skill: str) -> str | None:
    jd_cat = _get_category(jd_skill)
    if not jd_cat:
        return None
    for rs in resume_skills:
        if _get_category(rs) == jd_cat:
            return rs
    return None


def _estimate_impact(category: str, weight_base: float = 6.0) -> float:
    multiplier = {"required": 1.5, "preferred": 1.0, "bonus": 0.5}
    return round(weight_base * multiplier.get(category, 1.0), 1)


def _assess_difficulty(skill: str, resume_skills: set[str]) -> str:
    skill_cat = _get_category(skill)
    if skill_cat:
        for rs in resume_skills:
            if _get_category(rs) == skill_cat:
                return "easy"
    return "medium" if len(resume_skills) > 5 else "hard"


def _generate_suggestion(skill: str, difficulty: str, resume_skills: set[str]) -> str:
    if difficulty == "easy":
        related = _is_category_match(resume_skills, skill)
        if related:
            return f"You have {related} experience — reframe it to mention {skill} in context"
        return f"Add {skill} to your skills section — adjacent to your existing stack"
    elif difficulty == "medium":
        return f"Build a small project with {skill} (1-2 weeks) and add it to Projects section"
    return f"Gain hands-on {skill} experience through a course or open-source contribution (1-3 months)"


def analyze_skill_gaps(resume: Resume, jd: JobDescription) -> SkillGapAnalysis:
    resume_skills = _extract_resume_skills(resume)
    jd_skills = _extract_jd_skills(jd)

    matched: list[str] = []
    gaps: list[SkillGap] = []

    for jd_skill, jd_category in jd_skills.items():
        if jd_skill in resume_skills:
            matched.append(jd_skill)
            continue

        category_match = _is_category_match(resume_skills, jd_skill)
        if category_match:
            matched.append(jd_skill)
            continue

        difficulty = _assess_difficulty(jd_skill, resume_skills)
        impact = _estimate_impact(jd_category)
        suggestion = _generate_suggestion(jd_skill, difficulty, resume_skills)

        jd_context = ""
        for req in jd.requirements:
            if _canonicalize(req.extracted_keyword) == jd_skill:
                jd_context = req.text
                break
        if not jd_context:
            jd_context = f"Listed as {jd_category} in the job description"

        gaps.append(SkillGap(
            skill=jd_skill,
            category=jd_category,
            jd_context=jd_context,
            score_impact=impact,
            difficulty=difficulty,
            suggestion=suggestion,
        ))

    required_total = sum(1 for c in jd_skills.values() if c == "required")
    required_matched = sum(1 for s in matched if jd_skills.get(s) == "required")
    match_pct = (required_matched / required_total * 100) if required_total > 0 else 100.0

    critical = [g for g in gaps if g.category == "required"]
    recommended = [g for g in gaps if g.category == "preferred"]
    bonus = [g for g in gaps if g.category == "bonus"]

    all_gaps_sorted = sorted(gaps, key=lambda g: g.score_impact, reverse=True)
    top_3 = all_gaps_sorted[:3]

    quick_wins = [g.suggestion for g in gaps if g.difficulty == "easy"]
    short_term = [g.suggestion for g in gaps if g.difficulty == "medium"]
    long_term = [g.suggestion for g in gaps if g.difficulty == "hard"]

    return SkillGapAnalysis(
        total_gaps=len(gaps),
        critical_gaps=critical,
        recommended_gaps=recommended,
        bonus_gaps=bonus,
        matched_skills=matched,
        match_percentage=round(match_pct, 1),
        total_potential_score_gain=round(sum(g.score_impact for g in gaps), 1),
        top_3_highest_impact_gaps=top_3,
        quick_wins=quick_wins,
        short_term=short_term,
        long_term=long_term,
    )
