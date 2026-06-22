# Land It — Deployment Guide (100% Free)

Stack: **Supabase** (DB + Auth) · **Render** (backend) · **Vercel** (frontend)

---

## Step 1 — Supabase setup (5 min)

1. Go to https://supabase.com and create a free account + new project.
2. In the SQL editor (left sidebar), paste and run the entire file:
   `supabase/migrations/001_initial.sql`
3. Go to **Settings → API** and copy:
   - Project URL → `SUPABASE_URL`
   - `anon` public key → `SUPABASE_ANON_KEY`
   - `service_role` secret key → `SUPABASE_SERVICE_KEY`
4. Enable **Google OAuth** (free):
   - Supabase dashboard → Authentication → Providers → Google → Enable
   - Create a Google OAuth app at https://console.cloud.google.com (free)
   - Copy Client ID + Secret back into Supabase
   - Authorized redirect URI: `https://<your-project>.supabase.co/auth/v1/callback`
5. (Optional) Enable **GitHub OAuth** the same way via GitHub → Settings → Developer Apps.

---

## Step 2 — Backend on Render (5 min)

1. Push this repo to GitHub.
2. Go to https://render.com → New Web Service → connect your GitHub repo.
3. Render auto-detects `render.yaml`. Set these environment variables in the dashboard:
   ```
   ANTHROPIC_API_KEY      = sk-ant-...
   SUPABASE_URL           = https://xxxx.supabase.co
   SUPABASE_ANON_KEY      = eyJ...
   SUPABASE_SERVICE_KEY   = eyJ...
   CORS_ORIGINS           = https://your-app.vercel.app
   ENVIRONMENT            = production
   DEBUG                  = false
   ```
4. Deploy. Your backend URL will be: `https://landit-backend.onrender.com`

> Note: Free Render services sleep after 15 min of inactivity. First request after sleep takes ~30 sec.

---

## Step 3 — Frontend on Vercel (3 min)

1. Go to https://vercel.com → New Project → import your GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add these environment variables in Vercel:
   ```
   VITE_SUPABASE_URL      = https://xxxx.supabase.co
   VITE_SUPABASE_ANON_KEY = eyJ...
   VITE_API_URL           = https://landit-backend.onrender.com
   ```
4. Deploy. Your app URL will be: `https://land-it.vercel.app`

---

## Step 4 — Final wiring

- In Render, update `CORS_ORIGINS` to your exact Vercel URL.
- In Supabase → Authentication → URL Configuration:
  - **Site URL**: `https://land-it.vercel.app`
  - **Redirect URLs**: `https://land-it.vercel.app/auth/callback`
- Redeploy backend if CORS_ORIGINS changed.

---

## Local development

```bash
# Backend
cp .env.example .env        # fill in your Supabase keys
pip install -e .
python -m uvicorn backend.main:app --port 8000

# Frontend
cd frontend
cp .env.example .env        # fill in VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
npm install
npm run dev
```
