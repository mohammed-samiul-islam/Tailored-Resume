"""AI modules: schemas, skill matcher fallback, ats_scorer."""
import pytest

from ai.schemas import ParsedResume, JobAnalysis, SkillMatchResult, ExperienceItem, EducationItem
from ai.skill_matcher import match_skills, _match_keyword_fallback
from ai.ats_scorer import score_resume


def test_parsed_resume_schema():
    r = ParsedResume(name="Jane", skills=["Python"], experience=[])
    assert r.name == "Jane"
    assert r.skills == ["Python"]


def test_skill_match_keyword_fallback():
    resume = ParsedResume(skills=["Python", "React"])
    job = JobAnalysis(required_skills=["Python", "AWS"], keywords=["python", "aws"])
    result = _match_keyword_fallback(resume, job)
    assert "Python" in result.matched_skills or "python" in result.matched_skills
    assert "AWS" in result.missing_skills or "aws" in result.missing_skills


def test_skill_match_empty_job():
    resume = ParsedResume(skills=["Python"])
    job = JobAnalysis(required_skills=[], keywords=[])
    result = match_skills(resume, job)
    assert result.matched_skills == ["Python"]
    assert result.missing_skills == []


def test_ats_score():
    resume = ParsedResume(
        name="Dev",
        summary="I am a developer",
        skills=["Python", "React"],
        experience=[ExperienceItem(title="Engineer", company="Co", bullets=["Did things"])],
        education=[EducationItem(degree="BS", institution="U", year="2020")],
    )
    job = JobAnalysis(required_skills=["Python"], keywords=["python", "react"])
    skill_match = SkillMatchResult(matched_skills=["Python", "React"], missing_skills=["AWS"], match_scores={})
    result = score_resume(resume, job, skill_match)
    assert 0 <= result.score <= 100
    assert "keyword_coverage" in result.breakdown
    assert "skill_match" in result.breakdown
