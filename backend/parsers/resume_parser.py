"""Parse PDF/DOCX resumes into the Resume schema using pdfplumber and python-docx."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from backend.parsers.schemas import (
    Certification,
    Education,
    Project,
    Resume,
    ResumeContact,
    WorkExperience,
)

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_path: str | Path) -> str:
    import pdfplumber

    texts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
    return "\n".join(texts)


def extract_text_from_docx(file_path: str | Path) -> str:
    from docx import Document

    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(file_path: str | Path) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(path)
    elif ext == ".txt":
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

SECTION_HEADERS = [
    "summary", "professional summary", "objective", "profile", "about",
    "experience", "work experience", "professional experience", "employment",
    "education", "academic",
    "skills", "technical skills", "core competencies", "technologies",
    "projects", "personal projects", "side projects",
    "certifications", "certificates", "licenses",
    "publications", "papers",
    "awards", "honors", "achievements",
    "languages",
    "volunteer", "volunteering",
    "interests",
]

_HEADER_PATTERN = re.compile(
    r"^(?P<header>" + "|".join(re.escape(h) for h in SECTION_HEADERS) + r")\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def split_sections(text: str) -> dict[str, str]:
    matches = list(_HEADER_PATTERN.finditer(text))
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
# Contact extraction
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", re.IGNORECASE)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s,;]+")


def extract_contact(text: str) -> ResumeContact:
    lines = text.strip().split("\n")

    name = lines[0].strip() if lines else "Unknown"
    if len(name) > 60 or "@" in name:
        name = "Unknown"

    email_match = _EMAIL_RE.search(text)
    email = email_match.group() if email_match else ""

    phone_match = _PHONE_RE.search(text)
    phone = phone_match.group().strip() if phone_match else None

    linkedin_match = _LINKEDIN_RE.search(text)
    linkedin = linkedin_match.group() if linkedin_match else None

    github_match = _GITHUB_RE.search(text)
    github = github_match.group() if github_match else None

    urls = _URL_RE.findall(text)
    portfolio = None
    for url in urls:
        if "linkedin.com" not in url and "github.com" not in url:
            portfolio = url
            break

    location = _extract_location(text)

    return ResumeContact(
        name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        location=location,
        portfolio=portfolio,
    )


def _extract_location(text: str) -> Optional[str]:
    loc_re = re.compile(
        r"(?:^|\n)\s*([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}(?:\s+\d{5})?)\s*(?:\n|$)"
    )
    match = loc_re.search(text[:500])
    if match:
        return match.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

_SEASON_MAP = {"spring": 3, "summer": 6, "fall": 9, "autumn": 9, "winter": 1}

_DATE_RE = re.compile(
    r"(?P<month>[A-Za-z]+)[\s.,/-]*(?P<year>\d{4})"
    r"|(?P<mm>\d{1,2})[/.-](?P<yy>\d{4})"
    r"|(?P<year_only>\d{4})"
)

_QUARTER_RE = re.compile(r"Q([1-4])\s+(\d{4})", re.IGNORECASE)
_SEASON_RE = re.compile(
    r"(Spring|Summer|Fall|Winter|Autumn)\s+(\d{4})", re.IGNORECASE
)


def parse_date_str(s: str) -> Optional[date]:
    s = s.strip()
    if not s:
        return None

    # Quarter format: Q3 2022
    qm = _QUARTER_RE.search(s)
    if qm:
        q = int(qm.group(1))
        return date(int(qm.group(2)), (q - 1) * 3 + 1, 1)

    # Season format: Spring 2019
    sm = _SEASON_RE.search(s)
    if sm:
        month = _SEASON_MAP.get(sm.group(1).lower(), 1)
        return date(int(sm.group(2)), month, 1)

    m = _DATE_RE.search(s)
    if not m:
        return None
    if m.group("month"):
        month_str = m.group("month").lower()
        month = _MONTH_MAP.get(month_str)
        year = int(m.group("year"))
        if month:
            return date(year, month, 1)
    if m.group("mm"):
        return date(int(m.group("yy")), int(m.group("mm")), 1)
    if m.group("year_only"):
        return date(int(m.group("year_only")), 1, 1)
    return None


# ---------------------------------------------------------------------------
# Experience parsing
# ---------------------------------------------------------------------------

_SENIORITY_SIGNALS = [
    "led", "managed", "architected", "spearheaded", "directed", "oversaw",
    "mentored", "defined", "drove", "owned", "headed", "established",
    "scaled", "pioneered", "orchestrated", "transformed",
]

_METRIC_RE = re.compile(
    r"\$[\d,]+[KMBkmb]?"
    r"|\d+\s*%"
    r"|\d+[KMBkmb]\+?\s*(?:users|requests|records|customers|transactions|events)"
    r"|reduced\s+.{0,30}by\s+\d+"
    r"|increased\s+.{0,30}by\s+\d+"
    r"|team\s+of\s+\d+"
    r"|#\d+|top\s+\d+%",
    re.IGNORECASE,
)

_DATE_RANGE_RE = re.compile(
    r"(?P<start>[A-Za-z]+[\s.,/-]*\d{4}|\d{1,2}[/.-]\d{4})"
    r"\s*[-–—to]+\s*"
    r"(?P<end>[A-Za-z]+[\s.,/-]*\d{4}|\d{1,2}[/.-]\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)"
)


def _extract_technologies(text: str) -> list[str]:
    known_tech = [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C\\+\\+", "C#",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R",
        "React", "Vue", "Angular", "Next\\.js", "Svelte", "Django", "Flask", "FastAPI",
        "Spring", "Express", "Node\\.js", "Rails",
        "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Jenkins",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB",
        "Kafka", "RabbitMQ", "GraphQL", "REST", "gRPC",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Spark",
        "Git", "Linux", "CI/CD", "GitHub Actions", "CircleCI",
    ]
    pattern = re.compile(r"\b(" + "|".join(known_tech) + r")\b", re.IGNORECASE)
    found = pattern.findall(text)
    return list(dict.fromkeys(found))


def parse_work_experience(section_text: str) -> list[WorkExperience]:
    # Split on lines that look like a company/role header:
    # A line starting with a capital letter that is NOT a bullet point
    # and is followed by another non-bullet line (title or date line).
    # We use date ranges as strong anchors for block boundaries.
    blocks: list[str] = []
    current_block_lines: list[str] = []

    for line in section_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # If this line contains a date range and we already have content,
        # check if it's the start of a new role block
        has_date = bool(_DATE_RANGE_RE.search(stripped))
        is_bullet = stripped.startswith(("-", "•", "●", "*", "‣"))

        if has_date and not is_bullet and current_block_lines:
            # Look back: if the previous lines don't have a date range yet,
            # this date belongs to the current block. If they do, start new.
            prev_text = "\n".join(current_block_lines)
            if _DATE_RANGE_RE.search(prev_text):
                # Previous block already has dates — this is a new block
                blocks.append("\n".join(current_block_lines))
                current_block_lines = [stripped]
                continue

        # Heuristic: non-bullet, non-date line at the start pattern = new company
        if (
            not is_bullet
            and not has_date
            and len(stripped) < 80
            and current_block_lines
            and len(current_block_lines) > 2
        ):
            prev_has_bullets = any(
                l.strip().startswith(("-", "•", "●", "*", "‣"))
                for l in current_block_lines
            )
            prev_has_date = bool(_DATE_RANGE_RE.search("\n".join(current_block_lines)))
            if prev_has_bullets and prev_has_date:
                # The previous block looks complete — start a new one
                blocks.append("\n".join(current_block_lines))
                current_block_lines = [stripped]
                continue

        current_block_lines.append(stripped)

    if current_block_lines:
        blocks.append("\n".join(current_block_lines))

    experiences: list[WorkExperience] = []

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue

        lines = block.split("\n")
        company = ""
        title = ""
        start = None
        end = None
        location = None
        bullets: list[str] = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            date_match = _DATE_RANGE_RE.search(line_stripped)
            if date_match and i < 4:
                start = parse_date_str(date_match.group("start"))
                end_str = date_match.group("end").lower()
                if end_str in ("present", "current", "now"):
                    end = None
                else:
                    end = parse_date_str(date_match.group("end"))
                remaining = _DATE_RANGE_RE.sub("", line_stripped).strip(" \t|,—-")
                if remaining and not company:
                    company = remaining
                continue

            if i == 0 and not company:
                # First line might be "Company — Title" on one line
                em_dash_split = re.split(r"\s*[—–-]\s*", line_stripped, maxsplit=1)
                if len(em_dash_split) == 2 and len(em_dash_split[1]) > 3:
                    company = em_dash_split[0].strip()
                    title = em_dash_split[1].strip()
                else:
                    company = line_stripped
                continue
            if i <= 2 and not title and not line_stripped.startswith(("-", "•", "●", "*")):
                title = line_stripped
                continue

            if line_stripped.startswith(("-", "•", "●", "*", "‣")):
                bullets.append(line_stripped.lstrip("-•●*‣ ").strip())
            elif len(line_stripped) > 30 and i > 2:
                bullets.append(line_stripped)

        if not company and not title:
            continue
        if not start and not bullets:
            continue

        all_text = " ".join(bullets)
        technologies = _extract_technologies(all_text)
        impact_metrics = _METRIC_RE.findall(all_text)
        seniority_signals = [
            s for s in _SENIORITY_SIGNALS
            if re.search(rf"\b{s}\b", all_text, re.IGNORECASE)
        ]

        experiences.append(WorkExperience(
            company=company or "Unknown",
            title=title or "Unknown",
            start_date=start or date(2020, 1, 1),
            end_date=end,
            location=location,
            bullets=bullets,
            technologies=technologies,
            impact_metrics=impact_metrics,
            seniority_signals=seniority_signals,
        ))

    return experiences


# ---------------------------------------------------------------------------
# Education parsing
# ---------------------------------------------------------------------------

_DEGREE_RE = re.compile(
    r"(?:Bachelor|Master|Ph\.?D|Doctor|Associate|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?"
    r"|B\.?E\.?|M\.?E\.?|B\.?Tech|M\.?Tech|MBA|B\.?Sc|M\.?Sc)"
    r"(?:\s+(?:of|in))?\s+[A-Za-z\s,]+",
    re.IGNORECASE,
)


def parse_education(section_text: str) -> list[Education]:
    blocks = re.split(r"\n(?=[A-Z][^\n]{5,})", section_text)
    education_list: list[Education] = []

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue

        lines = block.split("\n")
        institution = lines[0].strip() if lines else "Unknown"
        degree_match = _DEGREE_RE.search(block)
        degree_str = degree_match.group().strip() if degree_match else ""

        degree_parts = degree_str.split(" in ", 1) if " in " in degree_str.lower() else [degree_str, ""]
        degree_name = degree_parts[0].strip() if degree_parts else degree_str
        field = degree_parts[1].strip() if len(degree_parts) > 1 else ""

        grad_date = None
        for line in lines:
            d = parse_date_str(line)
            if d:
                grad_date = d
                break

        gpa_match = re.search(r"(?:GPA|CGPA)[:\s]*(\d+\.?\d*)\s*/?\s*(\d+\.?\d*)?", block, re.IGNORECASE)
        gpa = None
        if gpa_match:
            gpa = float(gpa_match.group(1))

        honors: list[str] = []
        for h in ["summa cum laude", "magna cum laude", "cum laude", "honors", "dean's list", "distinction"]:
            if h.lower() in block.lower():
                honors.append(h.title())

        if not degree_name and not institution:
            continue

        education_list.append(Education(
            institution=institution,
            degree=degree_name or "Degree",
            field=field,
            graduation_date=grad_date,
            gpa=gpa,
            honors=honors,
            relevant_courses=[],
        ))

    return education_list


# ---------------------------------------------------------------------------
# Skills parsing
# ---------------------------------------------------------------------------

_SKILLS_DELIMITERS = re.compile(r"[,|;•●\n]+")


def _clean_skill(s: str) -> str:
    return s.strip().strip("-").strip("•").strip()


def parse_skills(section_text: str) -> dict[str, list[str]]:
    skills: dict[str, list[str]] = {}
    current_category = "general"

    for line in section_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Strip leading bullet markers
        line = re.sub(r"^[-•●*▪▸]\s*", "", line)

        if ":" in line:
            parts = line.split(":", 1)
            category = parts[0].strip().lower()
            items = [_clean_skill(s) for s in _SKILLS_DELIMITERS.split(parts[1]) if _clean_skill(s) and 2 <= len(_clean_skill(s)) <= 50]
            if items:
                skills[category] = items
        else:
            items = [_clean_skill(s) for s in _SKILLS_DELIMITERS.split(line) if _clean_skill(s) and 2 <= len(_clean_skill(s)) <= 50]
            if items:
                skills.setdefault(current_category, []).extend(items)

    return skills


# ---------------------------------------------------------------------------
# Projects parsing
# ---------------------------------------------------------------------------

def parse_projects(section_text: str) -> list[Project]:
    blocks = re.split(r"\n(?=[A-Z])", section_text)
    projects: list[Project] = []

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 15:
            continue

        lines = block.split("\n")
        name = lines[0].strip()
        desc_lines = [
            l.strip().lstrip("-•*● ") for l in lines[1:] if l.strip()
        ]
        description = " ".join(desc_lines)
        technologies = _extract_technologies(description)

        url_match = _URL_RE.search(block)
        url = url_match.group() if url_match else None
        github = None
        if url and "github.com" in url:
            github = url
            url = None

        projects.append(Project(
            name=name,
            description=description,
            technologies=technologies,
            url=url,
            github_url=github,
        ))

    return projects


# ---------------------------------------------------------------------------
# Seniority inference
# ---------------------------------------------------------------------------

def infer_seniority(total_yoe: float, signals: list[str]) -> str:
    leadership_count = len(signals)
    if total_yoe >= 15 or leadership_count >= 8:
        return "executive"
    if total_yoe >= 10 or leadership_count >= 6:
        return "staff_principal"
    if total_yoe >= 6 or leadership_count >= 3:
        return "senior"
    if total_yoe >= 2:
        return "mid"
    if total_yoe >= 0.5:
        return "junior"
    return "intern"


def compute_total_yoe(experiences: list[WorkExperience]) -> float:
    if not experiences:
        return 0.0
    total_months = 0
    for exp in experiences:
        end = exp.end_date or date.today()
        delta = (end.year - exp.start_date.year) * 12 + (end.month - exp.start_date.month)
        total_months += max(delta, 0)
    return round(total_months / 12, 1)


def infer_primary_domain(experiences: list[WorkExperience], skills: dict[str, list[str]]) -> str:
    all_tech = []
    for exp in experiences:
        all_tech.extend(t.lower() for t in exp.technologies)
    for skill_list in skills.values():
        all_tech.extend(s.lower() for s in skill_list)

    domain_signals = {
        "frontend": ["react", "vue", "angular", "css", "html", "svelte", "next.js", "tailwind"],
        "backend": ["django", "flask", "fastapi", "spring", "express", "node.js", "rails", "graphql", "grpc"],
        "ml": ["tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "ml", "deep learning", "nlp"],
        "devops": ["docker", "kubernetes", "terraform", "jenkins", "ci/cd", "aws", "gcp", "azure"],
        "mobile": ["swift", "kotlin", "react native", "flutter", "ios", "android"],
        "data": ["sql", "spark", "hadoop", "etl", "data pipeline", "airflow", "dbt"],
    }

    scores: dict[str, int] = {}
    for domain, keywords in domain_signals.items():
        scores[domain] = sum(1 for t in all_tech if t in keywords)

    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_resume(file_path: str | Path, user_id: str = "") -> Resume:
    raw_text = extract_text(file_path)
    sections = split_sections(raw_text)

    preamble = sections.get("preamble", raw_text[:500])
    contact = extract_contact(preamble)

    summary = None
    for key in ("summary", "professional summary", "objective", "profile", "about"):
        if key in sections:
            summary = sections[key]
            break

    exp_text = ""
    for key in ("experience", "work experience", "professional experience", "employment"):
        if key in sections:
            exp_text = sections[key]
            break
    work_experience = parse_work_experience(exp_text) if exp_text else []

    edu_text = ""
    for key in ("education", "academic"):
        if key in sections:
            edu_text = sections[key]
            break
    education = parse_education(edu_text) if edu_text else []

    skills_text = ""
    for key in ("skills", "technical skills", "core competencies", "technologies"):
        if key in sections:
            skills_text = sections[key]
            break
    skills = parse_skills(skills_text) if skills_text else {}

    proj_text = ""
    for key in ("projects", "personal projects", "side projects"):
        if key in sections:
            proj_text = sections[key]
            break
    projects = parse_projects(proj_text) if proj_text else []

    total_yoe = compute_total_yoe(work_experience)
    all_seniority_signals = []
    for exp in work_experience:
        all_seniority_signals.extend(exp.seniority_signals)
    seniority_level = infer_seniority(total_yoe, all_seniority_signals)
    primary_domain = infer_primary_domain(work_experience, skills)

    publications: list[str] = []
    if "publications" in sections or "papers" in sections:
        pub_text = sections.get("publications", sections.get("papers", ""))
        publications = [l.strip() for l in pub_text.split("\n") if l.strip()]

    awards: list[str] = []
    for key in ("awards", "honors", "achievements"):
        if key in sections:
            awards = [l.strip() for l in sections[key].split("\n") if l.strip()]
            break

    spoken_languages: list[str] = []
    if "languages" in sections:
        spoken_languages = [
            l.strip() for l in re.split(r"[,;\n]", sections["languages"]) if l.strip()
        ]

    certifications: list[Certification] = []
    for key in ("certifications", "certificates", "licenses"):
        if key in sections:
            for line in sections[key].split("\n"):
                line = line.strip()
                if line:
                    certifications.append(Certification(name=line, issuer=""))
            break

    return Resume(
        user_id=user_id,
        raw_text=raw_text,
        contact=contact,
        summary=summary,
        work_experience=work_experience,
        education=education,
        skills=skills,
        projects=projects,
        certifications=certifications,
        publications=publications,
        awards=awards,
        languages=spoken_languages,
        total_yoe=total_yoe,
        seniority_level=seniority_level,
        primary_domain=primary_domain,
    )


def parse_resume_text(raw_text: str, user_id: str = "") -> Resume:
    """Parse a resume from raw text (no file I/O)."""
    sections = split_sections(raw_text)

    preamble = sections.get("preamble", raw_text[:500])
    contact = extract_contact(preamble)

    summary = None
    for key in ("summary", "professional summary", "objective", "profile", "about"):
        if key in sections:
            summary = sections[key]
            break

    exp_text = ""
    for key in ("experience", "work experience", "professional experience", "employment"):
        if key in sections:
            exp_text = sections[key]
            break
    work_experience = parse_work_experience(exp_text) if exp_text else []

    edu_text = ""
    for key in ("education", "academic"):
        if key in sections:
            edu_text = sections[key]
            break
    education = parse_education(edu_text) if edu_text else []

    skills_text = ""
    for key in ("skills", "technical skills", "core competencies", "technologies"):
        if key in sections:
            skills_text = sections[key]
            break
    skills = parse_skills(skills_text) if skills_text else {}

    proj_text = ""
    for key in ("projects", "personal projects", "side projects"):
        if key in sections:
            proj_text = sections[key]
            break
    projects = parse_projects(proj_text) if proj_text else []

    total_yoe = compute_total_yoe(work_experience)
    all_seniority_signals = []
    for exp in work_experience:
        all_seniority_signals.extend(exp.seniority_signals)
    seniority_level = infer_seniority(total_yoe, all_seniority_signals)
    primary_domain = infer_primary_domain(work_experience, skills)

    return Resume(
        user_id=user_id,
        raw_text=raw_text,
        contact=contact,
        summary=summary,
        work_experience=work_experience,
        education=education,
        skills=skills,
        projects=projects,
        total_yoe=total_yoe,
        seniority_level=seniority_level,
        primary_domain=primary_domain,
    )
