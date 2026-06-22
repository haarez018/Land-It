"""Success Pattern Analyzer: detects what resume patterns lead to callbacks."""

from __future__ import annotations

from dataclasses import dataclass

from backend.parsers.schemas import Application


@dataclass
class SuccessPattern:
    pattern: str
    confidence: str
    sample_size: int
    recommendation: str


def analyze_success_patterns(applications: list[Application]) -> list[SuccessPattern]:
    if len(applications) < 5:
        return [SuccessPattern(
            pattern="Not enough data yet",
            confidence="low", sample_size=len(applications),
            recommendation=f"Apply to {10 - len(applications)} more roles to start detecting patterns",
        )]

    patterns: list[SuccessPattern] = []

    # Analyze by ATS score ranges
    with_scores = [a for a in applications if a.ats_score_after is not None]
    if with_scores:
        high_score = [a for a in with_scores if (a.ats_score_after or 0) >= 70]
        low_score = [a for a in with_scores if (a.ats_score_after or 0) < 50]
        callbacks_high = sum(1 for a in high_score if a.status.value in ("phone_screen", "interviewing", "offer"))
        callbacks_low = sum(1 for a in low_score if a.status.value in ("phone_screen", "interviewing", "offer"))

        if len(high_score) >= 3 and len(low_score) >= 3:
            rate_high = callbacks_high / len(high_score) if high_score else 0
            rate_low = callbacks_low / len(low_score) if low_score else 0
            if rate_high > rate_low * 1.5:
                patterns.append(SuccessPattern(
                    pattern=f"Resumes scoring 70+ get {rate_high:.0%} callback vs {rate_low:.0%} for <50",
                    confidence="medium" if len(with_scores) >= 10 else "low",
                    sample_size=len(with_scores),
                    recommendation="Focus on tailoring resumes to score above 70 before applying",
                ))

    # Analyze tailored vs original
    tailored = [a for a in applications if a.tailored_resume_id]
    untailored = [a for a in applications if not a.tailored_resume_id]
    if len(tailored) >= 3 and len(untailored) >= 3:
        t_callbacks = sum(1 for a in tailored if a.status.value in ("phone_screen", "interviewing", "offer"))
        u_callbacks = sum(1 for a in untailored if a.status.value in ("phone_screen", "interviewing", "offer"))
        t_rate = t_callbacks / len(tailored)
        u_rate = u_callbacks / len(untailored)
        if t_rate > u_rate:
            patterns.append(SuccessPattern(
                pattern=f"Tailored resumes get {t_rate:.0%} callbacks vs {u_rate:.0%} for untailored",
                confidence="medium", sample_size=len(tailored) + len(untailored),
                recommendation="Always tailor your resume before applying",
            ))

    # General follow-up pattern
    followed_up = [a for a in applications if a.status.value == "followed_up"]
    if len(followed_up) >= 3:
        fu_advanced = sum(1 for a in followed_up if a.status.value in ("phone_screen", "interviewing"))
        patterns.append(SuccessPattern(
            pattern=f"Follow-ups led to {fu_advanced} interview advances out of {len(followed_up)} sent",
            confidence="low", sample_size=len(followed_up),
            recommendation="Send follow-ups 5-7 days after applying",
        ))

    if not patterns:
        patterns.append(SuccessPattern(
            pattern="No clear patterns yet — keep applying and reporting outcomes",
            confidence="low", sample_size=len(applications),
            recommendation="Report which applications got callbacks to improve pattern detection",
        ))

    return patterns
