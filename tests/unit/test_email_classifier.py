"""Tests for the email signal classifier."""

import pytest

from backend.agents.tracker.email_monitor import classify_email, GmailMonitor


class TestClassifyEmail:

    def test_rejection_detected(self):
        signal = classify_email(
            "Your application to Backend Engineer at Stripe",
            "Thank you for your interest. After careful review, we have decided to "
            "move forward with other candidates. We wish you the best in your search."
        )
        assert signal.signal_type == "rejection"
        assert signal.confidence >= 0.3

    def test_rejection_variation(self):
        signal = classify_email(
            "Update on your application",
            "Unfortunately, we will not be moving forward with your application "
            "for the Software Engineer role at this time."
        )
        assert signal.signal_type == "rejection"

    def test_interview_invite_detected(self):
        signal = classify_email(
            "Interview invitation - Backend Engineer",
            "We'd love to schedule an interview with you for the Backend Engineer "
            "position. Are you available next Tuesday at 2 PM?"
        )
        assert signal.signal_type == "interview"
        assert signal.confidence >= 0.3

    def test_phone_screen_detected(self):
        signal = classify_email(
            "Introductory call",
            "I'm the recruiter for the Backend Engineer role. I'd like to set up "
            "a 30-minute phone screen to discuss your background."
        )
        assert signal.signal_type == "phone_screen"
        assert signal.confidence >= 0.3

    def test_offer_detected(self):
        signal = classify_email(
            "Offer of Employment",
            "We are thrilled to extend an offer for the Backend Engineer position. "
            "Please find attached the compensation package details."
        )
        assert signal.signal_type == "offer"
        assert signal.confidence >= 0.3

    def test_acknowledgement_detected(self):
        signal = classify_email(
            "Application received",
            "Thank you for applying to the Backend Engineer position. "
            "We've received your application and will review it shortly."
        )
        assert signal.signal_type == "acknowledgement"
        assert signal.confidence >= 0.3

    def test_followup_reply_detected(self):
        signal = classify_email(
            "Re: Following up: Backend Engineer application",
            "Thanks for reaching out. We're still reviewing applications and "
            "will get back to you soon."
        )
        assert signal.signal_type == "follow_up_reply"

    def test_unrelated_email_is_unknown(self):
        signal = classify_email(
            "Your Amazon order has shipped",
            "Your package containing Python Programming book is on its way!"
        )
        assert signal.signal_type == "unknown"

    def test_low_confidence_for_ambiguous(self):
        signal = classify_email(
            "Hi",
            "Just wanted to check in about things."
        )
        assert signal.confidence < 0.5


class TestGmailMonitor:

    def test_not_available_without_config(self):
        monitor = GmailMonitor()
        assert monitor.is_available is False

    @pytest.mark.asyncio
    async def test_check_inbox_raises(self):
        monitor = GmailMonitor()
        with pytest.raises(NotImplementedError, match="Gmail OAuth"):
            await monitor.check_inbox()

    @pytest.mark.asyncio
    async def test_watch_inbox_raises(self):
        monitor = GmailMonitor()
        with pytest.raises(NotImplementedError, match="OAuth"):
            await monitor.watch_inbox()
