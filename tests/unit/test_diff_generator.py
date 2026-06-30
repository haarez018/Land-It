"""Unit tests for the diff generator."""

import copy
from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    Resume,
    ResumeContact,
    WorkExperience,
)
from backend.agents.tailor.diff_generator import (
    generate_diff,
    _format_resume_text,
    ResumeDiff,
)
from backend.agents.tailor.resume_rewriter import RewriteChange


def _contact():
    return ResumeContact(name="Alex Chen", email="alex@example.com")


def _resume():
    return Resume(
        contact=_contact(),
        raw_text="test",
        summary="Original summary.",
        work_experience=[
            WorkExperience(
                company="Acme",
                title="Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Built APIs using Python",
                    "Managed databases",
                    "Helped with testing",
                ],
                technologies=["Python"],
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
        skills={"languages": ["Python"]},
    )


class TestFormatResumeText:
    def test_includes_contact(self):
        text = _format_resume_text(_resume())
        assert "Alex Chen" in text
        assert "alex@example.com" in text

    def test_includes_summary(self):
        text = _format_resume_text(_resume())
        assert "SUMMARY" in text
        assert "Original summary" in text

    def test_includes_experience(self):
        text = _format_resume_text(_resume())
        assert "EXPERIENCE" in text
        assert "Built APIs" in text

    def test_includes_education(self):
        text = _format_resume_text(_resume())
        assert "EDUCATION" in text
        assert "MIT" in text


class TestGenerateDiff:
    def test_no_changes_produces_empty_diff(self):
        original = _resume()
        rewritten = copy.deepcopy(original)
        diff = generate_diff(original, rewritten, [])
        assert diff.total_changes == 0

    def test_summary_change_detected(self):
        original = _resume()
        rewritten = copy.deepcopy(original)
        rewritten.summary = "New improved summary targeting this role."
        changes = [
            RewriteChange(
                section="Summary",
                original="Original summary.",
                rewritten="New improved summary targeting this role.",
                reason="test",
                dimension_improved=["voice_alignment"],
            )
        ]
        diff = generate_diff(original, rewritten, changes)
        assert diff.total_changes >= 1
        summary_diffs = [s for s in diff.section_diffs if s.section_name == "Summary"]
        assert len(summary_diffs) == 1
        assert summary_diffs[0].has_changes is True

    def test_bullet_change_detected(self):
        original = _resume()
        rewritten = copy.deepcopy(original)
        rewritten.work_experience[0].bullets[2] = "Facilitated testing infrastructure"
        changes = [
            RewriteChange(
                section="Work Experience / Acme / Bullet 3",
                original="Helped with testing",
                rewritten="Facilitated testing infrastructure",
                reason="verb upgrade",
                dimension_improved=["action_verb_strength"],
            )
        ]
        diff = generate_diff(original, rewritten, changes)

        exp_diffs = [s for s in diff.section_diffs if "Acme" in s.section_name]
        assert len(exp_diffs) == 1
        assert exp_diffs[0].has_changes is True
        changed_bullets = [b for b in exp_diffs[0].bullet_diffs if b.diff_type == "changed"]
        assert len(changed_bullets) >= 1

    def test_unified_diff_format(self):
        original = _resume()
        rewritten = copy.deepcopy(original)
        rewritten.summary = "New summary"
        diff = generate_diff(original, rewritten, [])
        assert isinstance(diff.unified_diff, str)
        # Unified diff should have +/- lines
        if diff.unified_diff:
            assert "---" in diff.unified_diff or "+++" in diff.unified_diff

    def test_score_passthrough(self):
        original = _resume()
        rewritten = copy.deepcopy(original)
        diff = generate_diff(original, rewritten, [], score_before=55.0, score_after=72.0)
        assert diff.score_before == 55.0
        assert diff.score_after == 72.0

    def test_skills_change_detected(self):
        original = _resume()
        rewritten = copy.deepcopy(original)
        rewritten.skills["additional"] = ["Go", "Kafka"]
        changes = [
            RewriteChange(
                section="Skills / Additional",
                original="(not present)",
                rewritten="Go",
                reason="keyword injection",
                dimension_improved=["keyword_density"],
            )
        ]
        diff = generate_diff(original, rewritten, changes)
        skills_diffs = [s for s in diff.section_diffs if s.section_name == "Skills"]
        assert len(skills_diffs) == 1
        assert skills_diffs[0].has_changes is True
