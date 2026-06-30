"""Unit tests for the weightage engine: role profiles, seniority matrix, normalization."""

import pytest

from backend.agents.tailor.weightage.role_profiles import ROLE_PROFILES, get_role_profile
from backend.agents.tailor.weightage.seniority_matrix import (
    SENIORITY_MULTIPLIERS,
    apply_seniority_adjustment,
)


class TestRoleProfiles:
    @pytest.mark.parametrize("role", list(ROLE_PROFILES.keys()))
    def test_weights_sum_to_one(self, role):
        weights = ROLE_PROFILES[role]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"{role} weights sum to {total}"

    @pytest.mark.parametrize("role", list(ROLE_PROFILES.keys()))
    def test_all_14_dimensions_present(self, role):
        weights = ROLE_PROFILES[role]
        assert len(weights) == 14, f"{role} has {len(weights)} dimensions, expected 14"

    def test_generic_fallback(self):
        profile = get_role_profile("nonexistent_role")
        assert len(profile) == 14
        total = sum(profile.values())
        assert abs(total - 1.0) < 0.01

    def test_known_role_returns_correct_profile(self):
        profile = get_role_profile("software_engineer_backend")
        assert profile["tech_stack_alignment"] == 0.15


class TestSeniorityMatrix:
    @pytest.mark.parametrize("seniority", list(SENIORITY_MULTIPLIERS.keys()))
    def test_all_14_multipliers_present(self, seniority):
        multipliers = SENIORITY_MULTIPLIERS[seniority]
        assert len(multipliers) == 14

    @pytest.mark.parametrize("seniority", list(SENIORITY_MULTIPLIERS.keys()))
    def test_adjusted_weights_sum_to_one(self, seniority):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, seniority)
        total = sum(adjusted.values())
        assert abs(total - 1.0) < 0.001, f"{seniority} adjusted weights sum to {total}"

    def test_mid_level_is_identity(self):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "mid")
        for k in base:
            assert abs(base[k] - adjusted[k]) < 0.001

    def test_intern_boosts_education(self):
        base = get_role_profile("software_engineer_backend")
        adjusted_intern = apply_seniority_adjustment(base, "intern")
        adjusted_senior = apply_seniority_adjustment(base, "senior")
        assert adjusted_intern["education_relevance"] > adjusted_senior["education_relevance"]

    def test_senior_boosts_impact(self):
        base = get_role_profile("product_manager")
        adjusted = apply_seniority_adjustment(base, "senior")
        base_mid = apply_seniority_adjustment(base, "mid")
        assert adjusted["quantified_impact"] > base_mid["quantified_impact"]

    def test_executive_heavily_weights_impact(self):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "executive")
        # quantified_impact should be one of the heaviest dimensions
        top_3 = sorted(adjusted.items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_keys = [k for k, v in top_3]
        assert "quantified_impact" in top_3_keys


class TestCrossRoleSeniority:
    """Ensure all role x seniority combinations produce valid normalized weights."""

    @pytest.mark.parametrize("role", list(ROLE_PROFILES.keys()))
    @pytest.mark.parametrize("seniority", list(SENIORITY_MULTIPLIERS.keys()))
    def test_all_combinations_normalize(self, role, seniority):
        base = get_role_profile(role)
        adjusted = apply_seniority_adjustment(base, seniority)
        total = sum(adjusted.values())
        assert abs(total - 1.0) < 0.001
        assert all(v >= 0 for v in adjusted.values())
