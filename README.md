# Job Tracker — Full Project Documentation

## Overview

AI-powered job search assistant for Michael Sounhein. Scrapes IT job listings from Indeed/LinkedIn/Glassdoor via JSearch API, scores them against Michael's resume using GLM-5.1, presents them in a Linear-inspired dark UI, and learns from his rejection/apply behavior to improve future matches.

**URL:** `http://192.168.87.30:5100` (LAN) | `http://localhost:5100` (local)  
**Project path:** `~/.openclaw/workspace/projects/job-tracker/`  
**Git:** commits in main workspace repo  

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  React Frontend (Vite → dist/)                   │
│  Served by Flask as static files on port 5100    │
│  Pages: Dashboard, NewJobs, AllJobs, JobDetail,  │
│         AppliedJobs, Profile, Settings           │
└────────────────────┬────────────────────────────┘
                     │ /api/*
┌────────────────────▼────────────────────────────┐
│  Flask Backend (app.py)                          │
│  - REST API for jobs, search terms, profile      │
│  - Chat API with GLM tool calling                │
│  - Triggers scraper on demand                    │
└────────┬───────────┬───────────┬────────────────┘
         │           │           │
    ┌────▼───┐  ┌────▼───┐  ┌───▼──────┐
    │Scraper │  │Scorer  │  │ Learner  │
    │(JSearch│  │(GLM-5.1│  │(behavior │
    │ API)   │  │ via GW)│  │ analysis)│
    └────────┘  └────────┘  └──────────┘
         │           │           │
    ┌────▼───────────▼───────────▼────┐
    │  SQLite: data/jobs.db           │
    │  Tables: jobs, search_terms,    │
    │  profiles, rejection_patterns,  │
    │  blocked_companies, chat_messages│
    └─────────────────────────────────┘
```

---

## File Map

```
projects/job-tracker/
├── .env                          # Environment vars (API keys, config)
├── .venv/                        # Python 3.12 venv
├── data/
│   ├── jobs.db                   # SQLite database
│   └── last_job_summary.txt      # Last scraper run summary
├── backend/
│   ├── app.py                    # Flask API server (all routes)
│   ├── config.py                 # Configuration class
│   ├── database.py               # SQLAlchemy engine, session, init
│   ├── models.py                 # Job, SearchTerm, Profile, RejectionPattern, BlockedCompany
│   ├── models_chat.py            # ChatMessage model
│   ├── scraper.py                # JSearch API scraper
│   ├── scorer.py                 # GLM-5.1 job scoring via OpenClaw gateway
│   ├── learner.py                # Behavioral analysis (reads rejections → patterns)
│   ├── chat_tools.py             # 6 tools the AI can call during chat
│   ├── notifier.py               # Telegram notifications
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Router, sidebar, layout, collapsible
│   │   ├── api/client.js         # Axios API client
│   │   └── pages/
│   │       ├── Dashboard.jsx     # Stats overview
│   │       ├── NewJobs.jsx       # New job list with quick triage (🎯❌)
│   │       ├── AllJobs.jsx       # All jobs with filters
│   │       ├── AppliedJobs.jsx   # Applied/Will Apply jobs
│   │       ├── JobDetail.jsx     # Split view: iframe + AI chat
│   │       ├── Profile.jsx       # Resume & search preferences
│   │       └── Settings.jsx      # Settings page
│   └── dist/                     # Built static files (served by Flask)
├── scripts/
│   ├── init_db.py                # Create all tables
│   ├── run_scraper.py            # CLI scraper trigger
│   └── seed_resume.py            # Seed resume from file
└── DESIGN.md                     # UI design system (Linear-inspired)
```

---

## Database Schema

### `jobs`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Job title |
| company | TEXT | Company name |
| location | TEXT | Job location |
| remote | BOOLEAN | Remote eligible |
| url | TEXT | Link to original listing |
| description | TEXT | Full job description |
| salary_min / salary_max | INTEGER | Annual salary range |
| source | TEXT | Indeed/LinkedIn/Glassdoor |
| source_id | TEXT | Unique ID from source |
| match_score | INTEGER | 0-100 from GLM scoring |
| match_reasoning | TEXT | Why GLM gave that score |
| status | TEXT | new/will_apply/applied/interview/offer/rejected |
| rejection_reason | TEXT | Why rejected (for AI learning) |
| apply_note | TEXT | Why applying (for AI learning) |
| applied_date | DATETIME | When applied |
| found_date | DATETIME | When scraped |

### `search_terms`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| term | TEXT | Search query string |
| source | TEXT | 'user' or 'ai' |
| active | BOOLEAN | Enabled for scraping |

### `profiles`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| resume_text | TEXT | Full resume text |
| location | TEXT | Default: "Appleton, WI" |
| max_distance | INTEGER | Default: 25 miles |
| preferences | TEXT | JSON blob |

### `rejection_patterns`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| pattern | TEXT | e.g., "contract-only roles" |
| source | TEXT | 'ai' or 'user' |
| active | BOOLEAN | |

### `blocked_companies`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT | Company name |
| reason | TEXT | Why blocked |

### `chat_messages`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| job_id | INTEGER FK → jobs(id) | |
| role | TEXT | 'user' or 'assistant' |
| content | TEXT | Message text |
| created_at | DATETIME | |

---

## API Endpoints

### Jobs
- `GET /api/stats` — Dashboard stats (counts by status, top match)
- `GET /api/jobs?status=new&sort=match_score` — List jobs (filter by status, sort)
- `GET /api/jobs/<id>` — Single job details
- `PUT /api/jobs/<id>/status` — Update status `{status, note}`
- `POST /api/scrape` — Trigger scraper run

### Chat (AI Agent)
- `GET /api/jobs/<id>/chat` — Get chat history for a job
- `POST /api/jobs/<id>/chat` — Send message, get AI response with tool calling
  - Request: `{message: "..."}`
  - Response: `{id, role: "assistant", content: "...", created_at: "..."}`

### Profile & Config
- `GET/PUT /api/profile` — Resume text, location, preferences
- `GET/POST/DELETE /api/search-terms` — Manage search terms
- `GET/POST/DELETE /api/blocked-companies` — Manage blocklist

### Frontend
- `GET /*` — Serves React SPA from `frontend/dist/`

---

## AI Chat Tool Calling

The chat agent has 6 tools it can call during conversation:

1. **update_resume** — Rewrites resume text. AI crafts polished bullets.
2. **add_search_term** — Adds job title keywords to scraper.
3. **block_company** — Blocks a company from future results.
4. **add_rejection_pattern** — Adds a pattern to penalize similar jobs.
5. **update_job_status** — Changes job status from chat.
6. **update_profile** — Updates location, distance, preferences.

Tools use OpenAI-compatible function calling format. The backend loops up to 5 iterations to handle chained tool calls.

---

## Scoring Pipeline

1. **Scraper** fetches jobs from JSearch API (Indeed/LinkedIn/Glassdoor)
2. **Learner** reads rejection patterns and builds behavioral context
3. **Scorer** sends each new job + resume + behavioral context to GLM-5.1
4. GLM returns match_score (0-100) and match_reasoning
5. Match reasoning is stored and shown as AI's opening message in chat

---

## Learning Pipeline

Every scraper run:
1. GLM reads recent rejection reasons + apply notes
2. Extracts patterns: "rejects contract roles", "likes remote + MECM"
3. Stores patterns in `rejection_patterns` table
4. Adds/removes search terms based on patterns
5. Injects behavioral context into future scoring prompts

---

## Cron Jobs (Automated Scans)

| ID | Time (CDT) | Schedule |
|----|-----------|----------|
| `1ac6b0f7-...` | 7:00 AM | Daily morning scan |
| `98e83326-...` | 12:00 PM | Daily midday scan |

Each triggers `scripts/run_scraper.py` → scrapes, learns, scores, sends Telegram summary.

---

## Systemd Service

- **Unit:** `~/.config/systemd/user/job-tracker.service`
- **Working dir:** `~/.../projects/job-tracker/backend`
- **Command:** `.venv/bin/gunicorn app:app --bind 0.0.0.0:5100 --workers 2`
- **Restart:** `systemctl --user restart job-tracker`
- **Logs:** `journalctl --user -u job-tracker -f`

---

## Key Integrations

| Service | Purpose | Auth |
|---------|---------|------|
| JSearch RapidAPI | Job scraping | Key: `cea608bc...` |
| OpenClaw Gateway | GLM-5.1 proxy | `localhost:18789`, token `172663...` |
| Telegram | Notifications | Chat `-1003791430087`, topic `1965` |

---

## Design Decisions

- **Four Visual Themes & Custom Hexagon Background** — Features an interactive Theme Switcher (sidebar, mobile, settings) with custom SVG background pattern support across:
  - *Sleek Arctic (Light)*: Clean, light slate/arctic aesthetic with subtle grey/blue borders.
  - *Cyberpunk Midnight (Dark)*: Sleek dark mode with vibrant neon purple/cyan accents.
  - *Warm Honeycomb (BusyBee Light)*: Warm parchment/beige background with deep charcoal text and honey-gold/amber accents.
  - *Honey Midnight (BusyBee Dark)*: Cozy dark charcoal-brown background with honey-gold accents.
- **Alternating Premium Row Layouts** — Clean lists featuring alternating color palettes and left-accent borders computed from the company name, improving readability.
- **Single-port deployment** — Flask serves React static files (no separate dev server)
- **Progressive status buttons** — Only show actions valid for current phase
- **Auto match reasoning** — Scorer's analysis appears as AI's opening message in chat
- **Tool-calling agent** — AI can modify resume, filters, and job status directly
- **Mobile-friendly** — Responsive sidebar collapses, full-width content

---

## Build & Deploy Commands

```bash
# Frontend build
cd frontend && npm run build

# Restart backend
systemctl --user restart job-tracker

# Check logs
journalctl --user -u job-tracker -f

# Manual scraper run
.venv/bin/python scripts/run_scraper.py

# Init DB
.venv/bin/python scripts/init_db.py
```
