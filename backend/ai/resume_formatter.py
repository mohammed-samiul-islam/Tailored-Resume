"""Export resume to professional ATS-friendly DOCX and PDF.

Layout modeled after Jake's Resume / Harvard CS template:
- Single column, US Letter, tight margins for 1-page fit
- Helvetica/Arial font stack, 10-11pt body, 22pt bold centered name
- Section headings: bold, uppercase, with horizontal rule
- Experience: title bold left + dates right-aligned, company italic
- Indented bullet points with round bullets
- Skills grouped by category
- Clickable hyperlinks for email, LinkedIn, GitHub, portfolio
"""
import html as _html
import re
from pathlib import Path
from io import BytesIO

from ai.schemas import ParsedResume


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    return _html.escape(s) if s else ""


def _contact_parts(resume: ParsedResume) -> list[str]:
    parts: list[str] = []
    if resume.phone:
        parts.append(resume.phone)
    if resume.email:
        parts.append(resume.email)
    if resume.linkedin:
        parts.append(resume.linkedin)
    if resume.github:
        parts.append(resume.github)
    return parts


def _contact_html_parts(resume: ParsedResume) -> list[str]:
    """Return contact items as clickable HTML links."""
    parts: list[str] = []
    if resume.phone:
        parts.append(_esc(resume.phone))
    if resume.email:
        e = _esc(resume.email)
        parts.append(f'<a href="mailto:{e}">{e}</a>')
    if resume.linkedin:
        url = resume.linkedin if resume.linkedin.startswith("http") else f"https://{resume.linkedin}"
        parts.append(f'<a href="{_esc(url)}">{_esc(resume.linkedin)}</a>')
    if resume.github:
        url = resume.github if resume.github.startswith("http") else f"https://{resume.github}"
        parts.append(f'<a href="{_esc(url)}">{_esc(resume.github)}</a>')
    return parts


def _skills_lines(resume: ParsedResume) -> list[tuple[str, str]]:
    """Return list of (category_label, comma-separated items).
    Uses skill_categories if present, else falls back to flat skills list."""
    if resume.skill_categories:
        return [(sc.category, ", ".join(sc.items)) for sc in resume.skill_categories if sc.items]
    if resume.skills:
        return [("Technical Skills", ", ".join(resume.skills))]
    return []


def _estimate_years_of_experience(resume: ParsedResume) -> int:
    """Rough estimate of total career years from experience durations."""
    import datetime
    current_year = datetime.date.today().year
    earliest, latest = current_year, current_year
    for exp in resume.experience:
        dur = exp.duration or ""
        years = re.findall(r"(20\d{2}|19\d{2})", dur)
        int_years = [int(y) for y in years]
        if int_years:
            earliest = min(earliest, min(int_years))
            latest = max(latest, max(int_years))
    if "present" in " ".join(e.duration or "" for e in resume.experience).lower():
        latest = current_year
    return max(0, latest - earliest)


# ===================================================================
# DOCX builder (python-docx)
# ===================================================================

def build_docx(resume: ParsedResume) -> bytes:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    yoe = _estimate_years_of_experience(resume)
    one_page = yoe < 10
    if one_page:
        resume = _trim_for_one_page(resume)

    FONT = "Arial"
    BODY_SIZE = 10 if one_page else 11
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(BODY_SIZE)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)

    for section in doc.sections:
        section.top_margin = Inches(0.4 if one_page else 0.5)
        section.bottom_margin = Inches(0.4 if one_page else 0.5)
        section.left_margin = Inches(0.5 if one_page else 0.7)
        section.right_margin = Inches(0.5 if one_page else 0.7)

    def _set_font(run, size=11, bold=False, italic=False, color=None):
        run.font.name = FONT
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic
        if color:
            run.font.color.rgb = RGBColor(*color)

    def _add_hr(doc):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(3)
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "4")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "333333")
        pBdr.append(bottom)
        pPr.append(pBdr)

    def _section_heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(text.upper())
        _set_font(run, size=11, bold=True)
        _add_hr(doc)

    def _title_date_line(left_text, right_text, left_bold=True, left_italic=False, size=10.5):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(0)
        run_left = p.add_run(left_text)
        _set_font(run_left, size=size, bold=left_bold, italic=left_italic)
        if right_text:
            run_right = p.add_run(f"\t{right_text}")
            _set_font(run_right, size=size)
        pPr = p._p.get_or_add_pPr()
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), "10080")
        tabs.append(tab)
        pPr.append(tabs)

    def _subtitle_line(text, size=10, italic=True):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(text)
        _set_font(run, size=size, italic=italic)

    def _bullet(text, size=10):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.left_indent = Inches(0.25)
        run = p.add_run(f"\u2022  {text}")
        _set_font(run, size=size)

    # --- Name ---
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(resume.name or "Your Name")
    _set_font(run, size=22, bold=True)

    # --- Contact ---
    contact = _contact_parts(resume)
    if contact:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run("  \u2022  ".join(contact))
        _set_font(run, size=9)

    _add_hr(doc)

    # --- Summary ---
    if resume.summary:
        _section_heading("Summary")
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(resume.summary)
        _set_font(run, size=10)

    # --- Skills ---
    skill_lines = _skills_lines(resume)
    if skill_lines:
        _section_heading("Technical Skills")
        for label, items in skill_lines:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            run_label = p.add_run(f"{label}: ")
            _set_font(run_label, size=10, bold=True)
            run_items = p.add_run(items)
            _set_font(run_items, size=10)

    # --- Experience ---
    if resume.experience:
        _section_heading("Experience")
        for exp in resume.experience:
            _title_date_line(exp.title or "", exp.duration or "")
            company_line = exp.company or ""
            if exp.location:
                company_line += f"  \u2014  {exp.location}"
            if company_line:
                _subtitle_line(company_line)
            for b in (exp.bullets or []):
                _bullet(b)

    # --- Projects ---
    if resume.projects:
        _section_heading("Projects")
        for proj in resume.projects:
            tech_str = ""
            if proj.tech:
                tech_str = "  |  " + ", ".join(proj.tech)
            _title_date_line(proj.name + tech_str, "")
            if proj.description:
                _subtitle_line(proj.description, italic=False)
            for b in (proj.bullets or []):
                _bullet(b)

    # --- Education ---
    if resume.education:
        _section_heading("Education")
        for ed in resume.education:
            _title_date_line(ed.degree, ed.year or "")
            _subtitle_line(ed.institution)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ===================================================================
# PDF builder (ReportLab — pure Python, no system deps)
# ===================================================================

def _build_pdf_reportlab(resume: ParsedResume) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable,
        )
    except ImportError:
        return b""

    PAGE_W, PAGE_H = letter
    MARGIN = 0.7 * inch
    CONTENT_W = PAGE_W - 2 * MARGIN
    DARK = HexColor("#1a1a1a")
    GRAY = HexColor("#444444")
    LINK_COLOR = HexColor("#1a5276")
    RULE_COLOR = HexColor("#333333")

    s_name = ParagraphStyle(
        "Name", fontName="Helvetica-Bold", fontSize=20,
        alignment=TA_CENTER, spaceAfter=2, textColor=DARK, leading=24,
    )
    s_contact = ParagraphStyle(
        "Contact", fontName="Helvetica", fontSize=9,
        alignment=TA_CENTER, spaceAfter=0, textColor=GRAY, leading=12,
    )
    s_heading = ParagraphStyle(
        "SectionHeading", fontName="Helvetica-Bold", fontSize=11,
        spaceBefore=8, spaceAfter=0, textColor=DARK, leading=14,
    )
    s_body = ParagraphStyle(
        "Body", fontName="Helvetica", fontSize=10,
        spaceBefore=1, spaceAfter=1, textColor=DARK, leading=13,
    )
    s_body_bold = ParagraphStyle(
        "BodyBold", fontName="Helvetica-Bold", fontSize=10,
        spaceBefore=1, spaceAfter=0, textColor=DARK, leading=13,
    )
    s_subtitle = ParagraphStyle(
        "Subtitle", fontName="Helvetica-Oblique", fontSize=10,
        spaceBefore=0, spaceAfter=1, textColor=GRAY, leading=13,
    )
    s_bullet = ParagraphStyle(
        "Bullet", fontName="Helvetica", fontSize=10,
        leftIndent=18, firstLineIndent=-14,
        spaceBefore=0, spaceAfter=1, textColor=DARK, leading=13,
    )
    s_right = ParagraphStyle(
        "Right", fontName="Helvetica", fontSize=10,
        alignment=TA_RIGHT, textColor=DARK, leading=13,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )
    story: list = []

    def _hr():
        story.append(HRFlowable(
            width="100%", thickness=0.6, color=RULE_COLOR,
            spaceBefore=2, spaceAfter=3,
        ))

    def _section(title):
        story.append(Paragraph(title.upper(), s_heading))
        _hr()

    def _title_date_row(left_html, right_text):
        left_p = Paragraph(left_html, s_body_bold)
        right_p = Paragraph(_esc(right_text), s_right) if right_text else Paragraph("", s_right)
        t = Table(
            [[left_p, right_p]],
            colWidths=[CONTENT_W * 0.75, CONTENT_W * 0.25],
        )
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t)

    def _link(url: str, label: str) -> str:
        return f'<a href="{_esc(url)}" color="#{LINK_COLOR.hexval()[2:]}">{_esc(label)}</a>'

    # --- Name ---
    story.append(Paragraph(_esc(resume.name or "Your Name"), s_name))

    # --- Contact (with clickable links) ---
    contact_parts: list[str] = []
    if resume.phone:
        contact_parts.append(_esc(resume.phone))
    if resume.email:
        contact_parts.append(_link(f"mailto:{resume.email}", resume.email))
    if resume.linkedin:
        url = resume.linkedin if resume.linkedin.startswith("http") else f"https://{resume.linkedin}"
        contact_parts.append(_link(url, resume.linkedin))
    if resume.github:
        url = resume.github if resume.github.startswith("http") else f"https://{resume.github}"
        contact_parts.append(_link(url, resume.github))
    if contact_parts:
        story.append(Paragraph("  \u2022  ".join(contact_parts), s_contact))

    _hr()

    # --- Summary ---
    if resume.summary:
        _section("Summary")
        story.append(Paragraph(_esc(resume.summary), s_body))

    # --- Skills ---
    skill_lines = _skills_lines(resume)
    if skill_lines:
        _section("Technical Skills")
        for label, items in skill_lines:
            story.append(Paragraph(
                f"<b>{_esc(label)}:</b>  {_esc(items)}", s_body,
            ))

    # --- Experience ---
    if resume.experience:
        _section("Experience")
        for i, exp in enumerate(resume.experience):
            _title_date_row(_esc(exp.title or ""), exp.duration or "")
            company_line = exp.company or ""
            if exp.location:
                company_line += f"  \u2014  {exp.location}"
            if company_line:
                story.append(Paragraph(_esc(company_line), s_subtitle))
            for b in (exp.bullets or []):
                story.append(Paragraph(f"\u2022  {_esc(b)}", s_bullet))
            if i < len(resume.experience) - 1:
                story.append(Spacer(1, 2))

    # --- Projects ---
    if resume.projects:
        _section("Projects")
        for i, proj in enumerate(resume.projects):
            title_text = _esc(proj.name)
            if proj.tech:
                title_text += f'  <font color="#555555">|  {_esc(", ".join(proj.tech))}</font>'
            _title_date_row(title_text, "")
            if proj.description:
                story.append(Paragraph(_esc(proj.description), s_body))
            for b in (proj.bullets or []):
                story.append(Paragraph(f"\u2022  {_esc(b)}", s_bullet))
            if i < len(resume.projects) - 1:
                story.append(Spacer(1, 2))

    # --- Education ---
    if resume.education:
        _section("Education")
        for ed in resume.education:
            _title_date_row(_esc(ed.degree), ed.year or "")
            story.append(Paragraph(_esc(ed.institution), s_subtitle))

    doc.build(story)
    buffer.seek(0)
    out = buffer.getvalue()
    return out if isinstance(out, bytes) and out.startswith(b"%PDF") else b""


# ===================================================================
# Public API
# ===================================================================

def _trim_for_one_page(resume: ParsedResume) -> ParsedResume:
    """Progressively trim content to help fit on one page."""
    from copy import deepcopy
    r = deepcopy(resume)

    MAX_BULLETS_PER_EXP = 4
    for exp in r.experience:
        if len(exp.bullets) > MAX_BULLETS_PER_EXP:
            exp.bullets = exp.bullets[:MAX_BULLETS_PER_EXP]

    MAX_BULLETS_PER_PROJ = 2
    for proj in r.projects:
        if len(proj.bullets) > MAX_BULLETS_PER_PROJ:
            proj.bullets = proj.bullets[:MAX_BULLETS_PER_PROJ]

    if r.summary and len(r.summary) > 200:
        r.summary = r.summary[:197].rsplit(" ", 1)[0] + "..."

    return r


def _weasy_render(html_str: str, css_str: str) -> bytes:
    """Render HTML+CSS to PDF bytes via WeasyPrint."""
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    fc = FontConfiguration()
    doc = HTML(string=html_str)
    css = CSS(string=css_str, font_config=fc)
    return doc.write_pdf(stylesheets=[css], font_config=fc) or b""


def _count_pages(pdf_bytes: bytes) -> int:
    """Count pages in a PDF by looking for /Type /Page entries."""
    return max(1, len(re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes)))


def build_pdf(resume: ParsedResume, output_path: str | Path | None = None) -> bytes:
    """Build PDF: try WeasyPrint first, then ReportLab fallback.

    Enforces US standard: 1 page if <10 years experience, up to 2 if 10+.
    """
    yoe = _estimate_years_of_experience(resume)
    max_pages = 1 if yoe < 10 else 2

    try:
        css_str = _WEASY_CSS_1PAGE if max_pages == 1 else _WEASY_CSS_2PAGE
        html_str = _resume_to_html(resume)
        out = _weasy_render(html_str, css_str)

        if max_pages == 1 and _count_pages(out) > 1:
            trimmed = _trim_for_one_page(resume)
            html_str = _resume_to_html(trimmed)
            out = _weasy_render(html_str, css_str)

        if isinstance(out, bytes) and len(out) > 100 and out.startswith(b"%PDF"):
            return out
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("WeasyPrint PDF failed, falling back to ReportLab: %s", e)
    return _build_pdf_reportlab(resume)


# ===================================================================
# WeasyPrint HTML/CSS template
# ===================================================================

_WEASY_CSS_1PAGE = """
@page {
    size: letter;
    margin: 0.4in 0.5in;
}

body {
    font-family: Helvetica, Arial, "Liberation Sans", sans-serif;
    font-size: 9.5pt;
    line-height: 1.25;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}

h1 {
    font-size: 18pt;
    font-weight: bold;
    text-align: center;
    margin: 0 0 2pt 0;
    letter-spacing: 0.5pt;
}

.contact {
    text-align: center;
    font-size: 8.5pt;
    color: #333;
    margin: 0 0 1pt 0;
    line-height: 1.3;
}
.contact a { color: #1a5276; text-decoration: none; }

hr {
    border: none;
    border-top: 0.75pt solid #333;
    margin: 3pt 0 4pt 0;
}

h2 {
    font-size: 10pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin: 5pt 0 0 0;
    padding-bottom: 1pt;
    border-bottom: 0.75pt solid #333;
}

.entry {
    margin-top: 3pt;
    page-break-inside: avoid;
}

.entry-table {
    width: 100%;
    border-collapse: collapse;
    margin: 0;
    padding: 0;
}
.entry-table td {
    padding: 0;
    vertical-align: top;
}
.entry-table .td-title {
    font-weight: bold;
    font-size: 9.5pt;
}
.entry-table .td-date {
    text-align: right;
    font-size: 9pt;
    white-space: nowrap;
    width: 1%;
}

.entry-subtitle {
    font-style: italic;
    color: #444;
    font-size: 9pt;
    margin: 0 0 0.5pt 0;
}

ul {
    margin: 1pt 0 1pt 14pt;
    padding: 0;
}
li {
    margin-bottom: 0.5pt;
    line-height: 1.25;
    font-size: 9.5pt;
}

.skills-line {
    margin: 1pt 0;
    font-size: 9.5pt;
    line-height: 1.3;
}
.skills-label {
    font-weight: bold;
}

.tech-stack {
    color: #555;
    font-weight: normal;
}
"""

_WEASY_CSS_2PAGE = """
@page {
    size: letter;
    margin: 0.5in 0.7in;
}

body {
    font-family: Helvetica, Arial, "Liberation Sans", sans-serif;
    font-size: 10pt;
    line-height: 1.3;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
}

h1 {
    font-size: 22pt;
    font-weight: bold;
    text-align: center;
    margin: 0 0 4pt 0;
    letter-spacing: 0.5pt;
}

.contact {
    text-align: center;
    font-size: 9pt;
    color: #333;
    margin: 0 0 2pt 0;
    line-height: 1.4;
}
.contact a { color: #1a5276; text-decoration: none; }

hr {
    border: none;
    border-top: 1pt solid #333;
    margin: 4pt 0 6pt 0;
}

h2 {
    font-size: 11pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin: 8pt 0 0 0;
    padding-bottom: 2pt;
    border-bottom: 1pt solid #333;
}

.entry {
    margin-top: 4pt;
    page-break-inside: avoid;
}

.entry-table {
    width: 100%;
    border-collapse: collapse;
    margin: 0;
    padding: 0;
}
.entry-table td {
    padding: 0;
    vertical-align: top;
}
.entry-table .td-title {
    font-weight: bold;
    font-size: 10.5pt;
}
.entry-table .td-date {
    text-align: right;
    font-size: 10pt;
    white-space: nowrap;
    width: 1%;
}

.entry-subtitle {
    font-style: italic;
    color: #444;
    font-size: 10pt;
    margin: 0 0 1pt 0;
}

ul {
    margin: 2pt 0 2pt 16pt;
    padding: 0;
}
li {
    margin-bottom: 1.5pt;
    line-height: 1.3;
    font-size: 10pt;
}

.skills-line {
    margin: 2pt 0;
    font-size: 10pt;
    line-height: 1.4;
}
.skills-label {
    font-weight: bold;
}

.tech-stack {
    color: #555;
    font-weight: normal;
}
"""


def _resume_to_html(resume: ParsedResume) -> str:
    h = ['<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>']

    # --- Name ---
    h.append(f"<h1>{_esc(resume.name or 'Your Name')}</h1>")

    # --- Contact (with clickable links) ---
    contact_parts = _contact_html_parts(resume)
    if contact_parts:
        h.append(f'<p class="contact">{"  &bull;  ".join(contact_parts)}</p>')

    h.append("<hr>")

    # --- Summary ---
    if resume.summary:
        h.append("<h2>Summary</h2>")
        h.append(f"<p>{_esc(resume.summary)}</p>")

    # --- Skills ---
    skill_lines = _skills_lines(resume)
    if skill_lines:
        h.append("<h2>Technical Skills</h2>")
        for label, items in skill_lines:
            h.append(
                f'<p class="skills-line">'
                f'<span class="skills-label">{_esc(label)}:</span> {_esc(items)}'
                f'</p>'
            )

    # --- Experience ---
    if resume.experience:
        h.append("<h2>Experience</h2>")
        for exp in resume.experience:
            h.append('<div class="entry">')
            h.append('<table class="entry-table"><tr>')
            h.append(f'<td class="td-title">{_esc(exp.title or "")}</td>')
            h.append(f'<td class="td-date">{_esc(exp.duration or "")}</td>')
            h.append('</tr></table>')
            company = exp.company or ""
            if exp.location:
                company += f"  \u2014  {exp.location}"
            if company:
                h.append(f'<div class="entry-subtitle">{_esc(company)}</div>')
            if exp.bullets:
                h.append("<ul>")
                for b in exp.bullets:
                    h.append(f"<li>{_esc(b)}</li>")
                h.append("</ul>")
            h.append("</div>")

    # --- Projects ---
    if resume.projects:
        h.append("<h2>Projects</h2>")
        for proj in resume.projects:
            h.append('<div class="entry">')
            title_html = _esc(proj.name)
            if proj.tech:
                title_html += f'  <span class="tech-stack">|  {_esc(", ".join(proj.tech))}</span>'
            h.append(f'<table class="entry-table"><tr>')
            h.append(f'<td class="td-title">{title_html}</td>')
            h.append(f'<td class="td-date"></td>')
            h.append('</tr></table>')
            if proj.description:
                h.append(f"<p>{_esc(proj.description)}</p>")
            if proj.bullets:
                h.append("<ul>")
                for b in proj.bullets:
                    h.append(f"<li>{_esc(b)}</li>")
                h.append("</ul>")
            h.append("</div>")

    # --- Education ---
    if resume.education:
        h.append("<h2>Education</h2>")
        for ed in resume.education:
            h.append('<div class="entry">')
            h.append('<table class="entry-table"><tr>')
            h.append(f'<td class="td-title">{_esc(ed.degree)}</td>')
            h.append(f'<td class="td-date">{_esc(ed.year or "")}</td>')
            h.append('</tr></table>')
            h.append(f'<div class="entry-subtitle">{_esc(ed.institution)}</div>')
            h.append("</div>")

    h.append("</body></html>")
    return "\n".join(h)
