"""Career Path Simulator: 3-track projection based on current resume."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.parsers.schemas import Resume


@dataclass
class CareerNode:
    title: str
    seniority: str
    typical_yoe: tuple[int, int]
    typical_salary_range: tuple[int, int]
    skills_needed: list[str]
    probability: float = 0.0


@dataclass
class CareerPath:
    name: str
    nodes: list[CareerNode]
    years_to_reach_end: int
    skills_gaps_for_path: list[str]


@dataclass
class CareerSimulation:
    current_position: CareerNode
    paths: list[CareerPath]
    recommended_path: str
    reasoning: str
    likely_title_2yr: str
    likely_salary_2yr: tuple[int, int]
    skills_to_develop_2yr: list[str]
    likely_title_5yr: str
    likely_salary_5yr: tuple[int, int]
    skills_to_develop_5yr: list[str]


CAREER_LADDERS: dict[str, dict[str, list[CareerNode]]] = {
    "software_engineer_backend": {
        "ic_track": [
            CareerNode("Junior Engineer", "junior", (0, 2), (75_000, 120_000), ["Python", "SQL", "Git"]),
            CareerNode("Software Engineer", "mid", (2, 5), (110_000, 170_000), ["System Design", "APIs", "Testing"]),
            CareerNode("Senior Engineer", "senior", (5, 8), (150_000, 230_000), ["Architecture", "Mentoring", "Performance"]),
            CareerNode("Staff Engineer", "staff_principal", (8, 12), (200_000, 350_000), ["Technical Strategy", "Cross-org Influence"]),
            CareerNode("Principal Engineer", "staff_principal", (12, 20), (250_000, 450_000), ["Industry Expertise", "Technical Vision"]),
        ],
        "management_track": [
            CareerNode("Software Engineer", "mid", (2, 5), (110_000, 170_000), ["System Design", "APIs"]),
            CareerNode("Senior Engineer", "senior", (5, 7), (150_000, 230_000), ["Architecture", "Mentoring"]),
            CareerNode("Engineering Manager", "senior", (7, 10), (180_000, 280_000), ["People Management", "Hiring", "Team Building"]),
            CareerNode("Director of Engineering", "executive", (10, 15), (220_000, 380_000), ["Org Design", "Strategy"]),
            CareerNode("VP of Engineering", "executive", (15, 25), (300_000, 550_000), ["Executive Leadership", "P&L"]),
        ],
        "specialist_track": [
            CareerNode("Software Engineer", "mid", (2, 5), (110_000, 170_000), ["Distributed Systems"]),
            CareerNode("Senior Specialist", "senior", (5, 8), (160_000, 250_000), ["Deep Specialization"]),
            CareerNode("Distinguished Engineer", "staff_principal", (10, 20), (280_000, 500_000), ["Industry Authority", "Research"]),
        ],
    },
    "product_manager": {
        "ic_track": [
            CareerNode("Associate PM", "junior", (0, 2), (80_000, 120_000), ["User Research", "Roadmapping"]),
            CareerNode("Product Manager", "mid", (2, 5), (120_000, 180_000), ["Strategy", "Data Analysis", "Stakeholder Mgmt"]),
            CareerNode("Senior PM", "senior", (5, 8), (160_000, 250_000), ["Product Strategy", "Cross-functional Leadership"]),
            CareerNode("Group PM", "staff_principal", (8, 12), (200_000, 330_000), ["Portfolio Management", "Org Influence"]),
        ],
        "management_track": [
            CareerNode("Product Manager", "mid", (2, 5), (120_000, 180_000), ["Strategy"]),
            CareerNode("Senior PM", "senior", (5, 8), (160_000, 250_000), ["Leadership"]),
            CareerNode("Director of Product", "executive", (8, 12), (200_000, 350_000), ["Org Strategy"]),
            CareerNode("VP of Product", "executive", (12, 20), (280_000, 500_000), ["Executive Leadership"]),
        ],
        "specialist_track": [
            CareerNode("PM (Technical)", "mid", (2, 5), (130_000, 190_000), ["Technical Depth"]),
            CareerNode("Senior Technical PM", "senior", (5, 10), (170_000, 270_000), ["Platform Strategy"]),
        ],
    },
}

_MANAGEMENT_SIGNALS = {"led", "managed", "mentored", "hired", "coached", "directed", "oversaw", "built team"}
_SPECIALIST_SIGNALS = {"research", "published", "patent", "phd", "deep expertise", "specialized"}


def _find_current_node(yoe: float, ladder: list[CareerNode]) -> int:
    for i, node in enumerate(ladder):
        if node.typical_yoe[0] <= yoe <= node.typical_yoe[1] + 2:
            return i
    return min(len(ladder) - 1, max(0, int(yoe / 3)))


def simulate_career(resume: Resume) -> CareerSimulation:
    domain = resume.primary_domain or "backend"
    role_key = f"software_engineer_{domain}" if domain in ("backend", "frontend") else "software_engineer_backend"
    if role_key not in CAREER_LADDERS:
        role_key = "software_engineer_backend"

    ladders = CAREER_LADDERS[role_key]
    yoe = resume.total_yoe

    # Detect management vs specialist signals
    all_text = " ".join(b for exp in resume.work_experience for b in exp.bullets).lower()
    mgmt_score = sum(1 for s in _MANAGEMENT_SIGNALS if s in all_text)
    spec_score = sum(1 for s in _SPECIALIST_SIGNALS if s in all_text)

    paths: list[CareerPath] = []
    for track_name, nodes in ladders.items():
        idx = _find_current_node(yoe, nodes)
        remaining = nodes[idx + 1:] if idx + 1 < len(nodes) else []
        resume_skills = set()
        for sl in resume.skills.values():
            resume_skills.update(s.lower() for s in sl)
        gaps = []
        for node in remaining:
            for skill in node.skills_needed:
                if skill.lower() not in resume_skills:
                    gaps.append(skill)

        years_left = (nodes[-1].typical_yoe[1] - yoe) if nodes else 0
        paths.append(CareerPath(
            name=track_name, nodes=nodes,
            years_to_reach_end=max(0, int(years_left)),
            skills_gaps_for_path=list(dict.fromkeys(gaps)),
        ))

    # Recommend
    if mgmt_score >= 3:
        rec = "management_track"
        reasoning = "Your resume shows strong management signals (led teams, mentored, hired)"
    elif spec_score >= 2:
        rec = "specialist_track"
        reasoning = "Your resume shows specialist signals (research, deep expertise)"
    else:
        rec = "ic_track"
        reasoning = "Your resume shows strong IC contributor signals"

    ic_nodes = ladders.get("ic_track", [])
    ic_idx = _find_current_node(yoe, ic_nodes)
    current = ic_nodes[ic_idx] if ic_idx < len(ic_nodes) else ic_nodes[-1] if ic_nodes else CareerNode("Engineer", "mid", (0, 5), (100_000, 150_000), [])

    next_2yr = ic_nodes[min(ic_idx + 1, len(ic_nodes) - 1)] if ic_nodes else current
    next_5yr = ic_nodes[min(ic_idx + 2, len(ic_nodes) - 1)] if ic_nodes else current

    return CareerSimulation(
        current_position=current, paths=paths,
        recommended_path=rec, reasoning=reasoning,
        likely_title_2yr=next_2yr.title,
        likely_salary_2yr=next_2yr.typical_salary_range,
        skills_to_develop_2yr=next_2yr.skills_needed[:3],
        likely_title_5yr=next_5yr.title,
        likely_salary_5yr=next_5yr.typical_salary_range,
        skills_to_develop_5yr=next_5yr.skills_needed[:3],
    )
