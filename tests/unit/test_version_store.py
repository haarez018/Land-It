"""Tests for the Resume Version Store."""

from __future__ import annotations

import pytest

from backend.memory.version_store import (
    VersionStore, ResumeVersion, ImprovementTrend,
    record_version, version_store, _tier_from_score,
)


@pytest.fixture(autouse=True)
def clean_store():
    version_store.clear()
    yield
    version_store.clear()


class TestVersionStore:
    def test_add_and_get(self):
        store = VersionStore()
        v = ResumeVersion(
            version_id="v1", resume_id="r1", version_number=0,
            created_at="2024-01-01", source="original", target_jd_id=None,
            target_company=None, ats_score=50, standout_score=40,
            combined_score=46, callback_probability=0.15, tier="Needs Work",
            change_summary="Initial upload", changes_made=0,
        )
        store.add_version(v)
        versions = store.get_versions("r1")
        assert len(versions) == 1
        assert versions[0].version_id == "v1"

    def test_versions_sorted_by_number(self):
        store = VersionStore()
        for i in [2, 0, 1]:
            store.add_version(ResumeVersion(
                version_id=f"v{i}", resume_id="r1", version_number=i,
                created_at="2024-01-01", source="tailored", target_jd_id=None,
                target_company=None, ats_score=50+i*10, standout_score=40,
                combined_score=46+i*10, callback_probability=0.15,
                tier="Solid", change_summary="", changes_made=i,
            ))
        versions = store.get_versions("r1")
        assert [v.version_number for v in versions] == [0, 1, 2]

    def test_get_latest(self):
        store = VersionStore()
        for i in range(3):
            store.add_version(ResumeVersion(
                version_id=f"v{i}", resume_id="r1", version_number=i,
                created_at="2024-01-01", source="tailored", target_jd_id=None,
                target_company=None, ats_score=50+i*10, standout_score=40,
                combined_score=46+i*10, callback_probability=0.15,
                tier="Solid", change_summary="", changes_made=0,
            ))
        latest = store.get_latest("r1")
        assert latest is not None
        assert latest.version_number == 2

    def test_get_latest_empty(self):
        store = VersionStore()
        assert store.get_latest("nonexistent") is None

    def test_next_version_number_empty(self):
        store = VersionStore()
        assert store.next_version_number("r1") == 0

    def test_next_version_number_increments(self):
        store = VersionStore()
        store.add_version(ResumeVersion(
            version_id="v0", resume_id="r1", version_number=0,
            created_at="2024-01-01", source="original", target_jd_id=None,
            target_company=None, ats_score=50, standout_score=40,
            combined_score=46, callback_probability=0.15, tier="Needs Work",
            change_summary="", changes_made=0,
        ))
        assert store.next_version_number("r1") == 1

    def test_clear_specific(self):
        store = VersionStore()
        store.add_version(ResumeVersion(
            version_id="v0", resume_id="r1", version_number=0,
            created_at="", source="original", target_jd_id=None,
            target_company=None, ats_score=50, standout_score=40,
            combined_score=46, callback_probability=0.15, tier="Needs Work",
            change_summary="", changes_made=0,
        ))
        store.add_version(ResumeVersion(
            version_id="v0", resume_id="r2", version_number=0,
            created_at="", source="original", target_jd_id=None,
            target_company=None, ats_score=60, standout_score=50,
            combined_score=56, callback_probability=0.2, tier="Solid",
            change_summary="", changes_made=0,
        ))
        store.clear("r1")
        assert len(store.get_versions("r1")) == 0
        assert len(store.get_versions("r2")) == 1

    def test_clear_all(self):
        store = VersionStore()
        store.add_version(ResumeVersion(
            version_id="v0", resume_id="r1", version_number=0,
            created_at="", source="original", target_jd_id=None,
            target_company=None, ats_score=50, standout_score=40,
            combined_score=46, callback_probability=0.15, tier="Needs Work",
            change_summary="", changes_made=0,
        ))
        store.clear()
        assert len(store.get_versions("r1")) == 0


class TestImprovementTrend:
    def test_no_versions(self):
        store = VersionStore()
        trend = store.get_improvement_trend("r1")
        assert trend.versions == 0
        assert trend.trend == "stable"

    def test_single_version(self):
        store = VersionStore()
        store.add_version(ResumeVersion(
            version_id="v0", resume_id="r1", version_number=0,
            created_at="", source="original", target_jd_id=None,
            target_company=None, ats_score=50, standout_score=40,
            combined_score=46, callback_probability=0.15, tier="Needs Work",
            change_summary="", changes_made=0,
        ))
        trend = store.get_improvement_trend("r1")
        assert trend.versions == 1
        assert trend.trend == "stable"

    def test_improving_trend(self):
        store = VersionStore()
        for i, score in enumerate([40, 55, 70]):
            store.add_version(ResumeVersion(
                version_id=f"v{i}", resume_id="r1", version_number=i,
                created_at="", source="tailored", target_jd_id=None,
                target_company=None, ats_score=score, standout_score=score,
                combined_score=score, callback_probability=score/200,
                tier="Solid", change_summary="", changes_made=i,
            ))
        trend = store.get_improvement_trend("r1")
        assert trend.trend == "improving"
        assert trend.improvement == 30.0

    def test_declining_trend(self):
        store = VersionStore()
        for i, score in enumerate([70, 55, 40]):
            store.add_version(ResumeVersion(
                version_id=f"v{i}", resume_id="r1", version_number=i,
                created_at="", source="tailored", target_jd_id=None,
                target_company=None, ats_score=score, standout_score=score,
                combined_score=score, callback_probability=score/200,
                tier="Solid", change_summary="", changes_made=0,
            ))
        trend = store.get_improvement_trend("r1")
        assert trend.trend == "declining"
        assert trend.improvement == -30.0

    def test_stable_trend(self):
        store = VersionStore()
        for i, score in enumerate([50, 51, 52]):
            store.add_version(ResumeVersion(
                version_id=f"v{i}", resume_id="r1", version_number=i,
                created_at="", source="tailored", target_jd_id=None,
                target_company=None, ats_score=score, standout_score=score,
                combined_score=score, callback_probability=score/200,
                tier="Solid", change_summary="", changes_made=0,
            ))
        trend = store.get_improvement_trend("r1")
        assert trend.trend == "stable"


class TestRecordVersion:
    def test_record_creates_version(self):
        v = record_version(
            resume_id="r1", source="original",
            ats_score=50, standout_score=40, combined_score=46,
            callback_probability=0.15, change_summary="Initial",
        )
        assert v.version_number == 0
        assert v.resume_id == "r1"
        assert v.tier == "Needs Work"

    def test_record_increments_version(self):
        record_version(
            resume_id="r1", source="original",
            ats_score=50, standout_score=40, combined_score=46,
            callback_probability=0.15,
        )
        v2 = record_version(
            resume_id="r1", source="tailored",
            ats_score=70, standout_score=60, combined_score=66,
            callback_probability=0.3, change_summary="Tailored for Google",
            target_company="Google",
        )
        assert v2.version_number == 1
        assert v2.target_company == "Google"


class TestTierFromScore:
    def test_standout(self):
        assert _tier_from_score(90) == "Standout"

    def test_strong(self):
        assert _tier_from_score(75) == "Strong"

    def test_solid(self):
        assert _tier_from_score(60) == "Solid"

    def test_needs_work(self):
        assert _tier_from_score(45) == "Needs Work"

    def test_weak(self):
        assert _tier_from_score(30) == "Weak"


# ── API routes ──────────────────────────────────────────────────────────

class TestVersionRoutes:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_get_versions_empty(self, client):
        resp = client.get("/api/resume/nonexistent/versions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_trend_empty(self, client):
        resp = client.get("/api/resume/nonexistent/versions/trend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["versions"] == 0
        assert data["trend"] == "stable"

    def test_versions_after_recording(self, client):
        record_version(
            resume_id="test-route", source="original",
            ats_score=50, standout_score=40, combined_score=46,
            callback_probability=0.15,
        )
        resp = client.get("/api/resume/test-route/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "original"

    def test_trend_after_recording(self, client):
        for score in [40, 60, 80]:
            record_version(
                resume_id="test-trend", source="tailored",
                ats_score=score, standout_score=score,
                combined_score=score, callback_probability=score/200,
            )
        resp = client.get("/api/resume/test-trend/versions/trend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend"] == "improving"
        assert data["improvement"] == 40.0
