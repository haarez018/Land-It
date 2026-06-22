"""Parse raw job description text into the JobDescription schema using regex + structure extraction."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from backend.parsers.schemas import JDRequirement, JobDescription

# ---------------------------------------------------------------------------
# Known tech keywords for extraction
# ---------------------------------------------------------------------------

_TECH_KEYWORDS = {
    "languages": [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "Perl", "Haskell",
        "Elixir", "Clojure", "Dart", "Lua", "MATLAB", "Julia",
    ],
    "frameworks": [
        "React", "Vue", "Angular", "Next.js", "Nuxt", "Svelte", "Django", "Flask",
        "FastAPI", "Spring", "Spring Boot", "Express", "Node.js", "Rails",
        "ASP.NET", "Laravel", "Gin", "Echo", "Actix", "Rocket", "NestJS",
        "Remix", "Gatsby", "TailwindCSS", "Bootstrap",
    ],
    "databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB",
        "Cassandra", "SQLite", "Oracle", "SQL Server", "CockroachDB", "Neo4j",
        "InfluxDB", "TimescaleDB", "Supabase", "Firebase",
    ],
    "cloud_infra": [
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible",
        "Jenkins", "GitHub Actions", "CircleCI", "GitLab CI", "ArgoCD",
        "Pulumi", "CloudFormation", "Helm", "Istio", "Envoy",
    ],
    "data_ml": [
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Spark",
        "Hadoop", "Airflow", "dbt", "Snowflake", "BigQuery", "Redshift",
        "Databricks", "MLflow", "Kubeflow", "Hugging Face", "LangChain",
        "OpenAI", "Anthropic",
    ],
    "tools": [
        "Git", "Jira", "Confluence", "Figma", "Notion", "Linear", "Slack",
        "Datadog", "Grafana", "Prometheus", "Sentry", "PagerDuty", "Splunk",
        "New Relic",
    ],
    "protocols": [
        "REST", "GraphQL", "gRPC", "WebSocket", "MQTT", "AMQP", "HTTP/2",
        "OAuth", "SAML", "OpenID Connect",
    ],
}

_ALL_TECH = []
for group in _TECH_KEYWORDS.values():
    _ALL_TECH.extend(group)

_TECH_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(_ALL_TECH, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Soft skills
# ---------------------------------------------------------------------------

_SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "collaboration", "problem-solving",
    "problem solving", "critical thinking", "time management", "adaptability",
    "creativity", "attention to detail", "self-motivated", "mentoring",
    "cross-functional", "stakeholder management", "interpersonal",
    "presentation", "written communication", "verbal communication",
    "analytical", "strategic thinking", "decision-making", "conflict resolution",
    "empathy", "accountability", "initiative", "ownership",
]

_SOFT_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in _SOFT_SKILLS) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Section identification
# ---------------------------------------------------------------------------

_JD_SECTION_HEADERS = [
    "about the role", "about the position", "about us", "about the team",
    "responsibilities", "what you'll do", "what you will do", "role overview",
    "requirements", "qualifications", "what we're looking for",
    "what you'll need", "what you need", "minimum qualifications",
    "preferred qualifications", "nice to have", "bonus",
    "benefits", "perks", "compensation", "what we offer",
    "tech stack", "technologies", "tools we use",
    "who you are", "ideal candidate",
]

_JD_HEADER_PATTERN = re.compile(
    r"^(?:#+\s*)?(?P<header>" +
    "|".join(re.escape(h) for h in _JD_SECTION_HEADERS) +
    r")\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _split_jd_sections(text: str) -> dict[str, str]:
    matches = list(_JD_HEADER_PATTERN.finditer(text))
    if not matches:
        return {"full_text": text}

    sections: dict[str, str] = {}
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections["preamble"] = preamble

    for i, match in enumerate(matches):
        key = match.group("header").strip().lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[key] = text[start:end].strip()

    return sections


# ---------------------------------------------------------------------------
# Title, company, metadata extraction
# ---------------------------------------------------------------------------

_SALARY_PATTERNS = [
    re.compile(r"\$\s*([\d,]+)\s*[-–—to]+\s*\$?\s*([\d,]+)"),
    re.compile(r"\$\s*(\d+)\s*[kK]\s*[-–—to]+\s*\$?\s*(\d+)\s*[kK]"),
    re.compile(r"\$\s*(\d+)\s*[-–—]\s*(\d+)\s*[kK]"),
    re.compile(r"([\d,]+)\s*[-–—to]+\s*([\d,]+)\s*(?:USD|EUR|GBP)"),
]

_SALARY_RE = re.compile(
    r"\$\s*([\d,]+)\s*(?:K|k)?\s*[-–—to]+\s*\$?\s*([\d,]+)\s*(?:K|k)?",
)

_YOE_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    re.IGNORECASE,
)

_REMOTE_RE = re.compile(
    r"\b(remote|hybrid|on-?site|in-?office)\b",
    re.IGNORECASE,
)

_EMPLOYMENT_RE = re.compile(
    r"\b(full[- ]?time|part[- ]?time|contract|freelance|internship|intern)\b",
    re.IGNORECASE,
)

_SENIORITY_RE = re.compile(
    r"\b(intern|junior|entry[- ]level|mid[- ]level|senior|staff|principal|lead|"
    r"director|vp|head of|chief|executive|manager|sr\.?|jr\.?)\b",
    re.IGNORECASE,
)

_EDUCATION_RE = re.compile(
    r"(?:Bachelor|Master|Ph\.?D|Doctorate|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|MBA|"
    r"B\.?E\.?|M\.?E\.?|B\.?Tech|M\.?Tech|degree)\s*(?:in\s+[A-Za-z\s]+)?",
    re.IGNORECASE,
)


def _extract_title(text: str) -> str:
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if 10 < len(line) < 80 and not line.startswith("http"):
            return line
    return "Unknown Role"


def _extract_company(text: str) -> str:
    patterns = [
        re.compile(r"(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\n|,|\s-)", re.MULTILINE),
        re.compile(r"^([A-Z][A-Za-z0-9\s&.]{2,30})\s*$", re.MULTILINE),
    ]
    for pattern in patterns:
        match = pattern.search(text[:500])
        if match:
            return match.group(1).strip()
    return "Unknown Company"


def _infer_seniority(text: str) -> str:
    matches = _SENIORITY_RE.findall(text[:500])
    if not matches:
        return "mid"
    first = matches[0].lower().replace(".", "").replace("-", " ").strip()
    mapping = {
        "intern": "intern", "junior": "junior", "jr": "junior",
        "entry level": "junior", "mid level": "mid", "senior": "senior",
        "sr": "senior", "staff": "staff_principal", "principal": "staff_principal",
        "lead": "senior", "director": "executive", "vp": "executive",
        "head of": "executive", "chief": "executive", "manager": "senior",
        "executive": "executive",
    }
    return mapping.get(first, "mid")


# ---------------------------------------------------------------------------
# Requirements extraction
# ---------------------------------------------------------------------------

_MUST_HAVE_SIGNALS = [
    "required", "must have", "must-have", "minimum", "essential",
    "you need", "you'll need", "you will need", "we require",
]

_NICE_TO_HAVE_SIGNALS = [
    "preferred", "nice to have", "nice-to-have", "bonus", "plus",
    "ideally", "a plus", "advantageous", "desirable",
]


def _classify_requirement(text: str, section_name: str) -> str:
    text_lower = text.lower()
    section_lower = section_name.lower()

    if any(s in section_lower for s in ["preferred", "nice to have", "bonus"]):
        return "nice_to_have"
    if any(s in section_lower for s in ["required", "minimum", "must", "qualifications"]):
        return "must_have"
    if any(s in text_lower for s in _NICE_TO_HAVE_SIGNALS):
        return "nice_to_have"
    if any(s in text_lower for s in _MUST_HAVE_SIGNALS):
        return "must_have"
    return "must_have"


def _classify_skill_type(text: str) -> str:
    if _TECH_PATTERN.search(text):
        return "technical"
    if _SOFT_PATTERN.search(text):
        return "soft"
    if any(kw in text.lower() for kw in ["industry", "domain", "regulatory", "compliance"]):
        return "domain"
    return "technical"


def _extract_keyword(text: str) -> str:
    tech_match = _TECH_PATTERN.search(text)
    if tech_match:
        return tech_match.group()
    soft_match = _SOFT_PATTERN.search(text)
    if soft_match:
        return soft_match.group()
    words = text.split()
    return " ".join(words[:3]) if words else text


def _extract_bullet_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^[-•●*▪▸>\d.)\s]+", "", line).strip()
        if len(cleaned) > 10:
            items.append(cleaned)
    return items


def _extract_requirements(sections: dict[str, str]) -> list[JDRequirement]:
    requirements: list[JDRequirement] = []

    req_sections = {
        k: v for k, v in sections.items()
        if any(s in k.lower() for s in [
            "requirement", "qualification", "what you", "who you",
            "need", "looking for", "nice to have", "preferred", "bonus",
            "ideal candidate",
        ])
    }

    if not req_sections and "full_text" in sections:
        req_sections = {"requirements": sections["full_text"]}

    for section_name, section_text in req_sections.items():
        items = _extract_bullet_items(section_text)
        for item in items:
            requirements.append(JDRequirement(
                text=item,
                category=_classify_requirement(item, section_name),
                skill_type=_classify_skill_type(item),
                extracted_keyword=_extract_keyword(item),
            ))

    return requirements


# ---------------------------------------------------------------------------
# Domain knowledge signals
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS = {
    "fintech": ["payments", "banking", "financial", "trading", "compliance", "PCI", "KYC", "AML"],
    "healthtech": ["healthcare", "HIPAA", "clinical", "EHR", "patient", "medical", "FDA"],
    "edtech": ["education", "learning", "curriculum", "LMS", "student", "academic"],
    "e-commerce": ["e-commerce", "ecommerce", "retail", "catalog", "inventory", "checkout", "cart"],
    "SaaS B2B": ["SaaS", "B2B", "enterprise", "subscription", "ARR", "churn"],
    "gaming": ["game", "gaming", "Unity", "Unreal", "multiplayer", "real-time"],
    "AI/ML": ["machine learning", "deep learning", "NLP", "LLM", "AI", "neural network"],
}


def _extract_domain_knowledge(text: str) -> list[str]:
    found: list[str] = []
    text_lower = text.lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            found.append(domain)
    return found


# ---------------------------------------------------------------------------
# Company values extraction
# ---------------------------------------------------------------------------

_VALUE_SIGNALS = [
    "we value", "we believe", "our values", "our culture", "we care about",
    "we prioritize", "core values",
]


def _extract_company_values(text: str) -> list[str]:
    values: list[str] = []
    for line in text.split("\n"):
        if any(s in line.lower() for s in _VALUE_SIGNALS):
            cleaned = re.sub(r"^.*?(?:values?|believe|care about)\s*:?\s*", "", line, flags=re.IGNORECASE)
            values.extend(v.strip() for v in re.split(r"[,;]", cleaned) if v.strip())
    return values[:10]


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_jd(
    raw_text: str,
    source: str = "manual",
    source_url: str = "",
) -> JobDescription:
    sections = _split_jd_sections(raw_text)

    title = _extract_title(raw_text)
    company = _extract_company(raw_text)

    salary_range = None
    for pattern in _SALARY_PATTERNS:
        salary_match = pattern.search(raw_text)
        if salary_match:
            low = int(salary_match.group(1).replace(",", ""))
            high = int(salary_match.group(2).replace(",", ""))
            if low < 1000:
                low *= 1000
            if high < 1000:
                high *= 1000
            if low < high and low > 10000:
                salary_range = (low, high)
                break
    if salary_range is None:
        salary_match = _SALARY_RE.search(raw_text)
        if salary_match:
            low = int(salary_match.group(1).replace(",", ""))
            high = int(salary_match.group(2).replace(",", ""))
            if low < 1000:
                low *= 1000
            if high < 1000:
                high *= 1000
            if low < high:
                salary_range = (low, high)

    raw_lower = raw_text.lower()
    _full_remote_signals = ["fully remote", "remote-first", "remote only", "100% remote",
                            "work from anywhere", "remote position"]
    _hybrid_signals_exact = ["hybrid", "flexible", "2-3 days in office", "3 days on-site",
                             "partially remote"]
    remote_policy = "onsite"
    if any(s in raw_lower for s in _full_remote_signals):
        remote_policy = "remote"
    elif any(s in raw_lower for s in _hybrid_signals_exact):
        remote_policy = "hybrid"
    else:
        remote_match = _REMOTE_RE.search(raw_text)
        if remote_match:
            r = remote_match.group(1).lower().replace("-", "")
            if "remote" in r:
                remote_policy = "remote"
            elif "hybrid" in r:
                remote_policy = "hybrid"

    employment_match = _EMPLOYMENT_RE.search(raw_text)
    employment_type = "full_time"
    if employment_match:
        e = employment_match.group(1).lower().replace("-", "").replace(" ", "")
        mapping = {
            "fulltime": "full_time", "parttime": "part_time",
            "contract": "contract", "freelance": "contract",
            "internship": "full_time", "intern": "full_time",
        }
        employment_type = mapping.get(e, "full_time")

    yoe_match = _YOE_RE.search(raw_text)
    required_experience_years = int(yoe_match.group(1)) if yoe_match else None

    edu_match = _EDUCATION_RE.search(raw_text)
    required_education = edu_match.group().strip() if edu_match else None

    seniority_level = _infer_seniority(raw_text)

    tech_stack = list(dict.fromkeys(_TECH_PATTERN.findall(raw_text)))
    soft_skills = list(dict.fromkeys(_SOFT_PATTERN.findall(raw_text)))
    domain_knowledge = _extract_domain_knowledge(raw_text)
    company_values = _extract_company_values(raw_text)

    requirements = _extract_requirements(sections)

    required_skills = [
        r.extracted_keyword for r in requirements
        if r.category == "must_have" and r.skill_type == "technical"
    ]
    preferred_skills = [
        r.extracted_keyword for r in requirements
        if r.category == "nice_to_have" and r.skill_type == "technical"
    ]

    role_priorities: list[str] = []
    for key in ("responsibilities", "what you'll do", "what you will do", "role overview"):
        if key in sections:
            items = _extract_bullet_items(sections[key])
            role_priorities = items[:5]
            break

    location_match = re.search(
        r"(?:Location|Based in|Office)[:\s]+([A-Za-z\s,]+?)(?:\n|$)",
        raw_text[:1000],
        re.IGNORECASE,
    )
    location = location_match.group(1).strip() if location_match else ""

    return JobDescription(
        raw_text=raw_text,
        title=title,
        company=company,
        location=location,
        remote_policy=remote_policy,
        salary_range=salary_range,
        seniority_level=seniority_level,
        employment_type=employment_type,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        required_experience_years=required_experience_years,
        required_education=required_education,
        requirements=requirements,
        tech_stack=tech_stack,
        soft_skills=soft_skills,
        domain_knowledge=domain_knowledge,
        company_values=company_values,
        role_priorities=role_priorities,
        source=source,
        source_url=source_url,
    )
