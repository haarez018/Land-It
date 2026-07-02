# Land It — Cockpit
> Your job search, on autopilot.

Six AI agents. One Lemma pod. A command centre for students and recent
graduates who are serious about landing the right role.

Live app: https://land-it-cockpit.apps.lemma.work

Demo: https://drive.google.com/file/d/1WZ9N2B3xK7lqusAMn5sFKboajjp3h9Yk/view?usp=drive_link

Built for the Gappy AI Hackathon — AI Job Application Command Centre track.

---

## What it does

Land It replaces the chaos of spreadsheets, browser tabs, and forgotten
follow-ups with a single operational dashboard where six specialist agents
work as one team:

| Agent | What it does |
|---|---|
| **Scout** | Discovers jobs from live boards (JSearch/RapidAPI, Remotive, Arbeitnow), scores each against your resume |
| **Tailor** | Rewrites your resume for a specific JD across 22 scoring dimensions (14 ATS + 8 Standout), streams changes live |
| **Pitcher** | Drafts cover letters and cold outreach matched to your writing voice |
| **Coach** | Generates targeted interview questions from the JD, grades your answers in real time |
| **Tracker** | Monitors application pipeline, schedules follow-ups, classifies email signals |
| **Planner** | Builds weekly strategy reports, calibration dashboards, career roadmaps |

Every agent output lands in an **Approval Inbox** — nothing goes out
without a human decision. That's the Lemma philosophy made visible.

---

## Architecture

```
frontend/          React + Vite + TypeScript + Tailwind
backend/
  agents/          Scout, Tailor, Pitcher, Coach, Tracker, Planner
  api/routes/      ~89 FastAPI endpoints
  parsers/         Resume (PDF/DOCX) + JD parser, Pydantic schemas
  agents/tailor/
    weightage/     22-dimension scoring engine + company profiles
    prediction/    Bayesian callback probability (sigmoid model)
    ab_testing/    A/B test two resume versions across all dimensions
supabase/          Auth + persistent storage + migrations
```

**Stack:** FastAPI · Python · Supabase · React · Vite · TypeScript · Tailwind · Lemma SDK

---

## The 22-Dimension Scoring Engine

Every resume is scored against a job description on two axes:

**14 ATS Dimensions**

Keyword density · Outcome density · Action verb strength · Quantified
impact · Tech stack alignment · Education relevance · Job title
progression · Employment continuity · Skill depth · ATS formatting ·
Contact completeness · Role duration · Recruiter scan pattern · Credibility
anchors

**8 Standout Dimensions**

First impression · Narrative pull · Uniqueness factor · Cultural signal ·
Builder ratio · Thought leadership · Executive presence · Memorability
spike

Weights adjust dynamically across three axes: role type × seniority ×
company profile. Per-company overrides exist for Google, Meta, Stripe, and
others.

---

## Lemma Integration

The app runs on a Lemma pod (`land-it-mission-control`). Using the
`lemma-sdk` Python client:

- Agent completions write rows to pod tables (`approvals`, `agent_activity`)
- The Approval Inbox reads directly from those pod tables
- Approving or skipping a card mutates pod state via the SDK
- Pod connection status, org, and live row count are surfaced in the UI

---

## Local Setup

### With Docker (recommended)

```bash
cp .env.example .env
# fill in your API keys in .env
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Without Docker

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `.env.example` and fill in:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Powers all six agents |
| `SUPABASE_URL` | Yes | Database + auth |
| `SUPABASE_SERVICE_KEY` | Yes | Backend service access |
| `JSEARCH_API_KEY` | No | Live job search (falls back to free scrapers) |
| `LEMMA_TOKEN` | No | Lemma pod read/write |
| `LEMMA_POD_ID` | No | Pod ID for land-it-mission-control |

---

## Key Features

- **Live resume diff** — streams the rewrite word by word, heatmap updates in real time as each dimension score changes
- **Callback probability** — sigmoid-based predictor (0–100%) with Brier score calibration dashboard
- **A/B resume testing** — compare two versions across all 22 dimensions, results persisted to Supabase
- **Bias detection** — flags gendered, age, cultural, and disability bias in resume language
- **ATS system profiles** — per-system quirks for Workday, Greenhouse, Lever, and others
- **Gmail integration** — polls inbox, classifies job-related signals (rejection / interview / offer / acknowledgement)
- **Mock interview** — real-time streaming graded feedback via WebSocket with SSE fallback
- **Rate limiting** — slowapi middleware, per-endpoint limits
- **Demo seeder** — one endpoint seeds 3 resumes, 15 jobs, 12 applications for instant demo setup

---

## Tests

```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

---

## License

MIT
