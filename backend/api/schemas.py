"""Request/response schemas for API."""
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class JobAnalyzeRequest(BaseModel):
    job_text: str


class ResumeGenerateRequest(BaseModel):
    resume_id: int
    job_id: int


class ResumeListItem(BaseModel):
    id: int
    file_url: str
    parsed_json: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    id: int
    job_text: str
    parsed_keywords: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class GeneratedResumeResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    ats_score: float | None
    score_breakdown: dict | None
    missing_keywords: list | None
    file_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True
