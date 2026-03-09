"""Generate ATS-optimized resume content using LLM."""
import json
import re

from openai import OpenAI

from ai.schemas import (
    ParsedResume,
    JobAnalysis,
    SkillMatchResult,
    SkillCategory,
    ExperienceItem,
    ProjectItem,
    EducationItem,
)
from core.config import get_settings


def generate_optimized_resume(
    resume: ParsedResume,
    job: JobAnalysis,
    skill_match: SkillMatchResult,
    *,
    improvement_feedback: str | None = None,
) -> ParsedResume:
    """Rewrite resume to align with job while keeping facts truthful."""
    settings = get_settings()
    if not settings.openai_api_key:
        return resume

    client = OpenAI(api_key=settings.openai_api_key)

    job_context = (
        f"Role: {job.role}\n"
        f"Required skills: {', '.join(job.required_skills[:20])}\n"
        f"Keywords: {', '.join(job.keywords[:20])}\n"
        f"Matched skills (keep these prominent): {', '.join(skill_match.matched_skills[:15])}\n"
        f"Missing skills (weave in only if truthfully applicable): {', '.join(skill_match.missing_skills[:10])}"
    )

    resume_json = resume.model_dump_json(indent=2)

    feedback_section = ""
    if improvement_feedback:
        feedback_section = f"""
IMPORTANT - Previous attempt feedback (you MUST address this to improve ATS score):
{improvement_feedback}

"""

    prompt = f"""You are an ATS resume optimizer. Rewrite this resume to better match the job description.

TARGET ROLE: {job.role}
Tailor the entire resume toward this role. If the role is front-end or React-focused, lead with front-end skills, rewrite bullets to highlight UI/UX work, component development, and performance optimization. If the role is backend-focused, lead with backend/API skills and infrastructure work. Adapt the emphasis to the domain.

STRICT RULES (do not violate):
- Do NOT invent experience, skills, or facts. Only rephrase, reorder, and emphasize what is already in the resume. Every claim must be traceable to the source resume. No hallucination.
- Add job keywords ONLY where they are truthfully applicable given the candidate's real experience. If the candidate has no experience with a keyword, do not add it.
- US standard length: 1 page if the candidate has under 10 years of experience; up to 2 pages if 10+ years. Be concise.
- Choose section order (e.g. Summary, Skills, Experience, Projects, Education) to maximize ATS match for this specific job — reorder sections if it helps.
- Keep bullet points achievement-oriented (metrics, impact) where possible. Start each bullet with a strong action verb.
- Group skills into categories (e.g. "Languages", "Frameworks", "Cloud & Tools", "Databases") in the skill_categories field. Keep the flat skills array too for backward compatibility. Place the most job-relevant category first.
- For each experience item, include the location if known (city, state or "Remote").
- For each project, list the tech stack in the tech array.
- Preserve linkedin and github URLs from the source resume if present.
- Return ONLY valid JSON, no markdown fences.
{feedback_section}
Job context:
{job_context}

Current resume (JSON):
{resume_json}

Return the optimized resume as a single JSON object with these keys:
- name, email, phone, linkedin, github
- summary (2-3 concise sentences)
- skills (flat array of all skills for backward compat)
- skill_categories (array of {{"category": "Languages", "items": ["Python", "JavaScript"]}})
- experience (array of {{"title", "company", "location", "duration", "bullets"}})
- projects (array of {{"name", "description", "bullets", "tech"}})
- education (array of {{"degree", "institution", "year"}})
"""

    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = (r.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content).replace("```", "").strip()
        data = json.loads(content)
        return ParsedResume(
            name=data.get("name", resume.name),
            email=data.get("email", resume.email),
            phone=data.get("phone", resume.phone),
            linkedin=data.get("linkedin", resume.linkedin),
            github=data.get("github", resume.github),
            summary=data.get("summary", resume.summary),
            skills=data.get("skills", resume.skills),
            skill_categories=[
                SkillCategory(category=sc.get("category", ""), items=sc.get("items", []))
                for sc in data.get("skill_categories", [])
            ],
            experience=[
                ExperienceItem(
                    title=e.get("title", ""),
                    company=e.get("company", ""),
                    location=e.get("location", ""),
                    duration=e.get("duration"),
                    bullets=e.get("bullets", []),
                )
                for e in data.get("experience", [])
            ],
            projects=[
                ProjectItem(
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    bullets=p.get("bullets", []),
                    tech=p.get("tech", []),
                )
                for p in data.get("projects", [])
            ],
            education=[
                EducationItem(
                    degree=e.get("degree", ""),
                    institution=e.get("institution", ""),
                    year=e.get("year"),
                )
                for e in data.get("education", [])
            ],
        )
    except Exception:
        return resume
