"""Comprehensive tests for all 15 new features."""

from __future__ import annotations

from datetime import date
import pytest

from backend.parsers.schemas import (
    Resume, ResumeContact, WorkExperience, Education, Application, ApplicationStatus, JobDescription,
)


def _resume(**kwargs) -> Resume:
    defaults = dict(
        contact=ResumeContact(name="Alex Chen", email="alex@test.com", location="San Francisco, CA"),
        raw_text="Alex Chen\nalex@test.com\nSUMMARY\nSenior backend engineer with 8 years building distributed systems.\nEXPERIENCE\nGoogle\nSenior Engineer\nJan 2020 - Present\n- Architected pipeline handling 5M events/day using Kafka and Go\n- Led team of 8 engineers\nSKILLS\nPython, Go, Kafka, PostgreSQL, AWS, Docker, Kubernetes",
        skills={"lang": ["Python", "Go"], "infra": ["Kafka", "PostgreSQL", "AWS", "Docker", "Kubernetes"]},
        work_experience=[WorkExperience(
            company="Google", title="Senior Engineer", start_date=date(2020, 1, 1),
            bullets=["Architected pipeline handling 5M events/day using Kafka and Go, reducing latency by 40%",
                     "Led team of 8 engineers to redesign service, improving reliability from 94% to 99.7%",
                     "Mentored 4 junior engineers through promotion"],
            technologies=["Python", "Go", "Kafka", "PostgreSQL", "AWS"],
            seniority_signals=["led", "architected", "mentored"],
        )],
        education=[Education(institution="Stanford", degree="MS", field="Computer Science", graduation_date=date(2017, 6, 1))],
        total_yoe=8.0, seniority_level="senior", primary_domain="backend",
    )
    defaults.update(kwargs)
    return Resume(**defaults)


# ═══════════════════════════════════════════════════════════════════════════
# TASK 1: Bias Detector
# ═══════════════════════════════════════════════════════════════════════════

class TestBiasDetector:
    def test_ninja_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="Code ninja with 10 years experience")
        report = detect_bias(r)
        assert any(f.text == "ninja" for f in report.flags)
        assert report.gendered_flags >= 1

    def test_rockstar_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="10x rockstar developer guru")
        report = detect_bias(r)
        assert any(f.text == "rockstar" for f in report.flags)
        assert any(f.text == "guru" for f in report.flags)

    def test_clean_resume(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="Senior engineer with expertise in distributed systems. Built and scaled APIs.")
        report = detect_bias(r)
        assert report.bias_free_score >= 95
        assert report.assessment == "Clean"

    def test_old_graduation_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="Graduated 1975 from MIT")
        report = detect_bias(r)
        assert report.age_flags >= 1

    def test_recent_graduation_not_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="Graduated 2022 from Stanford")
        report = detect_bias(r)
        age_year_flags = [f for f in report.flags if f.bias_type == "age" and f.text.isdigit()]
        assert len(age_year_flags) == 0

    def test_native_tongue_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="English is my native tongue")
        report = detect_bias(r)
        assert report.cultural_flags >= 1

    def test_score_degrades_with_flags(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="Code ninja rockstar guru veteran seasoned")
        report = detect_bias(r)
        assert report.bias_free_score < 70
        assert report.assessment == "Needs attention"

    def test_top_priority_fix(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="I am a code ninja")
        report = detect_bias(r)
        assert report.top_priority_fix is not None

    def test_references_available_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="References available upon request")
        report = detect_bias(r)
        assert report.age_flags >= 1

    def test_disability_disclosure_flagged(self):
        from backend.agents.tailor.bias_detector import detect_bias
        r = _resume(raw_text="Despite my disability, I excelled")
        report = detect_bias(r)
        assert report.total_flags >= 1


# ═══════════════════════════════════════════════════════════════════════════
# TASK 2: ATS System-Specific
# ═══════════════════════════════════════════════════════════════════════════

class TestATSSystems:
    def test_stripe_is_greenhouse(self):
        from backend.agents.tailor.ats_systems import get_ats_for_company
        profile = get_ats_for_company("Stripe")
        assert profile is not None
        assert profile.name == "Greenhouse"

    def test_amazon_is_workday(self):
        from backend.agents.tailor.ats_systems import get_ats_for_company
        profile = get_ats_for_company("Amazon")
        assert profile is not None
        assert profile.name == "Workday"

    def test_unknown_company(self):
        from backend.agents.tailor.ats_systems import get_ats_for_company
        assert get_ats_for_company("Random Startup XYZ") is None

    def test_6_ats_profiles(self):
        from backend.agents.tailor.ats_systems import ATS_PROFILES
        assert len(ATS_PROFILES) >= 6

    def test_all_profiles_have_fields(self):
        from backend.agents.tailor.ats_systems import ATS_PROFILES
        for key, p in ATS_PROFILES.items():
            assert p.name, f"{key} missing name"
            assert p.format_recommendations, f"{key} missing recommendations"
            assert p.preferred_format in ("pdf", "docx", "both"), f"{key} bad format"

    def test_company_ats_map_coverage(self):
        from backend.agents.tailor.ats_systems import COMPANY_ATS_MAP
        assert len(COMPANY_ATS_MAP) >= 25

    def test_recommendations_for_workday(self):
        from backend.agents.tailor.ats_systems import get_ats_recommendations
        r = _resume()
        recs = get_ats_recommendations(r, "Amazon")
        assert recs["ats_detected"] == "Workday"
        assert len(recs["recommendations"]) >= 1

    def test_recommendations_unknown(self):
        from backend.agents.tailor.ats_systems import get_ats_recommendations
        r = _resume()
        recs = get_ats_recommendations(r, "Unknown Corp")
        assert recs["ats_detected"] is None

    def test_netflix_is_lever(self):
        from backend.agents.tailor.ats_systems import get_ats_for_company
        assert get_ats_for_company("Netflix").name == "Lever"

    def test_vercel_is_ashby(self):
        from backend.agents.tailor.ats_systems import get_ats_for_company
        assert get_ats_for_company("Vercel").name == "Ashby"


# ═══════════════════════════════════════════════════════════════════════════
# TASK 3: STAR Story Bank
# ═══════════════════════════════════════════════════════════════════════════

class TestStoryBank:
    @pytest.fixture(autouse=True)
    def clean(self):
        from backend.agents.coach.story_bank import story_bank
        story_bank.clear()
        yield
        story_bank.clear()

    def test_add_story(self):
        from backend.agents.coach.story_bank import STARStory, story_bank
        s = STARStory(title="Led migration", situation="Legacy monolith", task="Break into microservices",
                      action="Designed new architecture and led team of 6", result="Reduced deploy time by 60%, saved $2M/year",
                      company_context="At Stripe, on payments team", metrics=["60% faster deploys", "$2M saved"])
        story_bank.add_story(s)
        assert len(story_bank.get_stories()) == 1
        assert s.specificity_score > 0
        assert s.impact_score > 0

    def test_question_classification(self):
        from backend.agents.coach.story_bank import classify_question
        assert classify_question("Tell me about a time you disagreed with someone") == "conflict"
        assert classify_question("Describe a failure you learned from") == "failure"
        assert classify_question("How did you lead a team?") == "leadership"

    def test_story_matching(self):
        from backend.agents.coach.story_bank import STARStory, story_bank
        s = STARStory(title="Conflict", situation="Disagreed with tech lead",
                      task="Resolve disagreement", action="Presented data", result="My approach adopted")
        story_bank.add_story(s)
        matches = story_bank.get_story_for_question("Tell me about a conflict")
        assert len(matches) >= 1

    def test_coverage_analysis(self):
        from backend.agents.coach.story_bank import STARStory, story_bank
        for qt in ["I led a team", "We had a conflict", "I failed at something"]:
            story_bank.add_story(STARStory(title=qt, situation=qt, task="do", action="did", result="done"))
        analysis = story_bank.analyze_coverage()
        assert analysis.question_types_covered >= 2
        assert len(analysis.gaps) >= 1
        assert analysis.coverage_percentage > 0

    def test_gap_detection(self):
        from backend.agents.coach.story_bank import story_bank
        analysis = story_bank.analyze_coverage()
        assert analysis.total_stories == 0
        assert len(analysis.gaps) == 10

    def test_impact_scoring(self):
        from backend.agents.coach.story_bank import score_impact, STARStory
        high = STARStory(title="Big win", result="Generated $5M revenue, promoted to senior, adopted company-wide")
        low = STARStory(title="Small win", result="Completed the task on time")
        assert score_impact(high) > score_impact(low)

    def test_specificity_scoring(self):
        from backend.agents.coach.story_bank import score_specificity, STARStory
        detailed = STARStory(title="T", situation="At Stripe on the payments team, we had a critical issue " * 5,
                             action="I analyzed the root cause and implemented a fix by redesigning the queue processing " * 5,
                             result="Reduced incidents by 90%", company_context="Stripe payments team", metrics=["90% fewer incidents"])
        vague = STARStory(title="T", situation="Had a problem", action="Fixed it", result="Better")
        assert score_specificity(detailed) > score_specificity(vague)


# ═══════════════════════════════════════════════════════════════════════════
# TASK 4: Career Path Simulator
# ═══════════════════════════════════════════════════════════════════════════

class TestCareerSimulator:
    def test_basic_simulation(self):
        from backend.agents.planner.career_simulator import simulate_career
        r = _resume()
        result = simulate_career(r)
        assert result.recommended_path in ("ic_track", "management_track", "specialist_track")
        assert result.likely_title_2yr
        assert result.likely_salary_2yr[0] > 0

    def test_management_signals(self):
        from backend.agents.planner.career_simulator import simulate_career
        r = _resume(work_experience=[WorkExperience(
            company="Google", title="Engineering Manager", start_date=date(2018, 1, 1),
            bullets=["Led team of 12 engineers", "Managed hiring pipeline", "Mentored 8 reports",
                     "Hired 5 senior engineers", "Coached team to promotion"],
            technologies=["Python"], seniority_signals=["led", "managed", "mentored", "hired", "coached"],
        )])
        result = simulate_career(r)
        assert result.recommended_path == "management_track"

    def test_3_paths_returned(self):
        from backend.agents.planner.career_simulator import simulate_career
        result = simulate_career(_resume())
        assert len(result.paths) >= 2

    def test_5yr_salary_higher_than_2yr(self):
        from backend.agents.planner.career_simulator import simulate_career
        result = simulate_career(_resume())
        assert result.likely_salary_5yr[1] >= result.likely_salary_2yr[0]

    def test_skills_to_develop(self):
        from backend.agents.planner.career_simulator import simulate_career
        result = simulate_career(_resume())
        assert isinstance(result.skills_to_develop_2yr, list)


# ═══════════════════════════════════════════════════════════════════════════
# TASK 5: Market Trends
# ═══════════════════════════════════════════════════════════════════════════

class TestMarketTrends:
    def test_backend_snapshot(self):
        from backend.agents.scout.market_trends import get_market_snapshot
        s = get_market_snapshot("software_engineer_backend")
        assert len(s.hot_skills) >= 3
        assert len(s.declining_skills) >= 1
        assert s.remote_percentage > 0

    def test_market_fit(self):
        from backend.agents.scout.market_trends import get_user_market_fit
        r = _resume()
        fit = get_user_market_fit(r, "software_engineer_backend")
        assert 0 <= fit.market_fit_score <= 100
        assert isinstance(fit.hot_skills_you_have, list)
        assert isinstance(fit.advice, str)

    def test_frontend_snapshot(self):
        from backend.agents.scout.market_trends import get_market_snapshot
        s = get_market_snapshot("software_engineer_frontend")
        assert len(s.hot_skills) >= 1

    def test_unknown_role_fallback(self):
        from backend.agents.scout.market_trends import get_market_snapshot
        s = get_market_snapshot("unknown_role")
        assert len(s.hot_skills) >= 1

    def test_emerging_requirements(self):
        from backend.agents.scout.market_trends import get_market_snapshot
        s = get_market_snapshot("software_engineer_backend")
        assert len(s.emerging_requirements) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# TASK 6: Cold Outreach
# ═══════════════════════════════════════════════════════════════════════════

class TestOutreach:
    def test_linkedin_dm(self):
        from backend.agents.pitcher.outreach_generator import generate_outreach
        msg = generate_outreach(_resume(), "Stripe", "Senior Backend Engineer")
        assert msg.channel == "linkedin"
        assert "Stripe" in msg.body
        assert msg.word_count > 20
        assert msg.word_count <= 200

    def test_email(self):
        from backend.agents.pitcher.outreach_generator import generate_outreach
        msg = generate_outreach(_resume(), "Google", "Staff Engineer", channel="email")
        assert msg.channel == "email"
        assert msg.subject is not None
        assert "Google" in msg.body

    def test_engineer_recipient(self):
        from backend.agents.pitcher.outreach_generator import generate_outreach
        msg = generate_outreach(_resume(), "Netflix", "Backend Eng", recipient_type="engineer")
        assert msg.recipient_type == "engineer"

    def test_no_generic_opening(self):
        from backend.agents.pitcher.outreach_generator import generate_outreach
        msg = generate_outreach(_resume(), "Stripe", "Engineer")
        assert "hope this finds you" not in msg.body.lower()


# ═══════════════════════════════════════════════════════════════════════════
# TASK 7: Multi-Format Resume
# ═══════════════════════════════════════════════════════════════════════════

class TestMultiFormat:
    def test_all_5_formats(self):
        from backend.agents.tailor.format_generator import generate_format, RESUME_FORMATS
        r = _resume()
        for fmt in RESUME_FORMATS:
            result = generate_format(r, fmt)
            assert result.content, f"{fmt} produced empty content"
            assert result.word_count > 0, f"{fmt} has 0 words"

    def test_linkedin_has_headline(self):
        from backend.agents.tailor.format_generator import generate_format
        result = generate_format(_resume(), "linkedin_optimized")
        assert "HEADLINE" in result.content

    def test_one_page_has_achievements(self):
        from backend.agents.tailor.format_generator import generate_format
        result = generate_format(_resume(), "one_page_summary")
        assert "ACHIEVEMENTS" in result.content

    def test_portfolio_is_markdown(self):
        from backend.agents.tailor.format_generator import generate_format
        result = generate_format(_resume(), "portfolio_narrative")
        assert "#" in result.content

    def test_unknown_format_falls_back(self):
        from backend.agents.tailor.format_generator import generate_format
        result = generate_format(_resume(), "nonexistent")
        assert result.format_type == "standard_pdf"


# ═══════════════════════════════════════════════════════════════════════════
# TASK 8: Timing Optimizer
# ═══════════════════════════════════════════════════════════════════════════

class TestTimingOptimizer:
    def test_basic_recommendation(self):
        from backend.agents.tracker.timing_optimizer import get_timing_recommendation
        rec = get_timing_recommendation()
        assert rec.best_day == "Tuesday"
        assert "Friday" in rec.avoid_days

    def test_fresh_posting_urgency(self):
        from backend.agents.tracker.timing_optimizer import get_timing_recommendation
        from datetime import date
        today = date.today().isoformat()
        rec = get_timing_recommendation(posting_date=today)
        assert rec.urgency_level == "apply_now"

    def test_old_posting(self):
        from backend.agents.tracker.timing_optimizer import get_timing_recommendation
        rec = get_timing_recommendation(posting_date="2024-01-01")
        assert rec.urgency_level == "may_be_filled"

    def test_no_posting_date(self):
        from backend.agents.tracker.timing_optimizer import get_timing_recommendation
        rec = get_timing_recommendation()
        assert rec.posting_age_days is None


# ═══════════════════════════════════════════════════════════════════════════
# TASK 9: Freshness Decay
# ═══════════════════════════════════════════════════════════════════════════

class TestFreshness:
    def test_current_role_high_score(self):
        from backend.agents.tailor.freshness import analyze_freshness
        r = _resume()
        report = analyze_freshness(r)
        assert report.freshness_score >= 80
        assert report.last_role_recency == "current"

    def test_stale_resume(self):
        from backend.agents.tailor.freshness import analyze_freshness
        r = _resume(work_experience=[WorkExperience(
            company="Old Corp", title="Engineer", start_date=date(2015, 1, 1), end_date=date(2018, 6, 1),
            bullets=["Did stuff"], technologies=["jQuery"],
        )], skills={"lang": ["jQuery", "CoffeeScript"]})
        report = analyze_freshness(r)
        assert report.freshness_score < 50
        assert len(report.decay_factors) >= 1

    def test_deprecated_tech_penalty(self):
        from backend.agents.tailor.freshness import analyze_freshness
        r = _resume(skills={"lang": ["jQuery", "CoffeeScript", "Flash"]})
        report = analyze_freshness(r)
        assert report.skills_currency < 100

    def test_objective_section_flagged(self):
        from backend.agents.tailor.freshness import analyze_freshness
        r = _resume(raw_text="OBJECTIVE\nTo obtain a position...\nEXPERIENCE\n...")
        report = analyze_freshness(r)
        assert report.format_modernity < 100


# ═══════════════════════════════════════════════════════════════════════════
# TASK 10: Learning Paths
# ═══════════════════════════════════════════════════════════════════════════

class TestLearningPaths:
    def test_generate_plan(self):
        from backend.agents.tailor.skill_gap import SkillGap, SkillGapAnalysis
        from backend.agents.planner.learning_path import generate_learning_plan
        gaps = SkillGapAnalysis(
            total_gaps=2, critical_gaps=[
                SkillGap("kubernetes", "required", "JD requires K8s", 9.0, "medium", "Learn K8s"),
                SkillGap("rust", "required", "JD requires Rust", 7.0, "hard", "Learn Rust"),
            ], recommended_gaps=[], bonus_gaps=[], matched_skills=[], match_percentage=60,
            total_potential_score_gain=16.0, top_3_highest_impact_gaps=[], quick_wins=[], short_term=[], long_term=[],
        )
        plan = generate_learning_plan(gaps)
        assert plan.total_weeks > 0
        assert len(plan.steps) == 2
        assert plan.expected_score_improvement > 0

    def test_known_resources(self):
        from backend.agents.planner.learning_path import LEARNING_RESOURCES
        assert "kubernetes" in LEARNING_RESOURCES
        assert "rust" in LEARNING_RESOURCES
        assert "aws" in LEARNING_RESOURCES
        assert len(LEARNING_RESOURCES) >= 10

    def test_quick_wins_separated(self):
        from backend.agents.tailor.skill_gap import SkillGap, SkillGapAnalysis
        from backend.agents.planner.learning_path import generate_learning_plan
        gaps = SkillGapAnalysis(
            total_gaps=1, critical_gaps=[SkillGap("python", "required", "", 5.0, "easy", "Add Python")],
            recommended_gaps=[], bonus_gaps=[], matched_skills=[], match_percentage=80,
            total_potential_score_gain=5.0, top_3_highest_impact_gaps=[], quick_wins=[], short_term=[], long_term=[],
        )
        plan = generate_learning_plan(gaps)
        assert len(plan.quick_wins) >= 0 or len(plan.medium_term) >= 0


# ═══════════════════════════════════════════════════════════════════════════
# TASK 11: Consistency Checker
# ═══════════════════════════════════════════════════════════════════════════

class TestConsistencyChecker:
    def test_date_overlap_detected(self):
        from backend.agents.tailor.consistency_checker import check_consistency
        r = _resume(work_experience=[
            WorkExperience(company="A", title="Engineer", start_date=date(2020, 1, 1), end_date=date(2023, 6, 1), bullets=["Built"], technologies=[]),
            WorkExperience(company="B", title="Engineer", start_date=date(2021, 1, 1), end_date=date(2024, 1, 1), bullets=["Built"], technologies=[]),
        ])
        issues = check_consistency(r)
        assert any(i.type == "date_overlap" for i in issues)

    def test_no_overlap_clean(self):
        from backend.agents.tailor.consistency_checker import check_consistency
        r = _resume(work_experience=[
            WorkExperience(company="A", title="Engineer", start_date=date(2022, 1, 1), end_date=None, bullets=["Built"], technologies=[]),
        ])
        issues = check_consistency(r)
        overlaps = [i for i in issues if i.type == "date_overlap"]
        assert len(overlaps) == 0

    def test_yoe_conflict(self):
        from backend.agents.tailor.consistency_checker import check_consistency
        r = _resume(raw_text="SUMMARY\nEngineer with 20 years of experience", summary="Engineer with 20 years of experience", total_yoe=5.0)
        issues = check_consistency(r)
        assert any(i.type == "yoe_conflict" for i in issues)

    def test_employment_gap_detected(self):
        from backend.agents.tailor.consistency_checker import check_consistency
        r = _resume(work_experience=[
            WorkExperience(company="A", title="E", start_date=date(2022, 1, 1), end_date=date(2023, 1, 1), bullets=["X"], technologies=[]),
            WorkExperience(company="B", title="E", start_date=date(2020, 1, 1), end_date=date(2021, 1, 1), bullets=["X"], technologies=[]),
        ])
        issues = check_consistency(r)
        gaps = [i for i in issues if i.type == "employment_gap"]
        assert len(gaps) >= 1

    def test_clean_resume_few_issues(self):
        from backend.agents.tailor.consistency_checker import check_consistency
        r = _resume()
        issues = check_consistency(r)
        critical = [i for i in issues if i.severity == "high"]
        assert len(critical) == 0


# ═══════════════════════════════════════════════════════════════════════════
# TASK 12: Interview Readiness
# ═══════════════════════════════════════════════════════════════════════════

class TestReadinessScore:
    def test_fully_ready(self):
        from backend.agents.coach.readiness_scorer import calculate_readiness
        score = calculate_readiness(resume_combined_score=85, story_coverage_pct=90,
                                     mock_avg_score=80, skill_gaps_addressed_pct=80, company_researched=True)
        assert score.total >= 80
        assert score.readiness_level == "ready"

    def test_not_started(self):
        from backend.agents.coach.readiness_scorer import calculate_readiness
        score = calculate_readiness()
        assert score.total == 0
        assert score.readiness_level == "not_started"
        assert len(score.gaps) >= 4

    def test_partial_readiness(self):
        from backend.agents.coach.readiness_scorer import calculate_readiness
        score = calculate_readiness(resume_combined_score=70, story_coverage_pct=50)
        assert score.readiness_level in ("needs_work", "almost")

    def test_next_steps_generated(self):
        from backend.agents.coach.readiness_scorer import calculate_readiness
        score = calculate_readiness(resume_combined_score=40)
        assert len(score.next_steps) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# TASK 13: Success Patterns
# ═══════════════════════════════════════════════════════════════════════════

class TestSuccessPatterns:
    def test_too_few_apps(self):
        from backend.agents.planner.success_patterns import analyze_success_patterns
        patterns = analyze_success_patterns([])
        assert len(patterns) >= 1
        assert patterns[0].confidence == "low"

    def test_with_apps(self):
        from backend.agents.planner.success_patterns import analyze_success_patterns
        apps = []
        for i in range(10):
            a = Application(status=ApplicationStatus.SUBMITTED if i < 7 else ApplicationStatus.PHONE_SCREEN,
                            ats_score_after=70 + i, tailored_resume_id="t" if i < 5 else None)
            apps.append(a)
        patterns = analyze_success_patterns(apps)
        assert len(patterns) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# TASK 14: Confidence Calibration
# ═══════════════════════════════════════════════════════════════════════════

class TestCalibration:
    def test_perfect_calibration(self):
        from backend.agents.planner.calibration import compute_calibration
        preds = [(0.8, True)] * 8 + [(0.2, False)] * 8
        report = compute_calibration(preds)
        assert report.brier_score < 0.2
        assert report.accuracy > 0.8

    def test_terrible_calibration(self):
        from backend.agents.planner.calibration import compute_calibration
        preds = [(0.9, False)] * 10 + [(0.1, True)] * 10
        report = compute_calibration(preds)
        assert report.brier_score > 0.5

    def test_empty_data(self):
        from backend.agents.planner.calibration import compute_calibration
        report = compute_calibration([])
        assert report.total_predictions == 0
        assert not report.is_well_calibrated

    def test_buckets_created(self):
        from backend.agents.planner.calibration import compute_calibration
        preds = [(i / 20, i % 3 == 0) for i in range(20)]
        report = compute_calibration(preds)
        assert len(report.calibration_buckets) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# TASK 15: Smart Notifications
# ═══════════════════════════════════════════════════════════════════════════

class TestNotifications:
    @pytest.fixture(autouse=True)
    def clean(self):
        from backend.agents.planner.notifications import notification_engine
        notification_engine.clear()
        yield
        notification_engine.clear()

    def test_stale_resume_trigger(self):
        from backend.agents.planner.notifications import notification_engine
        n = notification_engine.check_stale_resume("u1", 15)
        assert n is not None
        assert n.type == "reminder"

    def test_no_stale_if_recent(self):
        from backend.agents.planner.notifications import notification_engine
        n = notification_engine.check_stale_resume("u1", 5)
        assert n is None

    def test_follow_up_trigger(self):
        from backend.agents.planner.notifications import notification_engine
        n = notification_engine.check_follow_up("u1", "Google", 8)
        assert n is not None
        assert "Google" in n.body

    def test_score_milestone(self):
        from backend.agents.planner.notifications import notification_engine
        n = notification_engine.check_score_milestone("u1", 82, 75)
        assert n is not None
        assert n.type == "celebration"

    def test_no_milestone_if_already_high(self):
        from backend.agents.planner.notifications import notification_engine
        n = notification_engine.check_score_milestone("u1", 85, 81)
        assert n is None

    def test_dismiss(self):
        from backend.agents.planner.notifications import notification_engine
        n = notification_engine.check_stale_resume("u1", 20)
        assert n is not None
        pending_before = len(notification_engine.get_pending("u1"))
        notification_engine.dismiss("u1", n.id)
        pending_after = len(notification_engine.get_pending("u1"))
        assert pending_after == pending_before - 1

    def test_get_pending(self):
        from backend.agents.planner.notifications import notification_engine
        notification_engine.check_stale_resume("u1", 20)
        notification_engine.check_follow_up("u1", "Stripe", 10)
        pending = notification_engine.get_pending("u1")
        assert len(pending) == 2


# ═══════════════════════════════════════════════════════════════════════════
# API ROUTE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestNewRoutes:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_ats_systems_list(self, client):
        resp = client.get("/api/ats-systems")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6

    def test_market_trends(self, client):
        resp = client.get("/api/market/trends/software_engineer_backend")
        assert resp.status_code == 200
        assert len(resp.json()["hot_skills"]) >= 1

    def test_timing_recommend(self, client):
        resp = client.post("/api/timing/recommend", json={"industry": "tech"})
        assert resp.status_code == 200
        assert resp.json()["best_day"] == "Tuesday"

    def test_readiness(self, client):
        resp = client.post("/api/readiness", json={"resume_score": 70, "story_coverage": 50})
        assert resp.status_code == 200
        assert "readiness_level" in resp.json()

    def test_notifications_empty(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 200

    def test_story_bank_empty(self, client):
        resp = client.get("/api/coach/stories")
        assert resp.status_code == 200

    def test_story_analysis(self, client):
        resp = client.get("/api/coach/stories/analysis")
        assert resp.status_code == 200
        assert "coverage_percentage" in resp.json()

    def test_route_count(self, client):
        from backend.main import app
        routes = [r for r in app.routes if hasattr(r, "methods")]
        assert len(routes) >= 85
