# Tailored Resume

**Resumes tailored to every job.**  
Upload a master resume, paste a job description, get an ATS-optimized resume. We **aim for a score of 90+** and show you exactly what’s missing. No invented experience — every claim is traceable to your resume.

## Stack

- **Frontend:** Next.js 14, TypeScript, Tailwind, React Query
- **Backend:** FastAPI, PostgreSQL (async), Pydantic
- **AI:** OpenAI (job analysis, resume generation), sentence-transformers (skill matching), pdfplumber/python-docx (parsing), WeasyPrint (PDF export)

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY, OPENAI_API_KEY
```

Create a PostgreSQL database (e.g. `tailored_resume`) and set `DATABASE_URL`:

```text
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tailored_resume
```

Run the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

If `npm install` failed earlier (e.g. cache permission), fix npm cache or run from a different user:

```bash
cd frontend
npm install
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 if needed
npm run dev
```

Open http://localhost:3000 — sign up, upload a resume (PDF or DOCX, max 4MB), paste a job description, then generate and download your tailored resume (DOCX/PDF).

### Tests

**Backend** (from `backend/`):

```bash
source .venv/bin/activate
pytest tests/ -v
```

**Frontend** (from `frontend/`):

```bash
npm test
```

### Local testing (no PostgreSQL)

The backend defaults to **SQLite** so you can run without Docker or PostgreSQL:

1. **Backend:** Use Python 3.11 or 3.12 (3.14 may need Xcode license for some deps). From `backend/`:
   ```bash
   python3.12 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   # .env already has DATABASE_URL=sqlite+aiosqlite:///./tailored_resume.db
   uvicorn main:app --reload --port 8000
   ```
2. **Frontend:** If `npm install` hits cache permission errors, use a temp cache:
   ```bash
   cd frontend && npm install --cache /tmp/npm-cache-resumebuilder && npm run dev
   ```
3. Open **http://localhost:3000** and **http://localhost:8000/docs** for the API.

## Project structure

```text
Tailored Resume/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── api/                 # auth, resume, job routes
│   ├── core/                # config, security (JWT)
│   ├── database/            # async SQLAlchemy, models
│   ├── models/              # User, Resume, Job, GeneratedResume
│   ├── services/            # pipeline (parse → analyze → match → generate → score → format)
│   └── ai/                  # resume_parser, job_analyzer, skill_matcher, resume_generator, ats_scorer, resume_formatter
├── frontend/
│   ├── app/                 # pages (login, register, dashboard)
│   ├── components/
│   ├── hooks/
│   ├── services/            # api client
│   └── utils/
├── PROJECT_SPEC.md
└── README.md
```

## Environment

**Backend (`.env`):**

- `DATABASE_URL` — PostgreSQL async URL
- `SECRET_KEY` — JWT secret (e.g. `openssl rand -hex 32`)
- `OPENAI_API_KEY` — for job analysis and resume generation
- `UPLOAD_DIR` — default `uploads` (relative to backend root)
- `MAX_UPLOAD_BYTES` — default 4MB; only **PDF and DOCX** are allowed

**Frontend (`.env.local`):**

- `NEXT_PUBLIC_API_URL` — default `http://localhost:8000`

## Features

- **Auth:** Register / login (JWT)
- **Resume upload:** PDF or DOCX only, max 4MB; parsed into structured JSON
- **Job analysis:** Paste job description → extract role, skills, keywords
- **Skill matching:** Embeddings + cosine similarity (resume vs job)
- **Resume generation:** LLM rewrites with job keywords (truthful only; no invented experience). Section order and length follow US norms (1 page &lt;10 yrs, up to 2 pages 10+).
- **ATS score:** Conservative score + missing keywords; we always deliver the best resume we can (aim for 90+).
- **Export:** DOCX (always), PDF (when WeasyPrint is available)

## Notes

- **WeasyPrint:** PDF export needs WeasyPrint (and system libs on some OS). If PDF fails, DOCX is always generated.
- **Sentence-transformers:** First skill-match request may be slower (model download).
- **npm:** If you see `EEXIST` / permission errors during `npm install`, try `npm cache clean --force` or run from a directory with correct permissions.
