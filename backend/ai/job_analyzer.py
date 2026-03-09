"""Extract role, skills, keywords, and responsibilities from job description."""
import json
import re

from openai import OpenAI

from ai.schemas import JobAnalysis
from core.config import get_settings


def analyze_job_description(job_text: str) -> JobAnalysis:
    settings = get_settings()
    if not settings.openai_api_key:
        return _analyze_fallback(job_text)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = """Analyze this job description and extract the following as JSON. Return ONLY valid JSON, no markdown.
{
  "role": "job title / role name",
  "required_skills": ["skill1", "skill2"],
  "keywords": ["keyword1", "keyword2"],
  "responsibilities": ["responsibility 1", "responsibility 2"]
}

Job description:
"""
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt + job_text[:8000]}],
            temperature=0,
        )
        content = (r.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content).replace("```", "").strip()
        data = json.loads(content)
        return JobAnalysis(
            role=data.get("role", ""),
            required_skills=data.get("required_skills", []),
            keywords=data.get("keywords", []),
            responsibilities=data.get("responsibilities", []),
        )
    except Exception:
        return _analyze_fallback(job_text)


def _analyze_fallback(job_text: str) -> JobAnalysis:
    """Simple keyword extraction when no API key."""
    text_lower = job_text.lower()
    common_skills = [
        "python", "javascript", "react", "typescript", "node", "sql", "aws",
        "docker", "kubernetes", "rest", "api", "git", "agile", "leadership",
        "communication", "problem solving", "analytics", "machine learning",
    ]
    found = [s for s in common_skills if s in text_lower]
    role = "Unknown Role"
    for line in job_text.splitlines():
        line = line.strip()
        if line and len(line) < 100 and ("engineer" in line.lower() or "developer" in line.lower() or "manager" in line.lower()):
            role = line
            break
    return JobAnalysis(role=role, required_skills=found, keywords=found[:15], responsibilities=[])
