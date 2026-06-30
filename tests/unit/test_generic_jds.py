"""Unit tests for generic JD templates."""

from __future__ import annotations

import pytest

from backend.agents.tailor.generic_jds import (
    get_generic_jd,
    list_available_templates,
    _TEMPLATES,
)
from backend.parsers.schemas import JobDescription


class TestTemplateRegistry:
    def test_at_least_12_templates(self):
        templates = list_available_templates()
        assert len(templates) >= 12

    @pytest.mark.parametrize("key", list(_TEMPLATES.keys()))
    def test_each_template_has_required_fields(self, key):
        t = _TEMPLATES[key]
        assert "title" in t
        assert "raw_text" in t
        assert "required_skills" in t
        assert "tech_stack" in t
        assert "requirements" in t

    @pytest.mark.parametrize("key", list(_TEMPLATES.keys()))
    def test_raw_text_not_empty(self, key):
        t = _TEMPLATES[key]
        assert len(t["raw_text"]) >= 100

    @pytest.mark.parametrize("key", list(_TEMPLATES.keys()))
    def test_has_at_least_3_requirements(self, key):
        t = _TEMPLATES[key]
        assert len(t["requirements"]) >= 3

    @pytest.mark.parametrize("key", list(_TEMPLATES.keys()))
    def test_has_required_skills(self, key):
        t = _TEMPLATES[key]
        assert len(t["required_skills"]) >= 2

    @pytest.mark.parametrize("key", list(_TEMPLATES.keys()))
    def test_has_tech_stack(self, key):
        t = _TEMPLATES[key]
        assert len(t["tech_stack"]) >= 3


class TestGetGenericJD:
    @pytest.mark.parametrize("key", list(_TEMPLATES.keys()))
    def test_returns_valid_jd(self, key):
        role_type, seniority = key
        jd = get_generic_jd(role_type, seniority)
        assert isinstance(jd, JobDescription)
        assert jd.title
        assert len(jd.required_skills) >= 2
        assert len(jd.tech_stack) >= 3
        assert len(jd.requirements) >= 3
        assert jd.raw_text

    def test_fallback_to_mid(self):
        # "junior" doesn't exist for most roles, should fall back to "mid"
        jd = get_generic_jd("software_engineer_backend", "junior")
        assert isinstance(jd, JobDescription)
        assert jd.title

    def test_fallback_to_backend_mid(self):
        jd = get_generic_jd("nonexistent_role", "nonexistent_seniority")
        assert isinstance(jd, JobDescription)
        assert jd.title

    def test_all_role_types_have_mid(self):
        role_types = {k[0] for k in _TEMPLATES.keys()}
        for role in role_types:
            jd = get_generic_jd(role, "mid")
            assert jd.title

    def test_all_role_types_have_senior(self):
        role_types = {k[0] for k in _TEMPLATES.keys()}
        for role in role_types:
            jd = get_generic_jd(role, "senior")
            assert jd.title

    def test_company_is_generic(self):
        jd = get_generic_jd("software_engineer_backend", "senior")
        assert jd.company == "Generic Company"
