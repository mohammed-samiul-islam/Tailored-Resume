import { getToken, setToken, clearToken, authApi, resumeApi, jobApi } from "../api";

describe("api", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    clearToken();
    global.fetch = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe("token storage", () => {
    it("stores and retrieves token", () => {
      expect(getToken()).toBeNull();
      setToken("abc123");
      expect(getToken()).toBe("abc123");
      clearToken();
      expect(getToken()).toBeNull();
    });
  });

  describe("authApi", () => {
    it("register sends POST with json body", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ access_token: "t", user: { id: 1, email: "a@b.com" } }),
      });
      await authApi.register("a@b.com", "pass");
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/register"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ email: "a@b.com", password: "pass" }),
        })
      );
    });

    it("login sends form body", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ access_token: "t", user: { id: 1, email: "a@b.com" } }),
      });
      await authApi.login("a@b.com", "pass");
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/login"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        })
      );
    });
  });

  describe("resumeApi", () => {
    it("generate sends resume_id and job_id", async () => {
      setToken("t");
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            id: 1,
            resume_id: 1,
            job_id: 2,
            ats_score: 80,
            file_url: "uploads/x.docx",
            created_at: "2024-01-01",
          }),
      });
      await resumeApi.generate(1, 2);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/resume/generate"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ resume_id: 1, job_id: 2 }),
          headers: expect.objectContaining({ Authorization: "Bearer t" }),
        })
      );
    });
  });

  describe("jobApi", () => {
    it("analyze sends job_text", async () => {
      setToken("t");
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            id: 1,
            job_text: "Python developer",
            parsed_keywords: {},
            created_at: "2024-01-01",
          }),
      });
      await jobApi.analyze("Python developer with FastAPI.");
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/job/analyze"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ job_text: "Python developer with FastAPI." }),
        })
      );
    });
  });
});
