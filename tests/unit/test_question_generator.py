"""Tests for the interview question generator."""

import pytest

from backend.agents.coach.question_generator import (
    InterviewQuestion,
    generate_questions,
    _generate_tech_stack_questions,
    _generate_requirement_questions,
    _generate_seniority_questions,
    _generate_company_culture_questions,
)
from backend.parsers.schemas import JobDescription, JDRequirement


def _jd(**overrides) -> JobDescription:
    """Create a test JD with sensible defaults."""
    defaults = dict(
        title="Senior Software Engineer",
        company="Acme Corp",
        seniority_level="senior",
        required_skills=["Python", "Go", "PostgreSQL"],
        preferred_skills=["Kubernetes", "Redis"],
        tech_stack=["Python", "Go", "PostgreSQL", "Docker", "Kubernetes"],
        requirements=[
            JDRequirement(
                text="5+ years of backend development experience",
                category="must_have",
                skill_type="technical",
                extracted_keyword="backend development",
            ),
            JDRequirement(
                text="Strong communication and collaboration skills",
                category="must_have",
                skill_type="soft",
                extracted_keyword="communication",
            ),
            JDRequirement(
                text="Experience with distributed systems",
                category="must_have",
                skill_type="technical",
                extracted_keyword="distributed systems",
            ),
        ],
        company_values=["Move fast", "Think big", "Be transparent"],
        role_priorities=["Build scalable backend services"],
        soft_skills=["collaboration", "communication"],
    )
    defaults.update(overrides)
    return JobDescription(**defaults)


class TestGenerateQuestions:
    """Tests for the main generate_questions function."""

    def test_generates_correct_count(self):
        questions = generate_questions(_jd(), count=10, seed=42)
        assert len(questions) == 10

    def test_generates_fewer_if_count_small(self):
        questions = generate_questions(_jd(), count=5, seed=42)
        assert len(questions) == 5

    def test_all_questions_are_interview_questions(self):
        questions = generate_questions(_jd(), count=8, seed=42)
        for q in questions:
            assert isinstance(q, InterviewQuestion)

    def test_questions_have_required_fields(self):
        questions = generate_questions(_jd(), count=8, seed=42)
        for q in questions:
            assert q.id
            assert q.text
            assert q.category in ("behavioral", "technical", "situational", "system_design", "culture_fit")
            assert q.difficulty in ("easy", "medium", "hard")
            assert q.what_good_looks_like

    def test_covers_multiple_categories(self):
        questions = generate_questions(_jd(), count=10, seed=42)
        categories = {q.category for q in questions}
        # Should have at least 3 different categories
        assert len(categories) >= 3

    def test_seed_produces_reproducible_results(self):
        q1 = generate_questions(_jd(), count=10, seed=123)
        q2 = generate_questions(_jd(), count=10, seed=123)
        assert [q.text for q in q1] == [q.text for q in q2]

    def test_different_seeds_produce_different_results(self):
        # Use a minimal JD so generic templates fill most slots
        minimal = JobDescription(
            title="Engineer",
            company="Co",
            seniority_level="mid",
            tech_stack=[],
            requirements=[],
            company_values=[],
        )
        q1 = generate_questions(minimal, count=10, seed=1)
        q2 = generate_questions(minimal, count=10, seed=2)
        texts1 = [q.text for q in q1]
        texts2 = [q.text for q in q2]
        # At least some should differ (templates are shuffled differently)
        assert texts1 != texts2

    def test_questions_sorted_by_category_then_difficulty(self):
        questions = generate_questions(_jd(), count=10, seed=42)
        cat_order = {"behavioral": 0, "technical": 1, "situational": 2, "system_design": 3, "culture_fit": 4}
        diff_order = {"easy": 0, "medium": 1, "hard": 2}

        for i in range(1, len(questions)):
            prev = (cat_order.get(questions[i-1].category, 9), diff_order.get(questions[i-1].difficulty, 1))
            curr = (cat_order.get(questions[i].category, 9), diff_order.get(questions[i].difficulty, 1))
            assert prev <= curr, f"Questions not sorted: {questions[i-1].category}/{questions[i-1].difficulty} > {questions[i].category}/{questions[i].difficulty}"

    def test_no_duplicate_questions(self):
        questions = generate_questions(_jd(), count=10, seed=42)
        texts = [q.text for q in questions]
        assert len(texts) == len(set(texts))


class TestTechStackQuestions:
    """Tests for tech-stack-specific question generation."""

    def test_generates_questions_for_tech_stack(self):
        jd = _jd(tech_stack=["Python", "Go", "PostgreSQL"])
        questions = _generate_tech_stack_questions(jd)
        assert len(questions) == 3

    def test_question_mentions_tech(self):
        jd = _jd(tech_stack=["Kubernetes"])
        questions = _generate_tech_stack_questions(jd)
        assert "Kubernetes" in questions[0]["text"]

    def test_empty_tech_stack_generates_no_questions(self):
        jd = _jd(tech_stack=[])
        questions = _generate_tech_stack_questions(jd)
        assert len(questions) == 0

    def test_limits_to_3_techs(self):
        jd = _jd(tech_stack=["A", "B", "C", "D", "E"])
        questions = _generate_tech_stack_questions(jd)
        assert len(questions) == 3


class TestRequirementQuestions:
    """Tests for JD requirement-based questions."""

    def test_generates_from_requirements(self):
        jd = _jd()
        questions = _generate_requirement_questions(jd)
        assert len(questions) >= 1

    def test_technical_requirement_question(self):
        jd = _jd(requirements=[
            JDRequirement(
                text="Experience with microservices architecture",
                category="must_have",
                skill_type="technical",
                extracted_keyword="microservices",
            ),
        ])
        questions = _generate_requirement_questions(jd)
        assert len(questions) == 1
        assert questions[0]["category"] == "technical"
        assert "microservices" in questions[0]["text"].lower()

    def test_soft_skill_requirement_question(self):
        jd = _jd(requirements=[
            JDRequirement(
                text="Excellent leadership skills",
                category="must_have",
                skill_type="soft",
                extracted_keyword="leadership",
            ),
        ])
        questions = _generate_requirement_questions(jd)
        assert len(questions) == 1
        assert questions[0]["category"] == "behavioral"


class TestSeniorityQuestions:
    """Tests for seniority-calibrated questions."""

    def test_senior_gets_strategy_questions(self):
        jd = _jd(seniority_level="senior")
        questions = _generate_seniority_questions(jd)
        assert len(questions) >= 1
        assert any("strategy" in q["text"].lower() or "code review" in q["text"].lower() for q in questions)

    def test_junior_gets_workflow_questions(self):
        jd = _jd(seniority_level="junior")
        questions = _generate_seniority_questions(jd)
        assert len(questions) >= 1
        assert any("workflow" in q["text"].lower() for q in questions)


class TestCompanyCultureQuestions:
    """Tests for company values questions."""

    def test_generates_culture_question(self):
        jd = _jd(company="Google", company_values=["Innovation first"])
        questions = _generate_company_culture_questions(jd)
        assert len(questions) == 1
        assert "Google" in questions[0]["text"]
        assert "Innovation first" in questions[0]["text"]

    def test_no_values_no_questions(self):
        jd = _jd(company_values=[])
        questions = _generate_company_culture_questions(jd)
        assert len(questions) == 0
