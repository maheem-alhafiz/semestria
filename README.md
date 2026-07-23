# UManitoba Course Planner

A Coursicle-inspired academic planning app for University of Manitoba students:
search courses, understand linked lecture/lab sections, build conflict-free
semester schedules, and maintain multiple alternative multi-semester degree
plans.

Aurora is **never** queried live on a student's behalf. A separate importer
script pulls from Aurora's public, anonymous `/searchResults` endpoint on a
schedule and writes normalized data into our own Postgres database, which is
what the app actually serves from.

## Stack

| Layer     | Choice                                             |
|-----------|-----------------------------------------------------|
| Frontend  | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Backend   | FastAPI + SQLAlchemy 2.0 + Alembic                  |
| Database  | PostgreSQL 16                                       |
| Importer  | Standalone Python script (httpx), run on a schedule |

## Repo layout

```
umanitoba-planner/
├── backend/           FastAPI app, ORM models, importer, tests
├── frontend/           Next.js app
└── docker-compose.yml  Local Postgres for development
```

See `backend/app/README` equivalents (added in later phases) for deeper
per-module notes as they're built out.

## Local setup (run the full MVP)

1. **Database:**
   ```bash
   docker compose up -d
   ```
   Starts Postgres on `localhost:5432` with credentials matching `backend/.env.example`.

2. **Backend:**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements-dev.txt
   cp .env.example .env
   alembic revision --autogenerate -m "create initial schema"
   alembic upgrade head
   uvicorn app.main:app --reload
   ```
   Visit `http://localhost:8000/health` to confirm it's running, or
   `http://localhost:8000/docs` for interactive API docs.

3. **Import some course data** (in a second terminal, same venv):
   ```bash
   python -m app.importer.run_importer --terms 202690 --verbose
   ```
   Replace `202690` with whatever term code you want (see
   `app/importer/mapper.py::decode_term_description` for the code convention).
   Read the note in `app/importer/aurora_client.py` first -- the endpoint
   paths follow the standard Banner 9 convention but haven't been verified
   against the live aurora.umanitoba.ca host.

4. **Frontend** (in a third terminal):
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   npm run dev
   ```
   Visit `http://localhost:3000` — select a term, search for a course,
   add a few to your bucket, and hit **Generate Schedules**.

## API endpoints

| Method | Path                        | Purpose                                      |
|--------|-----------------------------|-----------------------------------------------|
| GET    | `/api/v1/terms`             | List all imported terms                      |
| GET    | `/api/v1/courses`           | Search courses (`term_code` required, `q` optional free-text) |
| POST   | `/api/v1/schedules/generate`| Generate every valid, conflict-free schedule for a term + course list |

Full interactive docs (request/response schemas, try-it-out) at `/docs` once the backend is running.

## Project phases

1. ✅ Project setup & folder architecture
2. ✅ Relational database models & migrations
3. ✅ Aurora bulk data importer script
4. ✅ Core scheduling / constraint-satisfaction engine (linking resolved relationally at import time, not parsed at schedule time -- see `app/importer/link_resolver.py`)
5. ✅ API endpoints & frontend wiring (search, schedule builder)

Future (designed for, not yet built): multi-semester degree plans (multiple
saved Plan A / Plan B style scenarios), prerequisite checking, degree
requirement tracking, GPA planning, workload balancing.
