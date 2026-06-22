"""
PitcherAgent: generates personalized cover letters in the user's voice.

Pipeline: voice analysis → company research → cover letter generation → validation
Falls back to template-based generation when no LLM is available.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from backend.agents.pitcher.voice_analyzer import VoiceProfile, analyze_voice
from backend.agents.pitcher.company_researcher import CompanyContext, research_company


@dataclass
class CoverLetter:
    """Generated cover letter with metadata."""
    text: str
    word_count: int
    paragraphs: int
    company_name: str
    role_title: str
    voice_match_score: float  # 0-100 estimate of voice alignment
    company_personalization_score: float  # 0-100 how personalized to the company
    requirements_addressed: list[str]
    verification_notes: list[str] = field(default_factory=list)


@dataclass
class PitcherResult:
    """Complete result from the pitcher pipeline."""
    cover_letter: CoverLetter
    voice_profile: VoiceProfile
    company_context: CompanyContext
    alternative_openings: list[str] = field(default_factory=list)


class PitcherAgent:
    """Generates personalized cover letters in the candidate's voice."""

    async def run(self, state: dict) -> dict:
        """
        LangGraph-compatible run method.

        Expected state keys:
            - resume: Resume object
            - jd: JobDescription object
            - writing_samples: list[str] (optional)

        Returns updated state with:
            - pitcher_result: PitcherResult
            - cover_letter: str
        """
        resume: Resume = state["resume"]
        jd: JobDescription = state["jd"]
        samples: list[str] = state.get("writing_samples", [])

        result = await self.generate(resume, jd, writing_samples=samples)

        return {
            **state,
            "pitcher_result": result,
            "cover_letter": result.cover_letter.text,
        }

    async def generate(
        self,
        resume: Resume,
        jd: JobDescription,
        *,
        writing_samples: Optional[list[str]] = None,
    ) -> PitcherResult:
        """
        Full cover letter generation pipeline.

        Args:
            resume: Parsed candidate resume
            jd: Target job description
            writing_samples: Optional writing samples for voice matching

        Returns:
            PitcherResult with letter, voice profile, and company context
        """
        # Step 1: Analyze candidate's voice
        voice = analyze_voice(writing_samples or [])

        # Step 2: Research the company
        company = research_company(jd)

        # Step 3: Select most relevant experience bullets
        relevant_bullets = self._select_relevant_bullets(resume, jd)

        # Step 4: Generate the cover letter (Claude if available, else template)
        try:
            letter_text = await self._generate_with_claude(
                resume=resume,
                jd=jd,
                voice=voice,
                company=company,
                relevant_bullets=relevant_bullets,
            )
        except Exception:
            letter_text = self._generate_letter(
                resume=resume,
                jd=jd,
                voice=voice,
                company=company,
                relevant_bullets=relevant_bullets,
            )

        # Step 5: Generate alternative openings
        alt_openings = self._generate_alternative_openings(jd, company)

        # Step 6: Validate and score
        letter = self._validate_letter(letter_text, jd, company, relevant_bullets)

        return PitcherResult(
            cover_letter=letter,
            voice_profile=voice,
            company_context=company,
            alternative_openings=alt_openings,
        )

    async def _generate_with_claude(
        self,
        resume: Resume,
        jd: JobDescription,
        voice: VoiceProfile,
        company: CompanyContext,
        relevant_bullets: list[str],
    ) -> str:
        """Generate cover letter body using Claude — precise, human, no clichés."""
        from backend.agents.llm import ask

        system = """You are a master cover letter writer and senior career coach.
Write a cover letter body (no salutation, no sign-off — just the paragraphs).

Non-negotiable rules:
- 3–4 paragraphs, 220–300 words total
- Zero clichés: never use "passionate about", "team player", "detail-oriented", "I am writing to express"
- Open with a specific hook about THIS company — something that shows you researched them
- Name 2 concrete achievements with measurable outcomes from the candidate's experience
- Connect achievements directly to what the role requires
- Close with confident next-step language, not pleading ("I look forward to hearing from you" is banned)
- Sound like a real human wrote this for this specific role, not a template"""

        skills_text = ", ".join(
            s
            for cat_skills in list(resume.skills.values())[:4]
            for s in cat_skills[:4]
        )
        bullets_text = "\n".join(f"• {b}" for b in relevant_bullets[:5])
        reqs_text = "\n".join(f"• {r.text}" for r in jd.requirements[:5])

        user = f"""Write the cover letter body for this candidate applying to this role.

CANDIDATE: {resume.contact.name} | {resume.total_yoe:.1f} years of experience | {resume.seniority_level}
SKILLS: {skills_text}

STRONGEST ACHIEVEMENTS:
{bullets_text}

TARGET ROLE: {jd.title or 'Software Engineer'} at {jd.company or 'the company'}
KEY REQUIREMENTS:
{reqs_text}

COMPANY CONTEXT:
Mission: {company.mission or 'Not specified'}
Values: {', '.join(company.values[:3]) if company.values else 'Not specified'}
Products/Services: {', '.join(company.products[:2]) if company.products else 'Not specified'}
Industry: {company.industry or 'Technology'}

VOICE TO MATCH: {voice.tone} tone, {voice.formality_level} formality
Style markers: {', '.join(voice.characteristic_phrases[:2]) if voice.characteristic_phrases else 'direct and confident'}

Write the letter body now (3–4 paragraphs, no salutation, no sign-off):"""

        return await ask(system, user, model="claude-haiku-4-5-20251001", max_tokens=700)

    def _select_relevant_bullets(
        self, resume: Resume, jd: JobDescription, top_n: int = 5
    ) -> list[str]:
        """Select the most JD-relevant bullets from the resume."""
        jd_keywords = set()
        for kw in jd.required_skills + jd.preferred_skills + jd.tech_stack:
            jd_keywords.add(kw.lower())
        for req in jd.requirements:
            for word in re.findall(r"\b\w{3,}\b", req.text):
                jd_keywords.add(word.lower())

        scored: list[tuple[float, str]] = []
        for exp in resume.work_experience:
            for bullet in exp.bullets:
                words = set(w.lower() for w in re.findall(r"\b\w{3,}\b", bullet))
                overlap = len(words & jd_keywords)
                has_metric = bool(re.search(r"\d+[%$KMBkmb]|\$\d+", bullet))
                score = overlap * 2 + (5 if has_metric else 0)
                scored.append((score, bullet))

        scored.sort(reverse=True)
        return [bullet for _, bullet in scored[:top_n]]

    def _generate_letter(
        self,
        resume: Resume,
        jd: JobDescription,
        voice: VoiceProfile,
        company: CompanyContext,
        relevant_bullets: list[str],
    ) -> str:
        """Generate cover letter text using templates + voice profile."""
        candidate_name = resume.contact.name
        role_title = jd.title or "the open position"
        company_name = jd.company or "your company"

        # ── Opening paragraph ──────────────────────────────────────────
        opening = self._craft_opening(voice, company, role_title)

        # ── Experience paragraph ───────────────────────────────────────
        experience_para = self._craft_experience_paragraph(
            voice, resume, jd, relevant_bullets
        )

        # ── Culture fit paragraph ──────────────────────────────────────
        culture_para = self._craft_culture_paragraph(voice, company, resume)

        # ── Closing paragraph ──────────────────────────────────────────
        closing = self._craft_closing(voice, company_name, role_title)

        # ── Assemble ───────────────────────────────────────────────────
        paragraphs = [opening, experience_para]
        if culture_para:
            paragraphs.append(culture_para)
        paragraphs.append(closing)

        letter = "\n\n".join(paragraphs)
        return letter

    def _craft_opening(
        self, voice: VoiceProfile, company: CompanyContext, role_title: str
    ) -> str:
        """Craft the opening paragraph — company-specific hook."""
        company_name = company.company_name or "your team"

        # Company-specific hook
        if company.mission:
            hook = f"{company_name}'s mission to {company.mission.lower().rstrip('.')} resonates deeply with me"
        elif company.products:
            hook = f"Having used {company.products[0]} extensively, I've seen firsthand how {company_name} approaches product excellence"
        elif company.values:
            hook = f"{company_name}'s emphasis on {company.values[0].lower()} aligns with how I approach my work"
        else:
            hook = f"The engineering challenges at {company_name} are exactly the kind of problems I'm driven to solve"

        # Tone adjustment
        if voice.tone == "confident_casual":
            opening = f"{hook}, and I'd love to bring my experience to the {role_title} role."
        elif voice.tone == "formal_authoritative":
            opening = f"{hook}. I am writing to apply for the {role_title} position, where I believe my background would be a strong fit."
        else:
            # warm_professional (default)
            opening = f"{hook}. I'm excited to apply for the {role_title} role and contribute to what you're building."

        return opening

    def _craft_experience_paragraph(
        self,
        voice: VoiceProfile,
        resume: Resume,
        jd: JobDescription,
        relevant_bullets: list[str],
    ) -> str:
        """Craft the experience paragraph — connect achievements to requirements."""
        parts: list[str] = []

        # Get top requirements
        top_reqs = [r.text for r in jd.requirements[:3]] or jd.role_priorities[:3]

        # Connect bullets to requirements
        if relevant_bullets:
            # Extract key achievement from top bullet
            top_bullet = relevant_bullets[0]
            # Simplify for cover letter
            achievement = self._bullet_to_narrative(top_bullet, voice)
            parts.append(achievement)

        # Add second achievement if available
        if len(relevant_bullets) >= 2:
            second = self._bullet_to_narrative(relevant_bullets[1], voice)
            parts.append(second)

        # Add tech stack connection
        matching_tech = set(s.lower() for s in jd.tech_stack) & set(
            s.lower() for skills in resume.skills.values() for s in skills
        )
        if matching_tech:
            tech_list = ", ".join(list(matching_tech)[:4])
            if voice.tone == "confident_casual":
                parts.append(f"I work with {tech_list} daily and know these tools inside out.")
            else:
                parts.append(f"My expertise spans {tech_list}, which directly aligns with your technical requirements.")

        return " ".join(parts)

    def _bullet_to_narrative(self, bullet: str, voice: VoiceProfile) -> str:
        """Convert a resume bullet into cover letter narrative."""
        # Remove leading verb and convert to first person narrative
        bullet = bullet.strip()

        # Extract the core achievement
        metric_match = re.search(
            r"(\d+[%$KMBkmb]|\$[\d,]+[KMBkmb]?|\d+x\b)", bullet
        )

        if metric_match:
            metric = metric_match.group(1)
            # Build narrative around the metric
            if voice.tone == "confident_casual":
                return f"In my current role, I {bullet[0].lower()}{bullet[1:].rstrip('.')}."
            else:
                return f"At my previous company, I {bullet[0].lower()}{bullet[1:].rstrip('.')}."
        else:
            return f"I have experience {bullet[0].lower()}{bullet[1:].rstrip('.')}."

    def _craft_culture_paragraph(
        self, voice: VoiceProfile, company: CompanyContext, resume: Resume
    ) -> str:
        """Craft the culture fit paragraph."""
        parts: list[str] = []

        if company.values:
            value = company.values[0]
            if voice.tone == "confident_casual":
                parts.append(
                    f"Your value of \"{value}\" is how I naturally operate."
                )
            else:
                parts.append(
                    f"I'm particularly drawn to {company.company_name}'s value of \"{value}\" — it mirrors my own approach to engineering."
                )

        if company.culture_signals:
            signal = company.culture_signals[0]
            parts.append(
                f"The {signal.lower()} resonates with my experience building in similar environments."
            )

        if not parts:
            return ""

        return " ".join(parts)

    def _craft_closing(
        self, voice: VoiceProfile, company_name: str, role_title: str
    ) -> str:
        """Craft the closing paragraph — confident, not pleading."""
        if voice.tone == "confident_casual":
            return (
                f"I'd love to chat about how I can contribute to {company_name}'s next chapter. "
                f"I'm available anytime that works for your team."
            )
        elif voice.tone == "formal_authoritative":
            return (
                f"I am confident that my background and skills would enable me to make meaningful "
                f"contributions to the {role_title} team at {company_name}. "
                f"I welcome the opportunity to discuss this further."
            )
        else:
            return (
                f"I'd welcome the chance to discuss how my experience aligns with what "
                f"{company_name} is building. I'm excited about the impact this role can have, "
                f"and I'm ready to hit the ground running."
            )

    def _generate_alternative_openings(
        self, jd: JobDescription, company: CompanyContext
    ) -> list[str]:
        """Generate 2-3 alternative opening lines."""
        company_name = company.company_name or "your company"
        alternatives: list[str] = []

        if company.products:
            alternatives.append(
                f"As a long-time user of {company.products[0]}, I've always admired "
                f"{company_name}'s approach to solving complex problems at scale."
            )

        if company.recent_news:
            alternatives.append(
                f"After reading about {company.recent_news[0]}, I knew I wanted to be "
                f"part of what {company_name} is building next."
            )

        if company.industry:
            alternatives.append(
                f"The {company.industry} space is at an inflection point, and "
                f"{company_name} is leading the way."
            )

        if company.values and len(company.values) >= 2:
            alternatives.append(
                f"What draws me to {company_name} isn't just the technology — "
                f"it's values like \"{company.values[1]}\" that signal a team I'd thrive in."
            )

        return alternatives[:3]

    def _validate_letter(
        self,
        text: str,
        jd: JobDescription,
        company: CompanyContext,
        relevant_bullets: list[str],
    ) -> CoverLetter:
        """Validate and score the generated cover letter."""
        words = text.split()
        word_count = len(words)
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])

        # Check company personalization
        text_lower = text.lower()
        company_mentions = text_lower.count(company.company_name.lower()) if company.company_name else 0
        has_mission = bool(company.mission and company.mission.lower()[:20] in text_lower)
        has_values = any(v.lower() in text_lower for v in company.values[:2]) if company.values else False
        has_product = any(p.lower() in text_lower for p in company.products[:2]) if company.products else False

        personalization_score = min(100.0, (
            (20 if company_mentions >= 2 else 10 * company_mentions) +
            (25 if has_mission else 0) +
            (25 if has_values else 0) +
            (20 if has_product else 0) +
            (10 if paragraphs >= 3 else 0)
        ))

        # Check voice match (heuristic)
        voice_score = 70.0  # Base for template-generated
        if word_count > 400:
            voice_score -= 10  # Too long
        if word_count < 150:
            voice_score -= 10  # Too short

        # Check banned phrases
        banned = [
            "i am writing to express my interest",
            "passionate about",
            "team player",
            "fast learner",
            "detail-oriented",
        ]
        for phrase in banned:
            if phrase in text_lower:
                voice_score -= 5

        # Requirements addressed
        reqs_addressed: list[str] = []
        for req in jd.requirements[:5]:
            kw = req.extracted_keyword.lower()
            if kw in text_lower:
                reqs_addressed.append(req.text)

        # Verification notes
        notes: list[str] = []
        if word_count > 350:
            notes.append(f"Letter is {word_count} words — consider trimming to under 350")
        if company_mentions < 2:
            notes.append("Consider mentioning the company name at least twice")
        if not reqs_addressed:
            notes.append("Letter doesn't directly reference any JD requirements — consider adding specifics")

        return CoverLetter(
            text=text,
            word_count=word_count,
            paragraphs=paragraphs,
            company_name=company.company_name,
            role_title=jd.title,
            voice_match_score=round(voice_score, 1),
            company_personalization_score=round(personalization_score, 1),
            requirements_addressed=reqs_addressed,
            verification_notes=notes,
        )
