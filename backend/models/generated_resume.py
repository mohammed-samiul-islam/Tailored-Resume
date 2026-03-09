from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON

from database.base import Base


class GeneratedResume(Base):
    __tablename__ = "generated_resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    optimized_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resume = relationship("Resume", back_populates="generated_resumes")
    job = relationship("Job", back_populates="generated_resumes")
