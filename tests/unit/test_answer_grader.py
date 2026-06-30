"""Tests for the interview answer grader."""

import pytest

from backend.agents.coach.answer_grader import (
    AnswerGrade,
    DimensionGrade,
    grade_answer,
    _score_structure,
    _score_specificity,
    _score_relevance,
    _score_impact,
    _score_communication,
    _check_red_flags,
)
from backend.agents.coach.question_generator import InterviewQuestion


def _question(**overrides) -> InterviewQuestion:
    defaults = dict(
        id="q_01",
        text="Tell me about a time you had to make a technical decision with incomplete information.",
        category="behavioral",
        difficulty="medium",
        what_good_looks_like="Uses STAR format, names a specific situation, explains trade-off analysis.",
        follow_ups=["What would you do differently?"],
        red_flags=["Vague answers with no specific example", "Blames others for the uncertainty"],
        targeting=["technical decision", "incomplete information"],
    )
    defaults.update(overrides)
    return InterviewQuestion(**defaults)


# Strong STAR-formatted answer with metrics
STRONG_ANSWER = (
    "At Google in 2023, our team of 6 engineers faced a critical decision about migrating "
    "our payment processing system from a monolith to microservices. My role was to evaluate "
    "the architectural options and present a recommendation to the VP of Engineering. "
    "I built a proof-of-concept using Kubernetes and gRPC, benchmarked the performance against "
    "our existing system, and created a migration plan with rollback strategies. I chose a "
    "strangler fig pattern to reduce risk. As a result, we reduced latency by 40%, improved "
    "uptime from 99.9% to 99.99%, and saved $150K annually in infrastructure costs. The "
    "migration was completed in 3 months with zero downtime."
)

# Weak vague answer
WEAK_ANSWER = "Yeah so basically I had to make some decisions at work. We like talked about it and stuff and decided to go with the thing that seemed best. It worked out fine I think."

# Medium answer — some structure, some specifics, but missing impact
MEDIUM_ANSWER = (
    "In my previous role, we needed to decide between PostgreSQL and MongoDB for a new service. "
    "I researched both options, considering our team's expertise, the data model requirements, "
    "and the query patterns we expected. I created a comparison document and presented it to the "
    "team. We went with PostgreSQL because our data was highly relational. The project launched "
    "on time and the database has been stable."
)


class TestScoreStructure:
    """Tests for STAR structure scoring."""

    def test_strong_star_answer_scores_high(self):
        score, feedback = _score_structure(STRONG_ANSWER)
        assert score >= 18

    def test_weak_answer_scores_low(self):
        score, feedback = _score_structure(WEAK_ANSWER)
        assert score <= 10

    def test_medium_answer_scores_mid(self):
        score, feedback = _score_structure(MEDIUM_ANSWER)
        assert 10 <= score <= 22

    def test_feedback_is_string(self):
        _, feedback = _score_structure(STRONG_ANSWER)
        assert isinstance(feedback, str)
        assert len(feedback) > 0

    def test_score_bounded(self):
        score, _ = _score_structure(STRONG_ANSWER)
        assert 0 <= score <= 25
        score2, _ = _score_structure(WEAK_ANSWER)
        assert 0 <= score2 <= 25


class TestScoreSpecificity:
    """Tests for specificity scoring."""

    def test_specific_answer_scores_high(self):
        score, _ = _score_specificity(STRONG_ANSWER)
        assert score >= 18

    def test_vague_answer_scores_low(self):
        score, _ = _score_specificity(WEAK_ANSWER)
        assert score <= 12

    def test_mentions_metrics_help(self):
        with_metrics = "We reduced latency by 40% and saved $150K. The team of 12 delivered in 3 months."
        without_metrics = "We made the system faster and saved money. The team delivered the project."
        score_with, _ = _score_specificity(with_metrics)
        score_without, _ = _score_specificity(without_metrics)
        assert score_with > score_without

    def test_score_bounded(self):
        score, _ = _score_specificity(STRONG_ANSWER)
        assert 0 <= score <= 25


class TestScoreRelevance:
    """Tests for relevance scoring."""

    def test_relevant_answer_scores_high(self):
        q = _question(targeting=["technical decision", "incomplete information"])
        score, _ = _score_relevance(
            "I had to make a critical technical decision about our architecture "
            "when we had incomplete information about the load requirements.",
            q,
        )
        assert score >= 15

    def test_irrelevant_answer_scores_low(self):
        q = _question(
            text="How do you handle code reviews?",
            targeting=["code review"],
        )
        score, _ = _score_relevance(
            "I love cooking pasta on weekends. My favorite recipe uses fresh basil.",
            q,
        )
        assert score <= 10

    def test_score_bounded(self):
        q = _question()
        score, _ = _score_relevance(STRONG_ANSWER, q)
        assert 0 <= score <= 25


class TestScoreImpact:
    """Tests for impact scoring."""

    def test_metrics_heavy_answer_scores_high(self):
        score, _ = _score_impact(
            "Reduced latency by 40%, saved $150K annually, improved uptime to 99.99%, "
            "and delivered the project 2 weeks ahead of schedule."
        )
        assert score >= 10

    def test_no_metrics_scores_low(self):
        score, _ = _score_impact("We did the thing and it was good.")
        assert score <= 6

    def test_impact_language_helps(self):
        score, _ = _score_impact(
            "This resulted in significant improvements. We saved time and reduced costs. "
            "The outcome was very positive and the team achieved its goals."
        )
        assert score >= 5

    def test_score_bounded(self):
        score, _ = _score_impact(STRONG_ANSWER)
        assert 0 <= score <= 15


class TestScoreCommunication:
    """Tests for communication scoring."""

    def test_good_length_scores_well(self):
        # 200 words, no filler
        answer = " ".join(["This is a clear sentence about my experience."] * 20)
        score, _ = _score_communication(answer)
        assert score >= 5

    def test_too_short_penalized(self):
        score, _ = _score_communication("Yes I did that.")
        assert score <= 5

    def test_filler_words_penalized(self):
        fillers = "Um, like, you know, basically I um did the thing, like, honestly."
        score, _ = _score_communication(fillers)
        score_clean, _ = _score_communication("I implemented the distributed caching layer using Redis and Memcached for our production system.")
        assert score < score_clean

    def test_score_bounded(self):
        score, _ = _score_communication(STRONG_ANSWER)
        assert 0 <= score <= 10


class TestCheckRedFlags:
    """Tests for red flag detection."""

    def test_short_answer_flagged(self):
        q = _question()
        flags = _check_red_flags("yes", q)
        assert any("too short" in f.lower() for f in flags)

    def test_overuse_of_we_flagged(self):
        q = _question()
        answer = "We did this and we did that. We planned and we executed. We succeeded because we worked hard. Then we celebrated."
        flags = _check_red_flags(answer, q)
        assert any("we" in f.lower() for f in flags)

    def test_strong_answer_no_generic_flags(self):
        q = _question(red_flags=[])
        flags = _check_red_flags(STRONG_ANSWER, q)
        # Should not trigger the short or we-overuse flags
        assert not any("too short" in f.lower() for f in flags)
        assert not any("overuse" in f.lower() for f in flags)


class TestGradeAnswer:
    """Tests for the full grade_answer function."""

    def test_returns_answer_grade(self):
        grade = grade_answer(_question(), STRONG_ANSWER)
        assert isinstance(grade, AnswerGrade)

    def test_strong_answer_high_overall(self):
        grade = grade_answer(_question(), STRONG_ANSWER)
        assert grade.overall_score >= 60

    def test_weak_answer_low_overall(self):
        grade = grade_answer(_question(), WEAK_ANSWER)
        assert grade.overall_score < 50

    def test_strong_beats_weak(self):
        strong_grade = grade_answer(_question(), STRONG_ANSWER)
        weak_grade = grade_answer(_question(), WEAK_ANSWER)
        assert strong_grade.overall_score > weak_grade.overall_score

    def test_has_5_dimensions(self):
        grade = grade_answer(_question(), STRONG_ANSWER)
        assert len(grade.dimensions) == 5

    def test_dimension_names(self):
        grade = grade_answer(_question(), STRONG_ANSWER)
        names = {d.name for d in grade.dimensions}
        assert "Structure (STAR)" in names
        assert "Specificity" in names
        assert "Relevance" in names
        assert "Impact" in names
        assert "Communication" in names

    def test_overall_is_sum_of_dimensions(self):
        grade = grade_answer(_question(), MEDIUM_ANSWER)
        dim_sum = sum(d.score for d in grade.dimensions)
        assert grade.overall_score == dim_sum

    def test_max_score_is_100(self):
        grade = grade_answer(_question(), STRONG_ANSWER)
        assert grade.max_score == 100
        dim_max_sum = sum(d.max_score for d in grade.dimensions)
        assert dim_max_sum == 100

    def test_has_strengths_and_improvements(self):
        grade = grade_answer(_question(), MEDIUM_ANSWER)
        assert len(grade.strengths) >= 1
        assert len(grade.improvements) >= 1

    def test_model_answer_from_question(self):
        q = _question(what_good_looks_like="Explain the tradeoff clearly.")
        grade = grade_answer(q, MEDIUM_ANSWER)
        assert grade.model_answer == "Explain the tradeoff clearly."

    def test_question_id_preserved(self):
        q = _question(id="q_07")
        grade = grade_answer(q, MEDIUM_ANSWER)
        assert grade.question_id == "q_07"
