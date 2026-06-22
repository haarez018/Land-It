"""
Generic JD templates — one representative JD per (role_type, seniority) pair.

These are NOT real JDs. They're composite templates representing the AVERAGE
requirements for each role type, used for baseline scoring during onboarding.
"""

from __future__ import annotations

from backend.parsers.schemas import JobDescription, JDRequirement

# ── Templates ────────────────────────────────────────────────────────────────

_TEMPLATES: dict[tuple[str, str], dict] = {
    ("software_engineer_backend", "mid"): {
        "title": "Backend Software Engineer",
        "raw_text": (
            "Backend Software Engineer\n\n"
            "We're looking for a mid-level backend engineer to build and maintain "
            "scalable APIs and services. You'll work with a small team shipping "
            "features end-to-end.\n\n"
            "Requirements:\n"
            "- 3+ years backend development experience\n"
            "- Proficiency in Python, Go, or Java\n"
            "- Experience with SQL databases (PostgreSQL, MySQL)\n"
            "- RESTful API design and implementation\n"
            "- Git, CI/CD, automated testing\n\n"
            "Nice to have:\n"
            "- Docker, Kubernetes\n"
            "- Message queues (Kafka, RabbitMQ)\n"
            "- Cloud platforms (AWS, GCP)\n"
            "- Microservices architecture experience\n"
        ),
        "required_skills": ["Python", "SQL", "REST APIs", "Git"],
        "preferred_skills": ["Docker", "Kubernetes", "Kafka", "AWS"],
        "tech_stack": ["Python", "PostgreSQL", "Docker", "AWS", "Redis"],
        "seniority_level": "mid",
        "required_experience_years": 3,
        "requirements": [
            {"text": "3+ years backend development", "category": "must_have", "skill_type": "technical", "extracted_keyword": "backend"},
            {"text": "Python, Go, or Java proficiency", "category": "must_have", "skill_type": "technical", "extracted_keyword": "python"},
            {"text": "SQL database experience", "category": "must_have", "skill_type": "technical", "extracted_keyword": "sql"},
            {"text": "RESTful API design", "category": "must_have", "skill_type": "technical", "extracted_keyword": "api"},
        ],
    },
    ("software_engineer_backend", "senior"): {
        "title": "Senior Backend Engineer",
        "raw_text": (
            "Senior Backend Engineer\n\n"
            "We need a senior backend engineer to design and build scalable "
            "distributed systems. You'll lead technical decisions, mentor junior "
            "engineers, and own critical infrastructure.\n\n"
            "Requirements:\n"
            "- 5+ years backend development experience\n"
            "- Expert in Python, Go, or Java\n"
            "- Distributed systems design (microservices, event-driven)\n"
            "- PostgreSQL, Redis, message queues\n"
            "- Strong API design skills\n"
            "- Experience leading technical projects\n\n"
            "Nice to have:\n"
            "- Kubernetes, Docker orchestration\n"
            "- Kafka or similar streaming platforms\n"
            "- System design at scale (>1M users)\n"
            "- Performance optimization experience\n"
        ),
        "required_skills": ["Python", "Go", "Distributed Systems", "PostgreSQL", "API Design"],
        "preferred_skills": ["Kubernetes", "Kafka", "gRPC", "AWS"],
        "tech_stack": ["Python", "Go", "PostgreSQL", "Kafka", "Kubernetes", "AWS", "Redis"],
        "seniority_level": "senior",
        "required_experience_years": 5,
        "requirements": [
            {"text": "5+ years backend development", "category": "must_have", "skill_type": "technical", "extracted_keyword": "backend"},
            {"text": "Distributed systems design", "category": "must_have", "skill_type": "technical", "extracted_keyword": "distributed systems"},
            {"text": "Technical leadership experience", "category": "must_have", "skill_type": "soft", "extracted_keyword": "leadership"},
            {"text": "Strong API design skills", "category": "must_have", "skill_type": "technical", "extracted_keyword": "api design"},
        ],
    },
    ("software_engineer_frontend", "mid"): {
        "title": "Frontend Engineer",
        "raw_text": (
            "Frontend Engineer\n\n"
            "Build modern, responsive web applications. You'll implement UI "
            "components, optimize performance, and collaborate with designers.\n\n"
            "Requirements:\n"
            "- 3+ years frontend development\n"
            "- React or Vue.js proficiency\n"
            "- TypeScript, HTML5, CSS3\n"
            "- Responsive design, accessibility\n"
            "- State management (Redux, Zustand)\n\n"
            "Nice to have:\n"
            "- Next.js or Nuxt.js\n"
            "- Testing (Jest, Cypress)\n"
            "- Design systems experience\n"
        ),
        "required_skills": ["React", "TypeScript", "HTML", "CSS"],
        "preferred_skills": ["Next.js", "Jest", "Cypress", "Figma"],
        "tech_stack": ["React", "TypeScript", "Next.js", "TailwindCSS", "Jest"],
        "seniority_level": "mid",
        "required_experience_years": 3,
        "requirements": [
            {"text": "3+ years frontend development", "category": "must_have", "skill_type": "technical", "extracted_keyword": "frontend"},
            {"text": "React or Vue.js proficiency", "category": "must_have", "skill_type": "technical", "extracted_keyword": "react"},
            {"text": "TypeScript experience", "category": "must_have", "skill_type": "technical", "extracted_keyword": "typescript"},
        ],
    },
    ("software_engineer_frontend", "senior"): {
        "title": "Senior Frontend Engineer",
        "raw_text": (
            "Senior Frontend Engineer\n\n"
            "Lead frontend architecture and mentor the team. Own performance, "
            "accessibility, and design system implementation.\n\n"
            "Requirements:\n"
            "- 5+ years frontend development\n"
            "- Expert in React and TypeScript\n"
            "- Performance optimization (Core Web Vitals)\n"
            "- Design systems and component libraries\n"
            "- State management architecture\n\n"
            "Nice to have:\n"
            "- Micro-frontend experience\n"
            "- GraphQL\n"
            "- E2E testing frameworks\n"
        ),
        "required_skills": ["React", "TypeScript", "Performance", "Design Systems"],
        "preferred_skills": ["GraphQL", "Micro-frontends", "Playwright"],
        "tech_stack": ["React", "TypeScript", "Next.js", "GraphQL", "TailwindCSS"],
        "seniority_level": "senior",
        "required_experience_years": 5,
        "requirements": [
            {"text": "5+ years frontend development", "category": "must_have", "skill_type": "technical", "extracted_keyword": "frontend"},
            {"text": "Expert React and TypeScript", "category": "must_have", "skill_type": "technical", "extracted_keyword": "react"},
            {"text": "Performance optimization experience", "category": "must_have", "skill_type": "technical", "extracted_keyword": "performance"},
        ],
    },
    ("ml_engineer", "mid"): {
        "title": "Machine Learning Engineer",
        "raw_text": (
            "Machine Learning Engineer\n\n"
            "Build and deploy ML models in production. Work with data scientists "
            "to take research to production systems.\n\n"
            "Requirements:\n"
            "- 3+ years ML engineering experience\n"
            "- Python, PyTorch or TensorFlow\n"
            "- ML model training and evaluation\n"
            "- Data pipelines (Spark, Airflow)\n"
            "- Docker, cloud ML services\n\n"
            "Nice to have:\n"
            "- MLOps (MLflow, Kubeflow)\n"
            "- Real-time inference systems\n"
            "- NLP or computer vision specialization\n"
        ),
        "required_skills": ["Python", "PyTorch", "TensorFlow", "ML"],
        "preferred_skills": ["MLOps", "Spark", "Kubeflow"],
        "tech_stack": ["Python", "PyTorch", "TensorFlow", "Spark", "Docker", "AWS"],
        "seniority_level": "mid",
        "required_experience_years": 3,
        "requirements": [
            {"text": "3+ years ML engineering", "category": "must_have", "skill_type": "technical", "extracted_keyword": "machine learning"},
            {"text": "Python proficiency", "category": "must_have", "skill_type": "technical", "extracted_keyword": "python"},
            {"text": "ML model training and evaluation", "category": "must_have", "skill_type": "technical", "extracted_keyword": "ml"},
        ],
    },
    ("ml_engineer", "senior"): {
        "title": "Senior ML Engineer",
        "raw_text": (
            "Senior ML Engineer\n\n"
            "Lead ML system architecture. Design training pipelines, inference "
            "infrastructure, and model monitoring at scale.\n\n"
            "Requirements:\n"
            "- 5+ years ML engineering\n"
            "- Expert in PyTorch/TensorFlow\n"
            "- Large-scale distributed training\n"
            "- Production ML systems\n"
            "- Strong software engineering foundations\n\n"
            "Nice to have:\n"
            "- LLM fine-tuning experience\n"
            "- Recommendation systems\n"
            "- GPU optimization (CUDA)\n"
        ),
        "required_skills": ["Python", "PyTorch", "Distributed Training", "MLOps"],
        "preferred_skills": ["LLM", "CUDA", "Recommendation Systems"],
        "tech_stack": ["Python", "PyTorch", "Kubernetes", "Spark", "AWS", "Docker"],
        "seniority_level": "senior",
        "required_experience_years": 5,
        "requirements": [
            {"text": "5+ years ML engineering", "category": "must_have", "skill_type": "technical", "extracted_keyword": "machine learning"},
            {"text": "Distributed training experience", "category": "must_have", "skill_type": "technical", "extracted_keyword": "distributed"},
            {"text": "Production ML systems", "category": "must_have", "skill_type": "technical", "extracted_keyword": "production ml"},
        ],
    },
    ("data_scientist", "mid"): {
        "title": "Data Scientist",
        "raw_text": (
            "Data Scientist\n\n"
            "Analyze data to drive product decisions. Build models, run A/B tests, "
            "and present insights to stakeholders.\n\n"
            "Requirements:\n"
            "- 3+ years data science experience\n"
            "- Python, SQL, statistics\n"
            "- ML model building (scikit-learn, XGBoost)\n"
            "- A/B testing and experimentation\n"
            "- Data visualization (Tableau, Matplotlib)\n\n"
            "Nice to have:\n"
            "- Spark/PySpark\n"
            "- Deep learning basics\n"
            "- Product analytics experience\n"
        ),
        "required_skills": ["Python", "SQL", "Statistics", "ML"],
        "preferred_skills": ["Spark", "Tableau", "Deep Learning"],
        "tech_stack": ["Python", "SQL", "Pandas", "scikit-learn", "Jupyter"],
        "seniority_level": "mid",
        "required_experience_years": 3,
        "requirements": [
            {"text": "3+ years data science", "category": "must_have", "skill_type": "technical", "extracted_keyword": "data science"},
            {"text": "Python and SQL proficiency", "category": "must_have", "skill_type": "technical", "extracted_keyword": "python"},
            {"text": "Statistical analysis", "category": "must_have", "skill_type": "technical", "extracted_keyword": "statistics"},
        ],
    },
    ("data_scientist", "senior"): {
        "title": "Senior Data Scientist",
        "raw_text": (
            "Senior Data Scientist\n\n"
            "Lead data science initiatives. Define experimentation strategy, "
            "build complex models, and mentor junior scientists.\n\n"
            "Requirements:\n"
            "- 5+ years data science experience\n"
            "- Advanced statistical modeling\n"
            "- Python, SQL, Spark\n"
            "- Experimentation platform design\n"
            "- Cross-functional leadership\n\n"
            "Nice to have:\n"
            "- Causal inference methods\n"
            "- PhD in quantitative field\n"
            "- Publishing track record\n"
        ),
        "required_skills": ["Python", "SQL", "Statistics", "Spark", "Leadership"],
        "preferred_skills": ["Causal Inference", "PhD", "Publications"],
        "tech_stack": ["Python", "SQL", "Spark", "Airflow", "Jupyter"],
        "seniority_level": "senior",
        "required_experience_years": 5,
        "requirements": [
            {"text": "5+ years data science", "category": "must_have", "skill_type": "technical", "extracted_keyword": "data science"},
            {"text": "Advanced statistical modeling", "category": "must_have", "skill_type": "technical", "extracted_keyword": "statistics"},
            {"text": "Cross-functional leadership", "category": "must_have", "skill_type": "soft", "extracted_keyword": "leadership"},
        ],
    },
    ("product_manager", "mid"): {
        "title": "Product Manager",
        "raw_text": (
            "Product Manager\n\n"
            "Own product roadmap and work with engineering to ship features. "
            "Define requirements, prioritize backlog, and measure success.\n\n"
            "Requirements:\n"
            "- 3+ years product management\n"
            "- Data-driven decision making\n"
            "- Strong communication and stakeholder management\n"
            "- Agile/Scrum experience\n"
            "- User research and product analytics\n\n"
            "Nice to have:\n"
            "- Technical background\n"
            "- B2B SaaS experience\n"
            "- SQL proficiency\n"
        ),
        "required_skills": ["Product Management", "Agile", "Analytics", "Communication"],
        "preferred_skills": ["SQL", "B2B SaaS", "Technical Background"],
        "tech_stack": ["Jira", "Amplitude", "SQL", "Figma"],
        "seniority_level": "mid",
        "required_experience_years": 3,
        "requirements": [
            {"text": "3+ years product management", "category": "must_have", "skill_type": "domain", "extracted_keyword": "product management"},
            {"text": "Data-driven decision making", "category": "must_have", "skill_type": "soft", "extracted_keyword": "data-driven"},
            {"text": "Stakeholder management", "category": "must_have", "skill_type": "soft", "extracted_keyword": "stakeholder"},
        ],
    },
    ("product_manager", "senior"): {
        "title": "Senior Product Manager",
        "raw_text": (
            "Senior Product Manager\n\n"
            "Lead product strategy for a major product area. Drive vision, "
            "align teams, and deliver measurable business outcomes.\n\n"
            "Requirements:\n"
            "- 5+ years product management\n"
            "- Track record of shipping 0-to-1 products\n"
            "- Strategic thinking and business acumen\n"
            "- Cross-functional team leadership\n"
            "- Quantified impact on business metrics\n\n"
            "Nice to have:\n"
            "- MBA or equivalent\n"
            "- Platform/infrastructure PM experience\n"
            "- Market sizing and competitive analysis\n"
        ),
        "required_skills": ["Product Strategy", "Leadership", "Analytics", "Shipping"],
        "preferred_skills": ["MBA", "Platform PM", "Competitive Analysis"],
        "tech_stack": ["Jira", "Amplitude", "SQL", "Figma", "Mixpanel"],
        "seniority_level": "senior",
        "required_experience_years": 5,
        "requirements": [
            {"text": "5+ years product management", "category": "must_have", "skill_type": "domain", "extracted_keyword": "product management"},
            {"text": "0-to-1 product shipping track record", "category": "must_have", "skill_type": "domain", "extracted_keyword": "shipping"},
            {"text": "Business impact with metrics", "category": "must_have", "skill_type": "soft", "extracted_keyword": "impact"},
        ],
    },
    ("devops_sre", "mid"): {
        "title": "DevOps / SRE Engineer",
        "raw_text": (
            "DevOps / SRE Engineer\n\n"
            "Build and maintain CI/CD pipelines, infrastructure, and monitoring. "
            "Ensure reliability and uptime of production systems.\n\n"
            "Requirements:\n"
            "- 3+ years DevOps/SRE experience\n"
            "- Kubernetes, Docker, Terraform\n"
            "- CI/CD pipeline design (GitHub Actions, Jenkins)\n"
            "- Cloud platforms (AWS, GCP, Azure)\n"
            "- Monitoring (Prometheus, Grafana, Datadog)\n\n"
            "Nice to have:\n"
            "- Python or Go scripting\n"
            "- Incident management experience\n"
            "- Cost optimization\n"
        ),
        "required_skills": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD"],
        "preferred_skills": ["Python", "Go", "Prometheus", "Datadog"],
        "tech_stack": ["Kubernetes", "Docker", "Terraform", "AWS", "GitHub Actions"],
        "seniority_level": "mid",
        "required_experience_years": 3,
        "requirements": [
            {"text": "3+ years DevOps/SRE", "category": "must_have", "skill_type": "technical", "extracted_keyword": "devops"},
            {"text": "Kubernetes and Docker", "category": "must_have", "skill_type": "technical", "extracted_keyword": "kubernetes"},
            {"text": "Cloud platform experience", "category": "must_have", "skill_type": "technical", "extracted_keyword": "cloud"},
        ],
    },
    ("devops_sre", "senior"): {
        "title": "Senior SRE / Platform Engineer",
        "raw_text": (
            "Senior SRE / Platform Engineer\n\n"
            "Design platform infrastructure, lead incident response, and drive "
            "reliability improvements across the organization.\n\n"
            "Requirements:\n"
            "- 5+ years SRE/platform engineering\n"
            "- Expert Kubernetes administration\n"
            "- Infrastructure-as-code at scale\n"
            "- SLO/SLI framework design\n"
            "- On-call leadership and incident management\n\n"
            "Nice to have:\n"
            "- Multi-region/multi-cloud\n"
            "- FinOps / cost optimization\n"
            "- Internal developer platform design\n"
        ),
        "required_skills": ["Kubernetes", "Terraform", "SRE", "Cloud", "IaC"],
        "preferred_skills": ["Multi-cloud", "FinOps", "Platform Engineering"],
        "tech_stack": ["Kubernetes", "Terraform", "AWS", "GCP", "Prometheus", "Go"],
        "seniority_level": "senior",
        "required_experience_years": 5,
        "requirements": [
            {"text": "5+ years SRE/platform engineering", "category": "must_have", "skill_type": "technical", "extracted_keyword": "sre"},
            {"text": "Kubernetes administration at scale", "category": "must_have", "skill_type": "technical", "extracted_keyword": "kubernetes"},
            {"text": "Incident management leadership", "category": "must_have", "skill_type": "soft", "extracted_keyword": "incident"},
        ],
    },
}


def get_generic_jd(role_type: str, seniority: str = "mid") -> JobDescription:
    """
    Return a parsed JobDescription from the generic template.

    Falls back to (role_type, "mid") if the exact (role_type, seniority) combo
    isn't found, then to ("software_engineer_backend", "mid") as ultimate fallback.
    """
    key = (role_type, seniority)
    if key not in _TEMPLATES:
        key = (role_type, "mid")
    if key not in _TEMPLATES:
        key = ("software_engineer_backend", "mid")

    t = _TEMPLATES[key]

    return JobDescription(
        raw_text=t["raw_text"],
        title=t["title"],
        company="Generic Company",
        seniority_level=t["seniority_level"],
        required_skills=t["required_skills"],
        preferred_skills=t["preferred_skills"],
        tech_stack=t["tech_stack"],
        required_experience_years=t.get("required_experience_years"),
        requirements=[
            JDRequirement(**r)
            for r in t["requirements"]
        ],
    )


def list_available_templates() -> list[tuple[str, str]]:
    """Return all available (role_type, seniority) template keys."""
    return list(_TEMPLATES.keys())
