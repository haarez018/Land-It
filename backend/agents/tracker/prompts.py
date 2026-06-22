"""Tracker agent prompts for follow-up email generation."""

FOLLOWUP_PROMPT = """
Write a professional follow-up email for {candidate_name} who applied
to {role_title} at {company_name} on {applied_date}.

This is follow-up #{followup_number}. It has been {days_since} days.

Requirements:
- Under 100 words
- References the specific role
- Reiterates genuine interest (not desperate)
- Has a clear call to action
- Matches the candidate's tone: {tone}
- Subject line included
- DO NOT: apologize for following up, be sycophantic, or repeat the entire cover letter

Return as JSON: {{ "subject": "...", "body": "..." }}
"""
