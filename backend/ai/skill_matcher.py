"""Match resume skills to job skills using embeddings (or keyword fallback)."""
from __future__ import annotations

from ai.schemas import ParsedResume, JobAnalysis, SkillMatchResult


def _normalize(s: str) -> str:
    return s.lower().strip()


def _match_keyword_fallback(resume: ParsedResume, job: JobAnalysis) -> SkillMatchResult:
    """Fallback when sentence-transformers is not installed: exact/substring match."""
    job_skills = list(dict.fromkeys(job.required_skills + job.keywords))[:50]
    resume_skills = list(dict.fromkeys(resume.skills))[:100]
    resume_lower = {_normalize(rs): rs for rs in resume_skills}
    if not job_skills:
        return SkillMatchResult(matched_skills=resume_skills[:20], missing_skills=[], match_scores={})
    if not resume_skills:
        return SkillMatchResult(matched_skills=[], missing_skills=job_skills, match_scores={})

    matched: list[str] = []
    missing: list[str] = []
    match_scores: dict[str, float] = {}

    for js in job_skills:
        jn = _normalize(js)
        best_score = 0.0
        best_resume_skill: str | None = None
        for rs in resume_skills:
            rn = _normalize(rs)
            if jn == rn:
                score = 1.0
            elif jn in rn or rn in jn:
                score = 0.7
            else:
                score = 0.0
            if score > best_score:
                best_score = score
                best_resume_skill = rs
        match_scores[js] = best_score
        if best_score >= 0.5 and best_resume_skill and best_resume_skill not in matched:
            matched.append(best_resume_skill)
        else:
            missing.append(js)

    return SkillMatchResult(
        matched_skills=matched,
        missing_skills=missing,
        match_scores=match_scores,
    )


def match_skills(resume: ParsedResume, job: JobAnalysis) -> SkillMatchResult:
    job_skills = list(dict.fromkeys(job.required_skills + job.keywords))[:50]
    resume_skills = list(dict.fromkeys(resume.skills))[:100]
    if not job_skills:
        return SkillMatchResult(matched_skills=resume_skills[:20], missing_skills=[], match_scores={})
    if not resume_skills:
        return SkillMatchResult(matched_skills=[], missing_skills=job_skills, match_scores={})

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return _match_keyword_fallback(resume, job)

    _model: SentenceTransformer | None = None

    def _get_model() -> SentenceTransformer:
        nonlocal _model
        if _model is None:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model

    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        a = np.asarray(a, dtype=float).flatten()
        b = np.asarray(b, dtype=float).flatten()
        if a.size != b.size or np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    model = _get_model()
    job_emb = model.encode(job_skills)
    resume_emb = model.encode(resume_skills)
    if job_emb.ndim == 1:
        job_emb = job_emb.reshape(1, -1)
    if resume_emb.ndim == 1:
        resume_emb = resume_emb.reshape(1, -1)

    threshold = 0.4
    matched = []
    missing = []
    match_scores = {}
    for j, js in enumerate(job_skills):
        best_score = 0.0
        best_resume_skill = None
        for r, rs in enumerate(resume_skills):
            sim = cosine_similarity(job_emb[j], resume_emb[r])
            if sim > best_score:
                best_score = sim
                best_resume_skill = rs
        match_scores[js] = best_score
        if best_score >= threshold and best_resume_skill:
            if best_resume_skill not in matched:
                matched.append(best_resume_skill)
        else:
            missing.append(js)

    return SkillMatchResult(
        matched_skills=matched,
        missing_skills=missing,
        match_scores=match_scores,
    )
