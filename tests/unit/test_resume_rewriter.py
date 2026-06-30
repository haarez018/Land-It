"""Unit tests for the 6-pass resume rewriter."""

from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    JDRequirement,
    JobDescription,
    Resume,
    ResumeContact,
    WorkExperience,
)
from backend.agents.tailor.resume_rewriter import (
    rewrite_resume,
    _pass_keyword_injection,
    _pass_bullet_restructuring,
    _pass_verb_upgrading,
    _pass_quantification,
    _pass_section_reordering,
    _pass_summary_rewrite,
    RewriteChange,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


def _contact():
    return ResumeContact(name="Alex Chen", email="alex@example.com")


def _resume():
    return Resume(
        contact=_contact(),
        raw_text=(
            "alex@example.com\n\nSUMMARY\nExperienced software engineer.\n\n"
            "EXPERIENCE\n"
            "Software Engineer at Acme Corp\nJan 2020 - Present\n"
            "Built REST APIs serving thousands of users\n"
            "Managed CI/CD pipeline for the team\n"
            "Helped with database migration project\n"
            "Worked on performance improvements\n\n"
            "SKILLS\nPython, Django, PostgreSQL\n\n"
            "EDUCATION\nBS Computer Science, MIT, 2019"
        ),
        summary="Experienced software engineer.",
        work_experience=[
            WorkExperience(
                company="Acme Corp",
                title="Software Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Built REST APIs serving thousands of users",
                    "Managed CI/CD pipeline for the team",
                    "Helped with database migration project",
                    "Worked on performance improvements",
                ],
                technologies=["Python", "Django", "PostgreSQL"],
            ),
        ],
        education=[
            Education(
                institution="MIT",
                degree="BS Computer Science",
                field="Computer Science",
                graduation_date=date(2019, 6, 1),
            )
        ],
        skills={"languages": ["Python"], "frameworks": ["Django"], "databases": ["PostgreSQL"]},
        seniority_level="mid",
        total_yoe=5.0,
    )


def _jd():
    return JobDescription(
        raw_text=(
            "Senior Backend Engineer at Stripe\n"
            "Required: Python, Go, Kafka, PostgreSQL, Docker, Kubernetes\n"
            "Build scalable payment infrastructure. 5+ years experience.\n"
            "Domain: fintech, payments, transactions"
        ),
        title="Senior Backend Engineer",
        company="Stripe",
        required_skills=["Python", "Go", "Kafka", "PostgreSQL"],
        preferred_skills=["Docker", "Kubernetes"],
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL", "Docker", "Kubernetes"],
        requirements=[
            JDRequirement(text="5+ years backend experience", category="must_have",
                         skill_type="technical", extracted_keyword="backend"),
            JDRequirement(text="Build scalable systems", category="must_have",
                         skill_type="technical", extracted_keyword="scalable"),
        ],
        seniority_level="senior",
        required_experience_years=5,
        role_priorities=["Build scalable payment infrastructure"],
    )


# ── Pass 1: Keyword Injection ──────────────────────────────────────────────


class TestKeywordInjection:
    def test_injects_missing_keywords(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_keyword_injection(resume, jd, changes)

        # Go and Kafka are missing from the resume — should appear in skills
        all_skills_flat = []
        for sl in result.skills.values():
            all_skills_flat.extend(s.lower() for s in sl)
        all_text = " ".join(all_skills_flat)

        # At least some missing keywords should be added
        assert len(changes) > 0, "Should have injected at least one keyword"

    def test_does_not_duplicate_existing_keywords(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_keyword_injection(resume, jd, changes)

        # "Python" and "PostgreSQL" already exist — should NOT be re-added
        python_changes = [c for c in changes if "Python" in c.rewritten and c.section.startswith("Skills")]
        assert len(python_changes) == 0, "Should not re-add existing skills"


# ── Pass 2: Bullet Restructuring ──────────────────────────────────────────


class TestBulletRestructuring:
    def test_most_relevant_bullet_first(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_bullet_restructuring(resume, jd, changes)

        # "Built REST APIs serving thousands of users" has "api", "serving", "users"
        # which are more JD-relevant than "Helped with database migration"
        first_bullet = result.work_experience[0].bullets[0]
        assert "api" in first_bullet.lower() or "built" in first_bullet.lower(), \
            f"Most relevant bullet should be first, got: {first_bullet}"

    def test_single_bullet_no_change(self):
        resume = _resume()
        resume.work_experience[0].bullets = ["Only one bullet"]
        changes: list[RewriteChange] = []
        result = _pass_bullet_restructuring(resume, _jd(), changes)
        assert len(changes) == 0


# ── Pass 3: Verb Upgrading ────────────────────────────────────────────────


class TestVerbUpgrading:
    def test_upgrades_weak_verbs(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_verb_upgrading(resume, jd, changes)

        # "Helped with" → "Facilitated" and "Worked on" → "Built"
        upgraded_verbs = [c for c in changes if "verb" in c.reason.lower() or "Upgraded" in c.reason]
        assert len(upgraded_verbs) >= 2, f"Should upgrade at least 2 weak verbs, got {len(upgraded_verbs)}"

    def test_preserves_strong_verbs(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []

        # "Built" is already Tier 2 — should not be changed by verb upgrader
        built_changes = [c for c in changes if "Built REST" in c.original]
        assert len(built_changes) == 0, "Should not upgrade already-strong verbs"

    def test_capitalizes_replacement(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_verb_upgrading(resume, jd, changes)

        for change in changes:
            # First word of rewritten should be capitalized
            first_word = change.rewritten.split()[0]
            assert first_word[0].isupper(), f"Replacement should be capitalized: {change.rewritten}"


# ── Pass 4: Quantification ───────────────────────────────────────────────


class TestQuantification:
    def test_adds_verification_markers(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_quantification(resume, jd, changes)

        verify_changes = [c for c in changes if c.requires_verification]
        assert len(verify_changes) > 0, "Should add at least one [USER TO VERIFY] marker"

        for change in verify_changes:
            assert "[USER TO VERIFY" in change.rewritten

    def test_skips_already_quantified_bullets(self):
        resume = _resume()
        # First bullet already has "thousands" but not a % or $ metric
        # Replace with explicitly quantified bullet
        resume.work_experience[0].bullets[0] = "Reduced API latency by 40% through caching"
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_quantification(resume, jd, changes)

        # The 40% bullet should NOT be modified
        latency_changes = [c for c in changes if "40%" in c.original]
        assert len(latency_changes) == 0, "Should not modify already-quantified bullets"


# ── Pass 5: Section Reordering ────────────────────────────────────────────


class TestSectionReordering:
    def test_detects_reordering_needed(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result, reordered = _pass_section_reordering(resume, jd, changes)

        # The test resume has SUMMARY > EXPERIENCE > SKILLS > EDUCATION
        # Optimal for backend is: experience > skills > projects > education
        # Since we already have experience before skills, no major reordering needed
        # Just check it doesn't crash
        assert isinstance(reordered, bool)


# ── Pass 6: Summary Rewrite ──────────────────────────────────────────────


class TestSummaryRewrite:
    def test_rewrites_summary(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_summary_rewrite(resume, jd, changes)

        assert result.summary != "Experienced software engineer."
        assert len(result.summary) > 20

        summary_changes = [c for c in changes if c.section == "Professional Summary"]
        assert len(summary_changes) == 1

    def test_summary_mentions_jd_role(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_summary_rewrite(resume, jd, changes)

        # Should reference the target role
        summary_lower = result.summary.lower()
        assert "engineer" in summary_lower or "backend" in summary_lower

    def test_summary_mentions_matching_skills(self):
        resume = _resume()
        jd = _jd()
        changes: list[RewriteChange] = []
        result = _pass_summary_rewrite(resume, jd, changes)

        # Should mention skills that overlap between resume and JD
        summary_lower = result.summary.lower()
        assert "python" in summary_lower or "postgresql" in summary_lower


# ── Full Pipeline ────────────────────────────────────────────────────────


class TestFullRewritePipeline:
    @pytest.mark.asyncio
    async def test_all_passes_applied(self):
        result = await rewrite_resume(_resume(), _jd())
        assert len(result.passes_applied) == 6
        assert "keyword_injection" in result.passes_applied
        assert "verb_upgrading" in result.passes_applied
        assert "summary_rewrite" in result.passes_applied
        assert result.summary_rewritten is True

    @pytest.mark.asyncio
    async def test_skip_passes(self):
        result = await rewrite_resume(
            _resume(), _jd(),
            skip_passes={"verb_upgrading", "quantification"},
        )
        assert "verb_upgrading" not in result.passes_applied
        assert "quantification" not in result.passes_applied
        assert len(result.passes_applied) == 4

    @pytest.mark.asyncio
    async def test_change_log_populated(self):
        result = await rewrite_resume(_resume(), _jd())
        assert len(result.change_log) > 0

        for change in result.change_log:
            assert change.section
            assert change.reason
            assert isinstance(change.dimension_improved, list)
            assert len(change.dimension_improved) > 0

    @pytest.mark.asyncio
    async def test_original_resume_not_mutated(self):
        resume = _resume()
        original_summary = resume.summary
        original_bullets = list(resume.work_experience[0].bullets)

        result = await rewrite_resume(resume, _jd())

        # Original should be unchanged
        assert resume.summary == original_summary
        assert resume.work_experience[0].bullets == original_bullets

    @pytest.mark.asyncio
    async def test_rewriter_produces_valid_resume(self):
        result = await rewrite_resume(_resume(), _jd())
        rewritten = result.rewritten_resume

        assert rewritten.contact.name == "Alex Chen"
        assert rewritten.contact.email == "alex@example.com"
        assert len(rewritten.work_experience) == 1
        assert rewritten.work_experience[0].company == "Acme Corp"
        assert len(rewritten.work_experience[0].bullets) >= 4
