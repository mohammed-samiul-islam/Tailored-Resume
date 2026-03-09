"""ATS score from keyword coverage, skill match, experience relevance, formatting."""
from ai.schemas import ParsedResume, JobAnalysis, SkillMatchResult, ATSScoreResult


WEIGHT_KEYWORD = 0.35
WEIGHT_SKILL = 0.25
WEIGHT_EXPERIENCE = 0.25
WEIGHT_FORMATTING = 0.15


def score_resume(
    resume: ParsedResume,
    job: JobAnalysis,
    skill_match: SkillMatchResult,
) -> ATSScoreResult:
    job_keywords = set(s.lower() for s in job.required_skills + job.keywords)
    if not job_keywords:
        return ATSScoreResult(
            score=70.0,
            breakdown={
                "keyword_coverage": 70.0,
                "skill_match": 70.0,
                "experience_relevance": 70.0,
                "formatting": 100.0,
            },
            missing_keywords=[],
        )

    resume_text = _resume_to_lower_text(resume)
    resume_words = set(resume_text.split())

    # --- Keyword coverage (35%): % of job keywords found anywhere in resume ---
    found = sum(1 for k in job_keywords if _keyword_in_resume(k, resume_text, resume_words))
    keyword_score = 100.0 * (found / len(job_keywords)) if job_keywords else 100.0

    # --- Skill match (25%): from skill_matcher result ---
    total_skills = len(skill_match.matched_skills) + len(skill_match.missing_skills)
    skill_score = (
        100.0 * (len(skill_match.matched_skills) / total_skills)
        if total_skills else 100.0
    )

    # --- Experience relevance (25%): bullets + entries + keyword density in titles ---
    experience_score = _score_experience(resume, job_keywords, resume_text)

    # --- Formatting (15%): structure completeness, contact info, skill categories ---
    formatting_score = _score_formatting(resume)

    total = (
        keyword_score * WEIGHT_KEYWORD
        + skill_score * WEIGHT_SKILL
        + experience_score * WEIGHT_EXPERIENCE
        + formatting_score * WEIGHT_FORMATTING
    )
    total = round(min(100.0, max(0.0, total)), 1)

    missing = [k for k in job_keywords if not _keyword_in_resume(k, resume_text, resume_words)]
    missing = list(dict.fromkeys(missing))[:20]

    return ATSScoreResult(
        score=total,
        breakdown={
            "keyword_coverage": round(keyword_score, 1),
            "skill_match": round(skill_score, 1),
            "experience_relevance": round(experience_score, 1),
            "formatting": round(formatting_score, 1),
        },
        missing_keywords=missing,
    )


def _score_experience(resume: ParsedResume, job_keywords: set[str], resume_text: str) -> float:
    if not resume.experience:
        return 20.0

    bullet_count = sum(len(e.bullets) for e in resume.experience)
    entry_count = len(resume.experience)

    # Base: 30 pts for having experience
    base = 30.0

    # Bullet depth: up to 25 pts (diminishing returns after ~12 bullets)
    bullet_pts = min(25.0, bullet_count * 2.5)

    # Entry count: up to 15 pts (3+ entries = full credit)
    entry_pts = min(15.0, entry_count * 5.0)

    # Keyword relevance in job titles and bullets: up to 30 pts
    title_text = " ".join(e.title.lower() for e in resume.experience)
    bullet_text = " ".join(
        b.lower() for e in resume.experience for b in (e.bullets or [])
    )
    exp_text = title_text + " " + bullet_text
    exp_words = set(exp_text.split())

    kw_hits = sum(1 for k in job_keywords if _keyword_in_resume(k, exp_text, exp_words))
    kw_ratio = kw_hits / len(job_keywords) if job_keywords else 1.0
    keyword_pts = kw_ratio * 30.0

    return min(100.0, base + bullet_pts + entry_pts + keyword_pts)


def _score_formatting(resume: ParsedResume) -> float:
    score = 0.0

    # Section presence (60 pts total)
    if resume.summary and len(resume.summary.strip()) >= 30:
        score += 15.0
    elif resume.summary and resume.summary.strip():
        score += 8.0

    if resume.skills and len(resume.skills) >= 3:
        score += 15.0
    elif resume.skills:
        score += 5.0

    if resume.experience:
        score += 15.0

    if resume.education:
        score += 15.0

    # Categorized skills (10 pts)
    if resume.skill_categories and len(resume.skill_categories) >= 2:
        score += 10.0
    elif resume.skill_categories:
        score += 5.0

    # Contact completeness (15 pts)
    contact_count = sum([
        bool(resume.email),
        bool(resume.phone),
        bool(resume.linkedin),
    ])
    score += min(15.0, contact_count * 5.0)

    # Projects section (5 pts bonus)
    if resume.projects:
        score += 5.0

    # Name present (5 pts)
    if resume.name and resume.name.strip():
        score += 5.0

    return min(100.0, score)


def _resume_to_lower_text(resume: ParsedResume) -> str:
    parts = [
        resume.name,
        resume.summary,
        " ".join(resume.skills),
    ]
    if resume.skill_categories:
        for sc in resume.skill_categories:
            parts.append(sc.category)
            parts.extend(sc.items)
    for e in resume.experience:
        parts.append(e.title)
        parts.append(e.company)
        parts.extend(e.bullets)
    for p in resume.projects:
        parts.append(p.name)
        parts.append(p.description)
        parts.extend(p.bullets)
        parts.extend(p.tech)
    for e in resume.education:
        parts.append(e.degree)
        parts.append(e.institution)
    return " ".join(parts).lower()


def _keyword_in_resume(keyword: str, resume_text: str, resume_words: set[str]) -> bool:
    k = keyword.lower().strip()
    if k in resume_text:
        return True
    if " " in k:
        return k in resume_text
    if k in resume_words:
        return True
    return any(k in w or w in k for w in resume_words)
