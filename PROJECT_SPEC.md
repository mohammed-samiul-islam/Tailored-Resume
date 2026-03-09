# Project Spec: AI ATS Resume Builder

## 1. Project name

**Tailored Resume** — *“Resumes tailored to every job.”*

- Clear and descriptive: each resume is tailored to the target role.
- Professional and memorable.

---

## 2. Analysis & review of your brainstorming

### What’s strong

- **Clear pipeline**: Upload → Parse → Analyze job → Match skills → Generate → Optimize → Score → Export. Good separation of concerns.
- **Sensible stack**: Next.js 14, FastAPI, PostgreSQL, vector DB, LLM. Fits the problem.
- **ATS focus**: Keyword coverage, formatting rules, scoring, and gap analysis are the right levers.
- **Modular AI layer**: Parser, job analyzer, skill matcher, generator, scorer, formatter — each can be tested and swapped.
- **Structured outputs**: JSON for parsed resume and job analysis makes the pipeline deterministic and debuggable.

### Gaps and suggested updates

| Area | Your idea | Update / addition |
|------|-----------|-------------------|
| **Auth** | Not specified | Add **auth**: JWT or session-based; protect `/resume/*` and `/job/*`. |
| **LangChain** | Listed in stack | **Optional**: Use for orchestration/chaining if you want; for “parse → analyze → generate” you can do fine with direct OpenAI + your own pipeline. Keep it simple first, add LangChain only if you need agents or complex flows. |
| **Chroma** | Vector DB for skill matching | **Clarify**: Skill matching can be “embed resume skills + job skills, then cosine similarity in memory” without a DB. Use **Chroma** (or similar) when you need to store many resumes/jobs and search at scale; for MVP, in-memory is enough. |
| **File storage** | S3 or Supabase | **Recommendation**: **Supabase Storage** for MVP (auth + DB + storage in one place; simpler). Move to S3 later if you need scale or existing AWS footprint. |
| **Resume Parser** | pdfplumber, python-docx, spaCy | **Keep**. Add **fallback**: if structure is unclear, use an LLM to extract sections (e.g. “return JSON with name, skills, experience, education”) for robustness. |
| **Job analyzer** | LLM + NLP | **Specify**: One LLM call with a structured prompt (and optionally JSON mode) to get `role`, `required_skills`, `keywords`, `responsibilities`. No need for heavy NLP beyond that for MVP. |
| **ATS scorer** | Keyword coverage, skill match, etc. | **Make formula explicit**: e.g. 40% keyword coverage + 30% skill match + 20% experience relevance + 10% formatting. Return breakdown + missing keywords. |
| **API** | POST/GET listed | **Add**: `GET /resume/list`, `GET /job/list`, `GET /generated/:id` (or similar) for dashboard; optional `DELETE` for cleanup. |
| **Errors & limits** | Not specified | **Add**: Rate limiting, max file size (e.g. 5MB), and clear error responses (e.g. 413, 422 with message). |
| **Security** | Not specified | **Add**: Validate file types (PDF/DOCX only); scan for macros in DOCX; don’t execute user content. |

---

## 3. Final architecture (updated)

```
Frontend (Next.js 14)
       │
       ▼
FastAPI Backend (auth, rate limit, validation)
       │
       ▼
AI Processing Layer
       │
  ┌────┼────────────────────────────────────┐
  ▼    ▼                                    ▼
Resume Parser    Job Description Analyzer   (optional: Chroma for multi-resume search)
  │    │
  └────┼────────────────────────────────────┘
       ▼
Skill Matching Engine (embeddings + cosine similarity)
       ▼
Resume Generator (LLM — truthful, keyword-aware)
       ▼
ATS Optimization (sections, no tables/graphics)
       ▼
ATS Scoring Engine (score + missing keywords)
       ▼
Resume Formatter (PDF / DOCX)
       ▼
Database + File Storage (PostgreSQL + Supabase Storage)
```

- **Chroma**: Introduce when you have “search across my resumes” or “match me to jobs”; for single-resume vs one job, in-memory similarity is enough.

---

## 4. Tech stack (final)

| Layer | Choice | Why |
|-------|--------|-----|
| **Frontend** | Next.js 14, TypeScript, Tailwind, ShadCN UI, React Query | App Router, type safety, fast UI, clean server state. |
| **Backend** | FastAPI, Pydantic | Async, automatic docs, validation. |
| **AI** | OpenAI API, sentence-transformers | LLM for parsing/generation; embeddings for skill match. |
| **Orchestration** | Direct Python pipeline (no LangChain for v1) | Simpler, fewer dependencies; add LangChain later if needed. |
| **Vector** | In-memory for MVP; Chroma when scaling | Keeps MVP simple. |
| **Database** | PostgreSQL | Reliable, good for JSON (parsed_json, etc.). |
| **Storage** | Supabase Storage (MVP) | Easiest with Supabase Auth/DB; S3 later if needed. |
| **Auth** | Supabase Auth or JWT (FastAPI) | Required for “my resumes / my jobs”. |

---

## 5. Core AI modules (final)

- **Resume Parser**: pdfplumber + python-docx; optional LLM fallback for messy layouts. Output: your JSON (name, skills, experience, projects, education).
- **Job Description Analyzer**: One LLM call → structured output (role, required_skills, keywords, responsibilities).
- **Skill Matching Engine**: sentence-transformers embeddings; cosine similarity; return matched_skills, missing_skills, optional strength scores.
- **Resume Generator**: OpenAI; rewrite bullets to be truthful + keyword-rich; same sections (Summary, Skills, Experience, Projects, Education).
- **ATS Optimization**: Enforce section order and plain formatting (no tables/columns/graphics).
- **ATS Scoring Engine**: Weighted score (e.g. 40/30/20/10); return score + missing keywords.
- **Resume Formatter**: python-docx for DOCX; WeasyPrint (or docx→PDF) for PDF.

---

## 6. Database schema (unchanged, with one addition)

- **users**: id, email, password (or auth provider id), created_at
- **resumes**: id, user_id, file_url, parsed_json, created_at
- **jobs**: id, user_id, job_text, parsed_keywords, created_at
- **generated_resumes**: id, resume_id, job_id, optimized_json, ats_score, file_url, created_at

Add **created_at** on **generated_resumes** for “recent builds” and versioning.

---

## 7. API endpoints (final)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /auth/register | Register (if not using Supabase only). |
| POST | /auth/login | Login / get JWT. |
| POST | /resume/upload | Upload PDF/DOCX; validate type/size. |
| POST | /resume/parse | Trigger parse (or do it on upload). |
| GET | /resume/list | List user’s resumes. |
| POST | /job/analyze | Submit job text; return parsed keywords. |
| GET | /job/list | List user’s jobs. |
| POST | /resume/generate | resume_id + job_id → run pipeline, save to generated_resumes. |
| GET | /resume/score | Get ATS score (and breakdown) for a generated resume. |
| GET | /resume/download | Download PDF or DOCX. |
| GET | /generated/:id | Get one generated resume metadata + score. |

---

## 8. Folder structure (final)

```
Tailored Resume/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── services/
│   └── utils/
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── resume.py
│   │   └── job.py
│   ├── services/
│   ├── models/
│   ├── database/
│   ├── ai/
│   │   ├── resume_parser.py
│   │   ├── job_analyzer.py
│   │   ├── skill_matcher.py
│   │   ├── resume_generator.py
│   │   ├── ats_scorer.py
│   │   └── resume_formatter.py
│   └── core/
│       ├── config.py
│       └── security.py
├── PROJECT_SPEC.md
└── README.md
```

---

## 9. Processing pipeline (unchanged intent)

1. User uploads resume → validate → store → parse (or on first use).
2. User pastes job description → analyze → store.
3. User clicks “Generate” (resume + job) → skill match → LLM generate → ATS optimize → score → format → save.
4. User views score + missing keywords; downloads PDF/DOCX.

---

## 10. Advanced features (priority for “impressive”)

1. **ATS score dashboard** — Score + breakdown + missing keywords (must-have).
2. **Keyword gap analysis** — List missing skills/keywords with suggestions (must-have).
3. **Resume preview** — In-browser preview before download (high).
4. **Bullet improvement** — “Improve this bullet” for a single line (high).
5. **Resume versioning** — Keep history of generated resumes per resume+job (medium).
6. **Multi-format export** — PDF + DOCX in one flow (already in scope).

---

## 11. Summary: what we decided and why

- **Name**: **Tailored Resume** — clear, professional, memorable.
- **Single pipeline**: One master resume + one job description → one tailored resume + score + export; no over-engineering.
- **Auth and storage**: Auth from day one; Supabase (Storage + optional Auth/DB) for faster MVP.
- **Chroma**: Deferred until we need search over many resumes/jobs; MVP uses in-memory similarity.
- **LangChain**: Omitted in v1; direct OpenAI + your modules are enough and easier to debug.
- **Parser**: Rule-based (pdfplumber, python-docx) plus optional LLM fallback for hard layouts.
- **Scoring**: Transparent weighted formula and missing keywords so the user can improve.
- **APIs**: REST with clear list/get/upload/generate/download/score; ready for a dashboard.
- **Security**: File validation, size limits, and no execution of user content.

This keeps the project **production-quality**, **modular**, and **explainable**, without extra complexity until you need it.

---

## 12. Finalized product decisions (post-brainstorm)

### Truthfulness & missing skills
- We **only add keywords** that can be truthfully inferred from the user’s resume (experience, education, projects).
- For keywords the user has **no experience with**: we do **not** add them (no false resume). We tell the user: learn that skill and add it to your master resume, then regenerate.
- **No invented experience or hallucination.** Every claim on the tailored resume must be traceable to the master resume.

### Delivery & scoring
- We **always deliver** the best resume we generate; we never refuse. User gets a usable file every time.
- We **aim for** ATS score 90+ (landing page says “aim for 90+”, not a guarantee).
- **ATS scorer**: Conservative, no inflation — when we show 90, it is meaningful.
- **Safety cap**: Max **10 attempts** per generation run (cost/latency control).

### UX copy
- **Missing keywords** (one list): “We didn’t add these because they weren’t on your resume. Learn these skills and add them to your master resume, then regenerate to aim for 90+.”
- When score &lt; 90: “This is the best match we could create from your current master resume.”
- **Every delivered resume**: “We’ve tailored your resume for this job and included relevant keywords from your experience.”

### Format & length
- **Resume length**: US standard — **1 page** if &lt;10 years experience, **up to 2 pages** if 10+ years.
- **Section order**: Decided by the LLM per job to maximize ATS score (no fixed template).

### Files & limits
- **Supported file types**: DOCX and PDF only.
- **Max file size**: 4MB.

### World-class checklist
- **Single source of truth**: One master resume → many tailored versions; UX makes this clear.
- **Traceability**: Every claim on the tailored resume must be traceable to the master (rephrase/reorder/emphasize OK; new facts not OK).
- **Security & privacy**: Resumes are PII; secure upload and storage; no training on user data; optional account + data deletion.
- **ATS reality**: We provide a strict, transparent proxy score; real ATS systems vary; we optimize for keyword coverage and structure.
- **Export**: ATS-friendly DOCX/PDF (no complex tables/graphics that break parsers); clear structure for accessibility.
- **Errors**: Clear, actionable messages (e.g. “PDF or DOCX only, max 4MB”); rate limiting to protect resources.
