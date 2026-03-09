"""Shared Pydantic schemas for AI pipeline."""
from pydantic import BaseModel


class SkillCategory(BaseModel):
    category: str  # e.g. "Languages", "Frameworks", "Cloud & Tools"
    items: list[str] = []


class ExperienceItem(BaseModel):
    title: str
    company: str
    location: str = ""
    duration: str | None = None
    bullets: list[str] = []


class ProjectItem(BaseModel):
    name: str
    description: str = ""
    bullets: list[str] = []
    tech: list[str] = []


class EducationItem(BaseModel):
    degree: str
    institution: str
    year: str | None = None


class ParsedResume(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    summary: str = ""
    skills: list[str] = []
    skill_categories: list[SkillCategory] = []
    experience: list[ExperienceItem] = []
    projects: list[ProjectItem] = []
    education: list[EducationItem] = []


class JobAnalysis(BaseModel):
    role: str = ""
    required_skills: list[str] = []
    keywords: list[str] = []
    responsibilities: list[str] = []


class SkillMatchResult(BaseModel):
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    match_scores: dict[str, float] = {}


class ATSScoreResult(BaseModel):
    score: float  # 0-100
    breakdown: dict[str, float] = {}
    missing_keywords: list[str] = []
