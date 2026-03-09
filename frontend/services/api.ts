const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TokenStorage = {
  get: () => string | null;
  set: (t: string) => void;
  clear: () => void;
};

const tokenStorage: TokenStorage = {
  get: () => (typeof window !== "undefined" ? localStorage.getItem("tailoredresume_token") : null),
  set: (t) => { if (typeof window !== "undefined") localStorage.setItem("tailoredresume_token", t); },
  clear: () => { if (typeof window !== "undefined") localStorage.removeItem("tailoredresume_token"); },
};

export function getToken(): string | null {
  return tokenStorage.get();
}

export function setToken(token: string): void {
  tokenStorage.set(token);
}

export function clearToken(): void {
  tokenStorage.clear();
}

async function request<T>(
  path: string,
  options: RequestInit & { json?: unknown } = {}
): Promise<T> {
  const { json, ...init } = options;
  const headers: HeadersInit = {
    ...(init.headers as Record<string, string>),
  };
  if (json !== undefined) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(json);
  }
  const token = tokenStorage.get();
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(Array.isArray(err.detail) ? err.detail[0]?.msg || res.statusText : err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Auth
export const authApi = {
  register: (email: string, password: string) =>
    request<{ access_token: string; user: { id: number; email: string } }>("/auth/register", {
      method: "POST",
      json: { email, password },
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; user: { id: number; email: string } }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    }),
};

// Resume
export const resumeApi = {
  list: () => request<{ id: number; file_url: string; parsed_json: unknown; created_at: string }[]>("/resume/list"),
  upload: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const token = tokenStorage.get();
    const res = await fetch(`${API_BASE}/resume/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },
  parse: (resumeId: number) =>
    request<{ id: number; file_url: string; parsed_json: unknown }>(`/resume/parse/${resumeId}`, { method: "POST" }),
  generate: (resumeId: number, jobId: number) =>
    request<{
      id: number;
      resume_id: number;
      job_id: number;
      ats_score: number | null;
      score_breakdown: Record<string, number> | null;
      missing_keywords: string[] | null;
      file_url: string | null;
      created_at: string;
    }>("/resume/generate", { method: "POST", json: { resume_id: resumeId, job_id: jobId } }),
  score: (generatedId: number) =>
    request<{ ats_score: number; breakdown: Record<string, number>; missing_keywords: string[] }>(
      `/resume/score/${generatedId}`
    ),
  downloadUrl: (generatedId: number, format: "docx" | "pdf" = "docx") => {
    const token = tokenStorage.get();
    return `${API_BASE}/resume/download/${generatedId}?format=${format}${token ? `&token=${token}` : ""}`;
  },
  getGenerated: (generatedId: number) =>
    request<{
      id: number;
      resume_id: number;
      job_id: number;
      ats_score: number | null;
      score_breakdown: Record<string, number> | null;
      missing_keywords: string[] | null;
      file_url: string | null;
      created_at: string;
    }>(`/resume/generated/${generatedId}`),
};

// Job
export const jobApi = {
  list: () =>
    request<{ id: number; job_text: string; parsed_keywords: unknown; created_at: string }[]>("/job/list"),
  analyze: (jobText: string) =>
    request<{ id: number; job_text: string; parsed_keywords: unknown; created_at: string }>("/job/analyze", {
      method: "POST",
      json: { job_text: jobText },
    }),
};
