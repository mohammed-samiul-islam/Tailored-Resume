"""Job analyze, list."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import get_db
from api.deps import get_current_user
from api.schemas import JobAnalyzeRequest, JobListItem
from models.user import User
from models.job import Job
from ai.job_analyzer import analyze_job_description

router = APIRouter(prefix="/job", tags=["job"])


@router.post("/analyze", response_model=JobListItem)
async def analyze_job(
    body: JobAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.job_text or len(body.job_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description must be at least 50 characters",
        )
    analysis = analyze_job_description(body.job_text)
    job = Job(
        user_id=user.id,
        job_text=body.job_text.strip(),
        parsed_keywords=analysis.model_dump(),
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return JobListItem.model_validate(job)


@router.get("/list", response_model=list[JobListItem])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()))
    return [JobListItem.model_validate(j) for j in res.scalars().all()]


@router.get("/{job_id}", response_model=JobListItem)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobListItem.model_validate(job)
