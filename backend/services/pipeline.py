"""Full pipeline: parse (if needed), analyze job (if needed), match -> generate -> score -> format."""
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ai.resume_parser import parse_resume
from ai.job_analyzer import analyze_job_description
from ai.skill_matcher import match_skills
from ai.resume_generator import generate_optimized_resume
from ai.ats_scorer import score_resume
from ai.resume_formatter import build_docx, build_pdf
from ai.schemas import ParsedResume, JobAnalysis

from models.resume import Resume
from models.job import Job
from models.generated_resume import GeneratedResume
from core.config import get_settings

logger = logging.getLogger(__name__)


async def run_generate_pipeline(
    db: AsyncSession,
    resume_id: int,
    job_id: int,
    user_id: int,
    upload_dir: Path,
) -> GeneratedResume:
    settings = get_settings()
    res = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id))
    resume_row = res.scalar_one_or_none()
    if not resume_row:
        raise ValueError("Resume not found")
    job_res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    job_row = job_res.scalar_one_or_none()
    if not job_row:
        raise ValueError("Job not found")

    resume_data: ParsedResume
    if resume_row.parsed_json:
        resume_data = ParsedResume.model_validate(resume_row.parsed_json)
    else:
        file_path = upload_dir / resume_row.file_url.replace("uploads/", "").lstrip("/")
        if not file_path.exists():
            file_path = Path(resume_row.file_url)
        try:
            resume_data = parse_resume(file_path, use_llm_fallback=True)
        except Exception as e:
            logger.warning("Resume parse failed in pipeline for %s: %s", file_path, e)
            resume_data = ParsedResume(name="Candidate", summary="", skills=[], experience=[], projects=[], education=[])
        resume_row.parsed_json = resume_data.model_dump()

    job_data: JobAnalysis
    if job_row.parsed_keywords:
        job_data = JobAnalysis.model_validate(job_row.parsed_keywords)
    else:
        job_data = analyze_job_description(job_row.job_text)
        job_row.parsed_keywords = job_data.model_dump()

    skill_match = match_skills(resume_data, job_data)
    min_score = settings.min_ats_score
    max_attempts = 10  # Safety cap per generation run
    current = resume_data
    best_optimized = resume_data
    best_result = None

    for attempt in range(max_attempts):
        improvement_feedback = None
        if attempt > 0 and best_result is not None:
            improvement_feedback = (
                f"Current ATS score: {best_result.score:.1f}/100. Target: {min_score}+. "
                f"Missing keywords to add naturally where truthful: {', '.join(best_result.missing_keywords[:15])}. "
                "Weave these into summary, skills, and experience bullets. Do not invent facts."
            )
        current = generate_optimized_resume(
            current, job_data, skill_match, improvement_feedback=improvement_feedback
        )
        result = score_resume(current, job_data, skill_match)
        if best_result is None or result.score > best_result.score:
            best_optimized = current
            best_result = result
        if result.score >= min_score:
            break

    # Always deliver the best we have — user gets a usable resume every time
    optimized = best_optimized
    ats_result = best_result if best_result is not None else score_resume(optimized, job_data, skill_match)

    docx_bytes = build_docx(optimized)
    upload_dir = Path(upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    base = f"generated_{resume_id}_{job_id}_{job_row.created_at.timestamp():.0f}"
    docx_path = upload_dir / f"{base}.docx"
    docx_path.write_bytes(docx_bytes)
    try:
        pdf_bytes = build_pdf(optimized)
        if (
            isinstance(pdf_bytes, bytes)
            and len(pdf_bytes) > 100
            and pdf_bytes.startswith(b"%PDF")
        ):
            pdf_path = upload_dir / f"{base}.pdf"
            pdf_path.write_bytes(pdf_bytes)
        else:
            logger.warning("PDF build returned empty or invalid content for %s", base)
    except Exception as e:
        logger.error("PDF build failed for %s: %s", base, e)
    file_url = f"uploads/{base}.docx"

    gen = GeneratedResume(
        resume_id=resume_id,
        job_id=job_id,
        optimized_json=optimized.model_dump(),
        ats_score=ats_result.score,
        score_breakdown=ats_result.breakdown,
        missing_keywords=ats_result.missing_keywords,
        file_url=file_url,
    )
    db.add(gen)
    await db.flush()
    await db.refresh(gen)
    return gen
