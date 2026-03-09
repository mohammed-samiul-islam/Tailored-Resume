"""Resume upload, parse, list, generate, score, download."""
import logging
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse, Response

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.connection import get_db
from api.deps import get_current_user
from api.schemas import ResumeListItem, ResumeGenerateRequest, GeneratedResumeResponse
from models.user import User
from models.resume import Resume
from models.generated_resume import GeneratedResume
from core.config import get_settings
from ai.resume_parser import parse_resume
from ai.resume_formatter import build_pdf
from ai.schemas import ParsedResume
from services.pipeline import run_generate_pipeline

router = APIRouter(prefix="/resume", tags=["resume"])


def _allowed_file(filename: str) -> bool:
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return ext in get_settings().allowed_resume_extensions


@router.post("/upload", response_model=ResumeListItem)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename or not _allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are allowed",
        )
    settings = get_settings()
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max {settings.max_upload_bytes // (1024*1024)}MB",
        )
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(file.filename or "upload"))
    safe_name = f"{user.id}_{os.urandom(4).hex()}_{sanitized}"
    path = upload_dir / safe_name
    if not path.resolve().is_relative_to(upload_dir):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    path.write_bytes(content)

    resume = Resume(user_id=user.id, file_url=f"uploads/{safe_name}")
    db.add(resume)
    await db.flush()
    try:
        parsed = parse_resume(path, use_llm_fallback=False)
        resume.parsed_json = parsed.model_dump()
    except Exception as e:
        logger.warning("Parse failed on upload for resume %s: %s", resume.id, e)
    await db.refresh(resume)
    return ResumeListItem.model_validate(resume)


@router.post("/parse/{resume_id}", response_model=ResumeListItem)
async def trigger_parse(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    settings = get_settings()
    path = Path(settings.upload_dir) / row.file_url.replace("uploads/", "").lstrip("/")
    if not path.exists():
        path = Path(row.file_url)
    parsed = parse_resume(path, use_llm_fallback=True)
    row.parsed_json = parsed.model_dump()
    await db.flush()
    await db.refresh(row)
    return ResumeListItem.model_validate(row)


@router.get("/list", response_model=list[ResumeListItem])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()))
    return [ResumeListItem.model_validate(r) for r in res.scalars().all()]


@router.post("/generate", response_model=GeneratedResumeResponse)
async def generate_resume(
    body: ResumeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    upload_dir = Path(settings.upload_dir).resolve()
    try:
        gen = await run_generate_pipeline(db, body.resume_id, body.job_id, user.id, upload_dir)
        return GeneratedResumeResponse.model_validate(gen)
    except ValueError as e:
        msg = str(e)
        if "below the minimum" in msg:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)


@router.get("/score/{generated_id}")
async def get_score(
    generated_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(GeneratedResume)
        .where(GeneratedResume.id == generated_id)
        .options(selectinload(GeneratedResume.resume))
    )
    gen = res.scalar_one_or_none()
    if not gen or gen.resume.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {
        "ats_score": gen.ats_score,
        "breakdown": gen.score_breakdown,
        "missing_keywords": gen.missing_keywords or [],
    }


@router.get("/generated/{generated_id}", response_model=GeneratedResumeResponse)
async def get_generated(
    generated_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(GeneratedResume)
        .where(GeneratedResume.id == generated_id)
        .options(selectinload(GeneratedResume.resume))
    )
    gen = res.scalar_one_or_none()
    if not gen or gen.resume.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return GeneratedResumeResponse.model_validate(gen)


@router.get("/download/{generated_id}")
async def download_resume(
    generated_id: int,
    format: str = "docx",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if format not in ("docx", "pdf"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Format must be 'docx' or 'pdf'")
    res = await db.execute(
        select(GeneratedResume).where(GeneratedResume.id == generated_id).options(
            selectinload(GeneratedResume.resume)
        )
    )
    gen = res.scalar_one_or_none()
    if not gen or gen.resume.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    settings = get_settings()
    upload_dir = Path(settings.upload_dir).resolve()
    base_name = gen.file_url.replace("uploads/", "").lstrip("/").replace(".docx", "")
    docx_path = upload_dir / f"{base_name}.docx"
    pdf_path = upload_dir / f"{base_name}.pdf"

    if format == "pdf":
        # Only ever return real PDF bytes — never return DOCX as PDF
        if pdf_path.exists():
            return FileResponse(str(pdf_path), filename=pdf_path.name, media_type="application/pdf")
        # Generate PDF on-the-fly from stored optimized_json so user always gets valid PDF
        try:
            resume_data = ParsedResume.model_validate(gen.optimized_json)
            pdf_bytes = build_pdf(resume_data)
            if isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 100 and pdf_bytes.startswith(b"%PDF"):
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="resume.pdf"'},
                )
        except Exception as e:
            logger.error("On-the-fly PDF generation failed for generated_id=%s: %s", generated_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF is not available for this resume. Download DOCX instead.",
        )

    if docx_path.exists():
        return FileResponse(str(docx_path), filename=docx_path.name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
