"""Resume and Job API (list, analyze, generate with mocks)."""
import io
import pytest
from httpx import AsyncClient

from tests.conftest import client, auth_headers


@pytest.mark.asyncio
async def test_resume_list_requires_auth(client_no_auth: AsyncClient):
    r = await client_no_auth.get("/resume/list")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_resume_list_empty(client: AsyncClient, auth_headers: dict):
    r = await client.get("/resume/list", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_resume_upload(client: AsyncClient, auth_headers: dict):
    content = b"%PDF-1.4 minimal content for test"
    r = await client.post(
        "/resume/upload",
        headers=auth_headers,
        files={"file": ("resume.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] >= 1
    assert "file_url" in data


@pytest.mark.asyncio
async def test_job_list_requires_auth(client_no_auth: AsyncClient):
    r = await client_no_auth.get("/job/list")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_job_analyze(client: AsyncClient, auth_headers: dict):
    job_text = "We need a Senior Python Developer with 5+ years experience in FastAPI and AWS."
    r = await client.post(
        "/job/analyze",
        headers=auth_headers,
        json={"job_text": job_text},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] >= 1
    assert "parsed_keywords" in data


@pytest.mark.asyncio
async def test_job_analyze_too_short(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/job/analyze",
        headers=auth_headers,
        json={"job_text": "Short"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_generate_resume(client: AsyncClient, auth_headers: dict):
    # Upload a resume first
    content = b"%PDF-1.4 test"
    ru = await client.post(
        "/resume/upload",
        headers=auth_headers,
        files={"file": ("r.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert ru.status_code == 200
    resume_id = ru.json()["id"]

    # Analyze a job
    rj = await client.post(
        "/job/analyze",
        headers=auth_headers,
        json={"job_text": "Python developer with FastAPI and React experience. Must have AWS."},
    )
    assert rj.status_code == 200
    job_id = rj.json()["id"]

    # Generate
    r = await client.post(
        "/resume/generate",
        headers=auth_headers,
        json={"resume_id": resume_id, "job_id": job_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["resume_id"] == resume_id
    assert data["job_id"] == job_id
    assert "ats_score" in data
    assert "file_url" in data


@pytest.mark.asyncio
async def test_download_invalid_format(client: AsyncClient, auth_headers: dict):
    r = await client.get("/resume/download/1?format=exe", headers=auth_headers)
    assert r.status_code == 422
    assert "docx" in r.json()["detail"] or "pdf" in r.json()["detail"]
