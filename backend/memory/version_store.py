"""Resume Version Store: tracks all resume versions with scores and improvement trends."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ResumeVersion:
    version_id: str
    resume_id: str
    version_number: int
    created_at: str
    source: str
    target_jd_id: str | None
    target_company: str | None
    ats_score: float
    standout_score: float
    combined_score: float
    callback_probability: float
    tier: str
    change_summary: str
    changes_made: int


@dataclass
class ImprovementTrend:
    versions: int
    first_score: float
    latest_score: float
    improvement: float
    trend: str


class VersionStore:
    """In-memory version store. Tracks all resume versions per user."""

    def __init__(self) -> None:
        self._versions: dict[str, list[ResumeVersion]] = {}

    def add_version(self, version: ResumeVersion) -> None:
        self._versions.setdefault(version.resume_id, []).append(version)

    def get_versions(self, resume_id: str) -> list[ResumeVersion]:
        versions = self._versions.get(resume_id, [])
        return sorted(versions, key=lambda v: v.version_number)

    def get_latest(self, resume_id: str) -> ResumeVersion | None:
        versions = self.get_versions(resume_id)
        return versions[-1] if versions else None

    def get_improvement_trend(self, resume_id: str) -> ImprovementTrend:
        versions = self.get_versions(resume_id)
        if not versions:
            return ImprovementTrend(versions=0, first_score=0, latest_score=0, improvement=0, trend="stable")

        first_score = versions[0].combined_score
        latest_score = versions[-1].combined_score
        improvement = round(latest_score - first_score, 1)

        if len(versions) < 2:
            trend = "stable"
        elif improvement > 5:
            trend = "improving"
        elif improvement < -5:
            trend = "declining"
        else:
            trend = "stable"

        return ImprovementTrend(
            versions=len(versions),
            first_score=first_score,
            latest_score=latest_score,
            improvement=improvement,
            trend=trend,
        )

    def next_version_number(self, resume_id: str) -> int:
        versions = self._versions.get(resume_id, [])
        if not versions:
            return 0
        return max(v.version_number for v in versions) + 1

    def clear(self, resume_id: str | None = None) -> None:
        if resume_id:
            self._versions.pop(resume_id, None)
        else:
            self._versions.clear()


version_store = VersionStore()


def _tier_from_score(score: float) -> str:
    if score >= 85:
        return "Standout"
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Solid"
    if score >= 40:
        return "Needs Work"
    return "Weak"


def record_version(
    resume_id: str,
    source: str,
    ats_score: float,
    standout_score: float,
    combined_score: float,
    callback_probability: float,
    change_summary: str = "",
    changes_made: int = 0,
    target_jd_id: str | None = None,
    target_company: str | None = None,
) -> ResumeVersion:
    import uuid
    version = ResumeVersion(
        version_id=uuid.uuid4().hex,
        resume_id=resume_id,
        version_number=version_store.next_version_number(resume_id),
        created_at=datetime.now(UTC).isoformat(),
        source=source,
        target_jd_id=target_jd_id,
        target_company=target_company,
        ats_score=ats_score,
        standout_score=standout_score,
        combined_score=combined_score,
        callback_probability=callback_probability,
        tier=_tier_from_score(combined_score),
        change_summary=change_summary,
        changes_made=changes_made,
    )
    version_store.add_version(version)
    return version
