"""Unit tests for company-specific scoring profiles."""

from __future__ import annotations

import pytest

from backend.agents.tailor.weightage.company_profiles import (
    COMPANY_PROFILES,
    CompanyProfile,
    get_company_profile,
    apply_company_profile,
    _infer_company_type,
)
from backend.agents.tailor.weightage.role_profiles import get_role_profile
from backend.agents.tailor.weightage.seniority_matrix import apply_seniority_adjustment
from backend.agents.tailor.standout.role_profiles import get_standout_role_profile
from backend.agents.tailor.standout.seniority_matrix import apply_standout_seniority_adjustment


# ── Profile registry tests ────────────────────────────────────────────────────


class TestCompanyProfileRegistry:
    def test_all_8_profiles_present(self):
        expected = {
            "google", "stripe", "netflix", "meta",
            "early_stage_startup", "faang_generic", "consulting_firm", "mid_size_tech",
        }
        assert set(COMPANY_PROFILES.keys()) == expected

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_each_profile_has_id(self, profile_id):
        assert COMPANY_PROFILES[profile_id].id == profile_id

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_each_profile_has_name(self, profile_id):
        assert len(COMPANY_PROFILES[profile_id].name) > 0

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_each_profile_has_hiring_philosophy(self, profile_id):
        assert len(COMPANY_PROFILES[profile_id].hiring_philosophy) > 20

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_each_profile_has_interview_signals(self, profile_id):
        assert len(COMPANY_PROFILES[profile_id].interview_signals) == 3

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_each_profile_has_red_flags(self, profile_id):
        assert len(COMPANY_PROFILES[profile_id].red_flags) == 2

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_ats_multipliers_positive(self, profile_id):
        for dim, mult in COMPANY_PROFILES[profile_id].ats_multipliers.items():
            assert mult > 0, f"{profile_id}.ats.{dim} = {mult}"

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_standout_multipliers_positive(self, profile_id):
        for dim, mult in COMPANY_PROFILES[profile_id].standout_multipliers.items():
            assert mult > 0, f"{profile_id}.standout.{dim} = {mult}"


# ── get_company_profile / _infer_company_type tests ───────────────────────────


class TestGetCompanyProfile:
    def test_exact_id_match(self):
        assert get_company_profile("google").id == "google"

    def test_case_insensitive(self):
        assert get_company_profile("Google").id == "google"
        assert get_company_profile("STRIPE").id == "stripe"

    def test_google_aliases(self):
        assert get_company_profile("Google LLC").id == "google"
        assert get_company_profile("Alphabet Inc").id == "google"
        assert get_company_profile("DeepMind").id == "google"

    def test_meta_aliases(self):
        assert get_company_profile("Meta Platforms").id == "meta"
        assert get_company_profile("Facebook").id == "meta"

    def test_faang_aliases(self):
        assert get_company_profile("Apple Inc").id == "faang_generic"
        assert get_company_profile("Amazon").id == "faang_generic"
        assert get_company_profile("Microsoft").id == "faang_generic"

    def test_consulting_aliases(self):
        assert get_company_profile("McKinsey & Company").id == "consulting_firm"
        assert get_company_profile("Bain & Company").id == "consulting_firm"
        assert get_company_profile("BCG").id == "consulting_firm"

    def test_unknown_company_returns_none(self):
        assert get_company_profile("Acme Corp") is None
        assert get_company_profile("Widgets Ltd") is None

    def test_empty_string_returns_none(self):
        assert get_company_profile("") is None

    def test_startup_signals(self):
        assert _infer_company_type("Acme Startup").id == "early_stage_startup"
        assert _infer_company_type("Series A Stage Company").id == "early_stage_startup"
        assert _infer_company_type("YC W24 batch").id == "early_stage_startup"

    def test_infer_unknown_returns_none(self):
        assert _infer_company_type("Random Corp") is None


# ── apply_company_profile tests ──────────────────────────────────────────────


class TestApplyCompanyProfile:
    def test_ats_weights_renormalize_to_one(self):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "mid")
        google = COMPANY_PROFILES["google"]
        final = apply_company_profile(adjusted, google, "ats")
        assert abs(sum(final.values()) - 1.0) < 0.001

    def test_standout_weights_renormalize_to_one(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, "mid")
        stripe = COMPANY_PROFILES["stripe"]
        final = apply_company_profile(adjusted, stripe, "standout")
        assert abs(sum(final.values()) - 1.0) < 0.001

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_all_profiles_renormalize_ats(self, profile_id):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "senior")
        profile = COMPANY_PROFILES[profile_id]
        final = apply_company_profile(adjusted, profile, "ats")
        assert abs(sum(final.values()) - 1.0) < 0.001
        assert all(v >= 0 for v in final.values())

    @pytest.mark.parametrize("profile_id", list(COMPANY_PROFILES.keys()))
    def test_all_profiles_renormalize_standout(self, profile_id):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, "senior")
        profile = COMPANY_PROFILES[profile_id]
        final = apply_company_profile(adjusted, profile, "standout")
        assert abs(sum(final.values()) - 1.0) < 0.001

    def test_google_boosts_spike_factor_standout(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, "mid")
        without = dict(adjusted)
        with_google = apply_company_profile(adjusted, COMPANY_PROFILES["google"], "standout")
        assert with_google["spike_factor"] > without["spike_factor"]

    def test_stripe_boosts_builder_ratio(self):
        base = get_standout_role_profile("software_engineer_backend")
        adjusted = apply_standout_seniority_adjustment(base, "mid")
        without = dict(adjusted)
        with_stripe = apply_company_profile(adjusted, COMPANY_PROFILES["stripe"], "standout")
        assert with_stripe["builder_ratio"] > without["builder_ratio"]

    def test_startup_deprioritizes_education(self):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "mid")
        without = dict(adjusted)
        with_startup = apply_company_profile(adjusted, COMPANY_PROFILES["early_stage_startup"], "ats")
        assert with_startup["education_relevance"] < without["education_relevance"]

    def test_consulting_boosts_bullet_quality(self):
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "mid")
        without = dict(adjusted)
        with_consulting = apply_company_profile(adjusted, COMPANY_PROFILES["consulting_firm"], "ats")
        assert with_consulting["bullet_quality"] > without["bullet_quality"]

    def test_missing_multiplier_key_uses_1(self):
        profile = CompanyProfile(
            id="test", name="Test", hiring_philosophy="Test profile",
            ats_multipliers={"keyword_density": 2.0},
        )
        base = get_role_profile("software_engineer_backend")
        adjusted = apply_seniority_adjustment(base, "mid")
        final = apply_company_profile(adjusted, profile, "ats")
        assert abs(sum(final.values()) - 1.0) < 0.001
        assert final["keyword_density"] > adjusted["keyword_density"]


# ── Cross-combination tests (role x seniority x company) ─────────────────────


class TestCrossCombinations:
    ROLES = ["software_engineer_backend", "product_manager", "data_scientist"]
    SENIORITIES = ["intern", "mid", "senior", "executive"]
    COMPANIES = list(COMPANY_PROFILES.keys())

    @pytest.mark.parametrize("company", COMPANIES)
    @pytest.mark.parametrize("seniority", SENIORITIES)
    @pytest.mark.parametrize("role", ROLES)
    def test_ats_triple_combination(self, role, seniority, company):
        base = get_role_profile(role)
        adjusted = apply_seniority_adjustment(base, seniority)
        final = apply_company_profile(adjusted, COMPANY_PROFILES[company], "ats")
        assert abs(sum(final.values()) - 1.0) < 0.001

    @pytest.mark.parametrize("company", COMPANIES)
    @pytest.mark.parametrize("seniority", SENIORITIES)
    @pytest.mark.parametrize("role", ROLES)
    def test_standout_triple_combination(self, role, seniority, company):
        base = get_standout_role_profile(role)
        adjusted = apply_standout_seniority_adjustment(base, seniority)
        final = apply_company_profile(adjusted, COMPANY_PROFILES[company], "standout")
        assert abs(sum(final.values()) - 1.0) < 0.001
