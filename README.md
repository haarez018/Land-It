# Land It

AI-powered job search copilot — scout roles, tailor resumes, draft cover letters, prep for interviews, and track everything in one place.

## Local Setup

### With Docker (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/land-it.git
cd land-it

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and DATABASE_URL at minimum

# 3. Spin up the full stack
docker compose up --build

# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

### Without Docker

**Backend**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

## Tech Stack

- **Backend** — FastAPI, Python 3.11, SQLite (dev) / Supabase (prod)
- **Frontend** — React 18, TypeScript, Vite, Tailwind CSS, Framer Motion
- **AI** — Anthropic Claude (resume tailoring, interview coaching, cover letters)
- **Job data** — JSearch (RapidAPI), Remotive, Arbeitnow
