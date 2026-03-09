"""Extract structured data from PDF/DOCX resumes."""
from pathlib import Path
import re
import json

import pdfplumber
from docx import Document
from openai import OpenAI

from ai.schemas import ParsedResume, SkillCategory, ExperienceItem, ProjectItem, EducationItem
from core.config import get_settings


def _extract_text_from_pdf(path: Path) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def _extract_text_from_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _parse_with_regex(text: str) -> ParsedResume:
    """Rule-based extraction: look for common section headers."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else ""
    email = ""
    phone = ""
    summary = ""
    skills: list[str] = []
    skill_categories: list[SkillCategory] = []
    experience: list[ExperienceItem] = []
    projects: list[ProjectItem] = []
    education: list[EducationItem] = []

    linkedin = ""
    github = ""

    email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", text)
    if email_match:
        email = email_match.group(0)
    phone_match = re.search(r"\+?[\d\s\-().]{10,}", text)
    if phone_match:
        phone = phone_match.group(0).strip()
    linkedin_match = re.search(r"linkedin\.com/in/[\w-]+", text, re.I)
    if linkedin_match:
        linkedin = linkedin_match.group(0)
    github_match = re.search(r"github\.com/[\w-]+", text, re.I)
    if github_match:
        github = github_match.group(0)

    section = None
    current_bullets: list[str] = []
    current_title = ""
    current_company = ""
    current_duration = ""

    section_headers = {
        "summary": re.compile(r"^(professional\s+)?summary|profile|objective|about\s*$", re.I),
        "skills": re.compile(r"^(technical\s+)?skills|core\s+competencies|competencies\s*$", re.I),
        "experience": re.compile(r"^(professional\s+)?experience|work\s+experience|employment(\s+history)?\s*$", re.I),
        "projects": re.compile(r"^(key\s+)?projects|personal\s+projects\s*$", re.I),
        "education": re.compile(r"^education|academic(\s+background)?\s*$", re.I),
    }

    for line in lines:
        if not line:
            continue
        matched = False
        for sec, pattern in section_headers.items():
            if pattern.match(line):
                if section == "experience" and (current_title or current_bullets):
                    experience.append(
                        ExperienceItem(
                            title=current_title or "Role",
                            company=current_company or "",
                            duration=current_duration,
                            bullets=current_bullets,
                        )
                    )
                    current_bullets = []
                    current_title = ""
                    current_company = ""
                    current_duration = ""
                section = sec
                matched = True
                break
        if matched:
            continue

        if section == "summary":
            summary += " " + line
        elif section == "skills":
            cat_match = re.match(r"^([A-Za-z &/]+):\s*(.+)$", line)
            if cat_match:
                cat_label = cat_match.group(1).strip()
                cat_items = [s.strip() for s in re.split(r"[,;|]", cat_match.group(2)) if s.strip()]
                skill_categories.append(SkillCategory(category=cat_label, items=cat_items))
                skills.extend(cat_items)
            else:
                parts = re.split(r"[,;|]", line)
                skills.extend([p.strip() for p in parts if p.strip() and len(p.strip()) < 80])
        elif section == "experience":
            if line.startswith("\u2022") or line.startswith("•") or line.startswith("-") or re.match(r"^\d+\.", line):
                current_bullets.append(re.sub(r"^[\u2022•\-]\s*|\d+\.\s*", "", line).strip())
            else:
                if current_bullets or current_title:
                    experience.append(
                        ExperienceItem(
                            title=current_title or "Role",
                            company=current_company or "",
                            duration=current_duration,
                            bullets=current_bullets,
                        )
                    )
                    current_bullets = []
                    current_duration = ""
                # "Company — Title (Location) (Date)" format
                em_dash_match = re.match(
                    r"^(.+?)\s*[\u2014\u2013—–-]{1,2}\s*(.+?)(?:\s*\(([^)]*)\))?\s*(?:\(([^)]*\d{4}[^)]*)\))?\s*$",
                    line,
                )
                if em_dash_match:
                    current_company = em_dash_match.group(1).strip()
                    title_part = em_dash_match.group(2).strip()
                    location = em_dash_match.group(3) or ""
                    date = em_dash_match.group(4) or ""
                    current_title = title_part
                    current_duration = date.strip()
                elif " at " in line:
                    parts = line.split(" at ", 1)
                    current_title = parts[0].strip()
                    current_company = parts[1].strip()
                elif ", " in line:
                    parts = line.split(", ", 1)
                    current_title = parts[0].strip()
                    current_company = parts[1].strip()
                else:
                    current_title = line
                    current_company = ""
        elif section == "projects":
            if line.startswith("•") or line.startswith("-"):
                current_bullets.append(re.sub(r"^[•\-]\s*", "", line).strip())
            elif current_bullets:
                projects.append(ProjectItem(name=line, bullets=current_bullets.copy()))
                current_bullets = []
            else:
                projects.append(ProjectItem(name=line))
        elif section == "education":
            if "," in line or " – " in line:
                parts = re.split(r"\s*[,–-]\s*", line, maxsplit=1)
                education.append(
                    EducationItem(
                        degree=parts[0].strip(),
                        institution=parts[1].strip() if len(parts) > 1 else "",
                    )
                )
            else:
                education.append(EducationItem(degree=line, institution=""))

    if section == "experience" and (current_title or current_bullets):
        experience.append(
            ExperienceItem(
                title=current_title or "Role",
                company=current_company or "",
                duration=current_duration,
                bullets=current_bullets,
            )
        )

    summary = summary.strip()
    skills = list(dict.fromkeys(s for s in skills if 1 < len(s) < 80))[:80]

    return ParsedResume(
        name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        summary=summary,
        skills=skills,
        skill_categories=skill_categories,
        experience=experience,
        projects=projects,
        education=education,
    )


def _parse_with_llm(text: str) -> ParsedResume:
    """Fallback: use OpenAI to extract structured JSON."""
    settings = get_settings()
    if not settings.openai_api_key:
        return _parse_with_regex(text)
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = """Extract the following from this resume text into JSON. Return ONLY valid JSON, no markdown.
Use this exact structure:
{
  "name": "full name",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "summary": "2-3 sentence summary",
  "skills": ["skill1", "skill2"],
  "skill_categories": [{"category": "Languages", "items": ["Python", "JavaScript"]}],
  "experience": [{"title": "", "company": "", "location": "", "duration": "", "bullets": []}],
  "projects": [{"name": "", "description": "", "bullets": [], "tech": []}],
  "education": [{"degree": "", "institution": "", "year": ""}]
}

Resume text:
"""
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt + text[:12000]}],
            temperature=0,
        )
        content = (r.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content).replace("```", "").strip()
        data = json.loads(content)
        return ParsedResume(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            linkedin=data.get("linkedin", ""),
            github=data.get("github", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", []),
            skill_categories=[
                SkillCategory(category=sc.get("category", ""), items=sc.get("items", []))
                for sc in data.get("skill_categories", [])
            ],
            experience=[ExperienceItem(**x) for x in data.get("experience", [])],
            projects=[ProjectItem(**x) for x in data.get("projects", [])],
            education=[EducationItem(**x) for x in data.get("education", [])],
        )
    except Exception:
        return _parse_with_regex(text)


def parse_resume(file_path: str | Path, use_llm_fallback: bool = False) -> ParsedResume:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    if path.suffix.lower() == ".pdf":
        text = _extract_text_from_pdf(path)
    elif path.suffix.lower() in (".docx", ".doc"):
        text = _extract_text_from_docx(path)
    else:
        raise ValueError("Only PDF and DOCX are supported")

    text = text.strip()
    if not text:
        raise ValueError("No text could be extracted from the file")

    parsed = _parse_with_regex(text)
    if use_llm_fallback and (
        not parsed.skills
        or not parsed.experience
        or not parsed.skill_categories
    ):
        parsed = _parse_with_llm(text)
    return parsed
