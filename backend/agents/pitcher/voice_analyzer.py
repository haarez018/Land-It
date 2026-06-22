"""
Extract writing voice from user samples to produce a VoiceProfile.

Analyzes sentence structure, formality, characteristic phrases, and tone
from writing samples (cover letters, emails, LinkedIn posts, etc.).
Falls back to heuristic analysis when no LLM is available.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VoiceProfile:
    """Captured writing style of a candidate."""
    avg_sentence_length: float = 15.0
    formality_level: str = "semi-formal"  # casual | semi-formal | formal | academic
    characteristic_phrases: list[str] = field(default_factory=list)
    punctuation_style: str = "standard"  # oxford_comma | em_dash_heavy | semicolon_user | standard
    enthusiasm_markers: list[str] = field(default_factory=list)
    hedging_frequency: str = "low"  # low | medium | high
    storytelling_style: str = "direct"  # anecdote_first | direct | data_driven | reflective
    tone: str = "warm_professional"  # warm_professional | confident_casual | formal_authoritative | friendly_approachable
    vocabulary_complexity: str = "professional"  # simple | professional | graduate_level | academic
    recurring_structures: list[str] = field(default_factory=list)
    things_to_avoid: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "avg_sentence_length": self.avg_sentence_length,
            "formality_level": self.formality_level,
            "characteristic_phrases": self.characteristic_phrases,
            "punctuation_style": self.punctuation_style,
            "enthusiasm_markers": self.enthusiasm_markers,
            "hedging_frequency": self.hedging_frequency,
            "storytelling_style": self.storytelling_style,
            "tone": self.tone,
            "vocabulary_complexity": self.vocabulary_complexity,
            "recurring_structures": self.recurring_structures,
            "things_to_avoid": self.things_to_avoid,
        }


# ── Heuristic constants ────────────────────────────────────────────────────

_FORMAL_MARKERS = {
    "furthermore", "consequently", "nevertheless", "henceforth", "thereby",
    "accordingly", "notwithstanding", "whereas", "herein", "aforementioned",
    "pursuant", "respectively", "thus", "hence", "moreover",
}

_CASUAL_MARKERS = {
    "honestly", "basically", "pretty much", "kind of", "sort of",
    "super", "really", "actually", "like", "tons of", "huge fan",
    "love", "awesome", "excited", "stoked", "pumped", "cool",
}

_HEDGING_WORDS = {
    "maybe", "perhaps", "possibly", "might", "could", "somewhat",
    "fairly", "rather", "slightly", "tends to", "seems", "appears",
    "i think", "i believe", "i feel", "in my opinion",
}

_ENTHUSIASM_WORDS = {
    "!", "excited", "passionate", "thrilled", "love", "genuinely",
    "incredible", "amazing", "fantastic", "remarkable", "truly",
}

_STORYTELLING_OPENERS = {
    "anecdote_first": ["when i", "i remember", "one time", "back when", "there was a time"],
    "data_driven": ["in my experience", "data shows", "research indicates", "studies suggest", "metrics"],
    "reflective": ["looking back", "i've learned", "what i realized", "the key insight", "reflecting on"],
}


# ── Analysis functions ──────────────────────────────────────────────────────

def _analyze_sentence_length(text: str) -> float:
    """Average sentence length in words."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if not sentences:
        return 15.0
    lengths = [len(s.split()) for s in sentences]
    return sum(lengths) / len(lengths)


def _analyze_formality(text: str) -> str:
    """Detect formality level from vocabulary."""
    text_lower = text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))

    formal_count = len(words & _FORMAL_MARKERS)
    casual_count = sum(1 for marker in _CASUAL_MARKERS if marker in text_lower)

    if formal_count >= 3:
        return "formal"
    if formal_count >= 1 and casual_count == 0:
        return "semi-formal"
    if casual_count >= 3:
        return "casual"
    return "semi-formal"


def _analyze_punctuation(text: str) -> str:
    """Detect punctuation style."""
    em_dashes = text.count("—") + text.count(" - ") + text.count("--")
    semicolons = text.count(";")
    oxford_commas = len(re.findall(r",\s+\w+,\s+and\b", text))

    if em_dashes >= 3:
        return "em_dash_heavy"
    if semicolons >= 3:
        return "semicolon_user"
    if oxford_commas >= 2:
        return "oxford_comma"
    return "standard"


def _analyze_hedging(text: str) -> str:
    """Detect hedging frequency."""
    text_lower = text.lower()
    hedge_count = sum(1 for h in _HEDGING_WORDS if h in text_lower)
    word_count = len(text.split())

    if word_count == 0:
        return "low"
    ratio = hedge_count / (word_count / 100)
    if ratio >= 3:
        return "high"
    if ratio >= 1:
        return "medium"
    return "low"


def _analyze_enthusiasm(text: str) -> tuple[list[str], str]:
    """Detect enthusiasm markers and tone."""
    text_lower = text.lower()
    found: list[str] = []
    for marker in _ENTHUSIASM_WORDS:
        if marker in text_lower or marker in text:
            found.append(marker)

    exclamation_count = text.count("!")
    if exclamation_count >= 3 or len(found) >= 3:
        tone = "confident_casual"
    elif len(found) >= 1:
        tone = "warm_professional"
    else:
        tone = "formal_authoritative"

    return found[:5], tone


def _analyze_storytelling(text: str) -> str:
    """Detect storytelling style."""
    text_lower = text.lower()
    for style, openers in _STORYTELLING_OPENERS.items():
        if any(opener in text_lower for opener in openers):
            return style
    return "direct"


def _extract_characteristic_phrases(text: str) -> list[str]:
    """Extract recurring multi-word phrases."""
    # Find 2-4 word phrases that appear more than once
    words = re.findall(r"\b\w+\b", text.lower())
    phrases: list[str] = []

    for n in (3, 2):
        ngrams = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
        counts = Counter(ngrams)
        for phrase, count in counts.most_common(10):
            if count >= 2 and not all(
                w in {"the", "a", "an", "is", "was", "to", "and", "of", "in", "for", "that", "with", "it", "on"}
                for w in phrase.split()
            ):
                phrases.append(phrase)

    return phrases[:5]


def _analyze_vocabulary_complexity(text: str) -> str:
    """Estimate vocabulary complexity."""
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return "professional"

    avg_word_length = sum(len(w) for w in words) / len(words)
    long_words = sum(1 for w in words if len(w) >= 8)
    long_ratio = long_words / len(words)

    if avg_word_length >= 6.5 or long_ratio >= 0.25:
        return "academic"
    if avg_word_length >= 5.5 or long_ratio >= 0.15:
        return "graduate_level"
    if avg_word_length >= 4.5:
        return "professional"
    return "simple"


def _detect_recurring_structures(text: str) -> list[str]:
    """Detect sentence structure patterns."""
    structures: list[str] = []
    sentences = re.split(r"[.!?]+", text)

    patterns = {
        "I [verb]ed X, which [result]": r"I \w+ed .+, which .+",
        "By [verb]ing X, I [result]": r"By \w+ing .+, I .+",
        "When I [verb], [result]": r"When I \w+, .+",
        "[Result] through [action]": r".+ through \w+ing",
        "As a [role], I [action]": r"As a .+, I .+",
    }

    for label, pattern in patterns.items():
        matches = sum(1 for s in sentences if re.search(pattern, s.strip()))
        if matches >= 2:
            structures.append(label)

    return structures[:3]


def _analyze_paragraph_patterns(text: str) -> dict:
    """How does this person structure paragraphs?"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return {"avg_paragraph_length": 0, "paragraph_count": 0, "prefers_short_paragraphs": True}
    lengths = [len(p.split()) for p in paragraphs]
    avg = sum(lengths) / len(lengths)
    return {
        "avg_paragraph_length": round(avg, 1),
        "paragraph_count": len(paragraphs),
        "prefers_short_paragraphs": avg < 50,
    }


def _analyze_jargon_level(text: str) -> str:
    """Does this person use technical jargon or plain language?"""
    jargon_words = ["leverage", "synergy", "paradigm", "ecosystem", "scalable",
                    "robust", "cutting-edge", "state-of-the-art", "bleeding-edge",
                    "best-in-class", "world-class", "mission-critical"]
    plain_words = {"use", "work", "help", "make", "build", "fix", "good", "fast"}
    words = text.lower().split()
    jargon_count = sum(1 for w in words if any(j in w for j in jargon_words))
    plain_count = sum(1 for w in words if w in plain_words)
    ratio = jargon_count / max(plain_count, 1)
    if ratio > 0.3:
        return "heavy_jargon"
    if ratio > 0.1:
        return "moderate_jargon"
    return "plain_language"


def _analyze_voice_ratio(text: str) -> float:
    """Active vs passive voice ratio. Higher = more active."""
    passive_patterns = [
        r"was\s+\w+ed\b", r"were\s+\w+ed\b", r"been\s+\w+ed\b",
        r"is\s+\w+ed\b", r"are\s+\w+ed\b", r"being\s+\w+ed\b",
    ]
    sentences = re.split(r"[.!?]+", text)
    passive_count = sum(
        1 for s in sentences if any(re.search(p, s, re.I) for p in passive_patterns)
    )
    total = max(len(sentences), 1)
    return round(1.0 - (passive_count / total), 2)


def _analyze_transition_words(text: str) -> dict:
    """What transition patterns does this person use?"""
    transitions = {
        "however": 0, "moreover": 0, "furthermore": 0, "additionally": 0,
        "consequently": 0, "therefore": 0, "nevertheless": 0,
        "specifically": 0, "in particular": 0, "for example": 0,
        "that said": 0, "on the other hand": 0, "in addition": 0,
        "as a result": 0, "more importantly": 0,
    }
    text_lower = text.lower()
    for word in transitions:
        transitions[word] = text_lower.count(word)
    used = {k: v for k, v in transitions.items() if v > 0}
    return {
        "transition_frequency": sum(used.values()),
        "favorite_transitions": sorted(used, key=used.get, reverse=True)[:3] if used else [],
        "style": "formal" if any(w in used for w in ["moreover", "furthermore", "consequently"]) else "casual",
    }


def _analyze_question_usage(text: str) -> dict:
    """How often does this person use questions in writing?"""
    # Count question marks directly, then compute ratio against total sentences
    questions = text.count("?")
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    total = max(len(sentences), 1)
    return {
        "question_count": questions,
        "question_ratio": round(questions / total, 2),
        "uses_rhetorical_questions": questions > 0,
    }


# ── Main analysis function ──────────────────────────────────────────────────

def analyze_voice(samples: list[str]) -> VoiceProfile:
    """
    Analyze writing samples and produce a VoiceProfile.

    Args:
        samples: List of writing samples (cover letters, emails, etc.)

    Returns:
        VoiceProfile capturing the candidate's writing style
    """
    if not samples:
        return VoiceProfile()  # Return defaults

    combined = "\n\n".join(samples)

    avg_sentence_length = _analyze_sentence_length(combined)
    formality = _analyze_formality(combined)
    punctuation = _analyze_punctuation(combined)
    hedging = _analyze_hedging(combined)
    enthusiasm_markers, tone = _analyze_enthusiasm(combined)
    storytelling = _analyze_storytelling(combined)
    characteristic_phrases = _extract_characteristic_phrases(combined)
    vocabulary = _analyze_vocabulary_complexity(combined)
    recurring_structures = _detect_recurring_structures(combined)

    # Derive things to avoid based on what the person DOESN'T do
    avoid: list[str] = []
    if formality == "casual":
        avoid.append("overly formal language like 'pursuant to'")
    elif formality == "formal":
        avoid.append("casual language like 'super excited' or 'awesome'")
    if hedging == "low":
        avoid.append("hedging words like 'maybe' or 'perhaps'")
    if "!" not in combined:
        avoid.append("exclamation marks")

    return VoiceProfile(
        avg_sentence_length=round(avg_sentence_length, 1),
        formality_level=formality,
        characteristic_phrases=characteristic_phrases,
        punctuation_style=punctuation,
        enthusiasm_markers=enthusiasm_markers,
        hedging_frequency=hedging,
        storytelling_style=storytelling,
        tone=tone,
        vocabulary_complexity=vocabulary,
        recurring_structures=recurring_structures,
        things_to_avoid=avoid,
    )
