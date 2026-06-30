"""Unit tests for the resume parser against sample fixtures."""

from pathlib import Path

import pytest

from backend.parsers.resume_parser import (
    compute_total_yoe,
    extract_contact,
    extract_text,
    infer_primary_domain,
    infer_seniority,
    parse_education,
    parse_resume,
    parse_skills,
    parse_work_experience,
    split_sections,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_resumes"


class TestExtractText:
    def test_reads_txt_file(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        assert "Alex Chen" in text
        assert "Google" in text

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            extract_text(Path("fake.xyz"))


class TestSplitSections:
    def test_finds_standard_sections(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        sections = split_sections(text)
        assert "experience" in sections or "work experience" in sections
        assert "education" in sections
        assert "skills" in sections

    def test_returns_full_text_for_no_headers(self):
        sections = split_sections("Just a plain block of text with no headers.")
        assert "full_text" in sections


class TestExtractContact:
    def test_senior_backend_contact(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        contact = extract_contact(text[:500])
        assert contact.email == "alex.chen@email.com"
        assert contact.phone is not None
        assert "linkedin.com" in (contact.linkedin or "")
        assert "github.com" in (contact.github or "")

    def test_junior_frontend_contact(self):
        text = extract_text(FIXTURES / "junior_frontend.txt")
        contact = extract_contact(text[:500])
        assert contact.email == "sarah.kim@gmail.com"
        assert "github.com" in (contact.github or "")


class TestParseWorkExperience:
    def test_senior_backend_has_experiences(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        sections = split_sections(text)
        exp_text = sections.get("experience", "")
        experiences = parse_work_experience(exp_text)
        assert len(experiences) >= 1

    def test_bullets_extracted(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        sections = split_sections(text)
        exp_text = sections.get("experience", "")
        experiences = parse_work_experience(exp_text)
        total_bullets = sum(len(e.bullets) for e in experiences)
        assert total_bullets >= 3

    def test_technologies_extracted(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        sections = split_sections(text)
        exp_text = sections.get("experience", "")
        experiences = parse_work_experience(exp_text)
        all_tech = []
        for e in experiences:
            all_tech.extend(e.technologies)
        assert len(all_tech) >= 1


class TestParseEducation:
    def test_senior_backend_education(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        sections = split_sections(text)
        edu_text = sections.get("education", "")
        education = parse_education(edu_text)
        assert len(education) >= 1


class TestParseSkills:
    def test_skills_with_categories(self):
        text = extract_text(FIXTURES / "senior_backend.txt")
        sections = split_sections(text)
        skills_text = sections.get("skills", "")
        skills = parse_skills(skills_text)
        assert len(skills) >= 1
        total_skills = sum(len(v) for v in skills.values())
        assert total_skills >= 3


class TestSeniorityInference:
    def test_senior_with_many_signals(self):
        signals = ["led", "architected", "spearheaded", "mentored"]
        assert infer_seniority(8.0, signals) == "senior"

    def test_junior_with_low_yoe(self):
        assert infer_seniority(1.5, []) == "junior"

    def test_intern_with_minimal_yoe(self):
        assert infer_seniority(0.3, []) == "intern"

    def test_executive_with_high_signals(self):
        signals = ["led", "directed", "oversaw", "managed", "drove", "defined", "scaled", "established"]
        assert infer_seniority(16.0, signals) == "executive"


class TestPrimaryDomain:
    def test_infers_backend(self):
        from backend.parsers.schemas import WorkExperience
        from datetime import date

        exp = WorkExperience(
            company="X", title="Y",
            start_date=date(2020, 1, 1),
            technologies=["Django", "FastAPI", "PostgreSQL"],
            bullets=[],
        )
        domain = infer_primary_domain([exp], {})
        assert domain == "backend"


class TestFullParse:
    def test_senior_backend_e2e(self):
        resume = parse_resume(FIXTURES / "senior_backend.txt")
        assert resume.contact.name != "Unknown"
        assert resume.contact.email == "alex.chen@email.com"
        assert resume.total_yoe > 0
        assert resume.seniority_level in ("senior", "staff_principal")
        assert len(resume.work_experience) >= 1
        assert len(resume.education) >= 1
        assert len(resume.skills) >= 1

    def test_junior_frontend_e2e(self):
        resume = parse_resume(FIXTURES / "junior_frontend.txt")
        assert resume.contact.email == "sarah.kim@gmail.com"
        assert resume.seniority_level in ("intern", "junior")
        assert len(resume.projects) >= 1

    def test_career_changer_pm_e2e(self):
        resume = parse_resume(FIXTURES / "career_changer_pm.txt")
        assert resume.contact.email == "michael.torres@email.com"
        assert resume.total_yoe > 0
        assert len(resume.education) >= 1
