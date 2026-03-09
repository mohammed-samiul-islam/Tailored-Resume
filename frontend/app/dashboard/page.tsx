"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { resumeApi, jobApi, getToken } from "@/services/api";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Upload, FileText, Briefcase, Sparkles, Download, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

export default function DashboardPage() {
  const [jobText, setJobText] = useState("");
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const queryClient = useQueryClient();

  const { data: resumes = [], isLoading: resumesLoading } = useQuery({
    queryKey: ["resumes"],
    queryFn: resumeApi.list,
    retry: false,
  });

  const { data: jobs = [], isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: jobApi.list,
    retry: false,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => resumeApi.upload(file),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      if (data?.id != null) setResumeId(Number(data.id));
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (text: string) => jobApi.analyze(text),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setJobText("");
      if (data?.id != null) setJobId(Number(data.id));
    },
  });

  const generateMutation = useMutation({
    mutationFn: ({ resumeId, jobId }: { resumeId: number; jobId: number }) =>
      resumeApi.generate(resumeId, jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resumes"] }),
  });

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (uploadFile) {
      uploadMutation.mutate(uploadFile);
      setUploadFile(null);
    }
  };

  const handleAnalyzeJob = (e: React.FormEvent) => {
    e.preventDefault();
    if (jobText.trim().length >= 50) analyzeMutation.mutate(jobText.trim());
  };

  const handleGenerate = () => {
    setDownloadError("");
    const rId = resumeId != null ? Number(resumeId) : null;
    const jId = jobId != null ? Number(jobId) : null;
    if (rId != null && jId != null && !Number.isNaN(rId) && !Number.isNaN(jId)) {
      generateMutation.mutate({ resumeId: rId, jobId: jId });
    }
  };

  const downloadWithAuth = async (generatedId: number, format: "docx" | "pdf") => {
    setDownloadError("");
    const token = getToken();
    const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/resume/download/${generatedId}?format=${format}`;
    try {
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Download failed" }));
        setDownloadError(err?.detail ?? "Download failed. Try again.");
        return;
      }
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      const jobSnippet = jobs.find((j) => j.id === jobId)?.job_text?.slice(0, 30).replace(/[^a-zA-Z0-9]+/g, "_") || "tailored";
      a.download = `resume_${jobSnippet}.${format}`;
      a.click();
      URL.revokeObjectURL(objectUrl);
    } catch {
      setDownloadError("Network error. Check your connection and try again.");
    }
  };

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-stone-900">Dashboard</h1>
        <p className="mt-1 text-stone-600">Upload a resume, add a job, and generate an ATS-optimized resume.</p>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" /> Upload resume
            </CardTitle>
          </CardHeader>
          <form onSubmit={handleUpload} className="space-y-3">
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-stone-600 file:mr-4 file:rounded-lg file:border-0 file:bg-amber-50 file:px-4 file:py-2 file:text-amber-700"
            />
            <Button type="submit" disabled={!uploadFile || uploadMutation.isPending}>
              {uploadMutation.isPending ? "Uploading…" : "Upload"}
            </Button>
          </form>
          {uploadMutation.isSuccess && (
            <p className="mt-2 flex items-center gap-1 text-sm text-green-700">
              <CheckCircle className="h-4 w-4" /> Resume uploaded and selected.
            </p>
          )}
          {uploadMutation.isError && (
            <p className="mt-2 flex items-center gap-1 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" /> {uploadMutation.error instanceof Error ? uploadMutation.error.message : "Upload failed. Only PDF/DOCX, max 4MB."}
            </p>
          )}
          {resumesLoading && <p className="mt-3 flex items-center gap-1 text-sm text-stone-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading resumes…</p>}
          {resumes.length > 0 && (
            <div className="mt-4 border-t border-stone-200 pt-4">
              <p className="mb-2 text-sm font-medium text-stone-700">Your resumes</p>
              <ul className="space-y-1">
                {resumes.map((r) => (
                  <li key={r.id} className="flex items-center gap-2 text-sm">
                    <FileText className="h-4 w-4 text-stone-400" />
                    <span className="truncate">{r.file_url?.split("/").pop() ?? "resume"}</span>
                    <button
                      type="button"
                      onClick={() => setResumeId(Number(r.id))}
                      className={resumeId === Number(r.id) ? "text-amber-600 font-medium" : "text-amber-600 hover:underline"}
                    >
                      {resumeId === Number(r.id) ? "Selected" : "Select"}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" /> Add job description
            </CardTitle>
          </CardHeader>
          <form onSubmit={handleAnalyzeJob} className="space-y-3">
            <textarea
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              placeholder="Paste the full job description here (min 50 characters)..."
              rows={5}
              className="w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm placeholder:text-stone-400 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
            <Button type="submit" disabled={jobText.trim().length < 50 || analyzeMutation.isPending}>
              {analyzeMutation.isPending ? "Analyzing…" : "Analyze & save"}
            </Button>
          </form>
          {analyzeMutation.isSuccess && (
            <p className="mt-2 flex items-center gap-1 text-sm text-green-700">
              <CheckCircle className="h-4 w-4" /> Job analyzed and selected.
            </p>
          )}
          {analyzeMutation.isError && (
            <p className="mt-2 flex items-center gap-1 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" /> {analyzeMutation.error instanceof Error ? analyzeMutation.error.message : "Analysis failed. Make sure the description is at least 50 characters."}
            </p>
          )}
          {jobsLoading && <p className="mt-3 flex items-center gap-1 text-sm text-stone-500"><Loader2 className="h-4 w-4 animate-spin" /> Loading jobs…</p>}
          {jobs.length > 0 && (
            <div className="mt-4 border-t border-stone-200 pt-4">
              <p className="mb-2 text-sm font-medium text-stone-700">Saved jobs</p>
              <ul className="space-y-1">
                {jobs.map((j) => (
                  <li key={j.id} className="flex items-center gap-2 text-sm">
                    <Briefcase className="h-4 w-4 text-stone-400" />
                    <span className="line-clamp-1 flex-1">{j.job_text.slice(0, 60)}…</span>
                    <button
                      type="button"
                      onClick={() => setJobId(Number(j.id))}
                      className={jobId === Number(j.id) ? "text-amber-600 font-medium" : "text-amber-600 hover:underline"}
                    >
                      {jobId === Number(j.id) ? "Selected" : "Select"}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" /> Generate ATS resume
          </CardTitle>
        </CardHeader>
        <p className="mb-2 text-sm text-stone-600">
          Select a resume and a job above, then generate a tailored resume with an ATS score.
        </p>
        <p className="mb-4 text-xs text-stone-500">
          {resumeId != null && jobId != null
            ? `Selected: Resume #${resumeId}, Job #${jobId}`
            : resumeId != null
              ? "Select a job from the list above."
              : jobId != null
                ? "Select a resume from the list above."
                : "Select a resume and a job from the cards above."}
        </p>
        <Button
          onClick={handleGenerate}
          disabled={
            resumeId === null ||
            resumeId === undefined ||
            jobId === null ||
            jobId === undefined ||
            generateMutation.isPending
          }
        >
          {generateMutation.isPending ? "Generating…" : "Generate resume"}
        </Button>
        {generateMutation.isError && (
          <p className="mt-4 text-sm text-red-600">
            {generateMutation.error instanceof Error ? generateMutation.error.message : "Generation failed. Try again."}
          </p>
        )}
        {generateMutation.data && (
          <div className="mt-6 rounded-lg border border-stone-200 bg-stone-50 p-4">
            <p className="font-medium text-stone-900">Generated resume</p>
            <p className="mt-1 text-sm text-stone-600">
              We&apos;ve tailored your resume for this job and included relevant keywords from your experience.
            </p>
            <p className="mt-2 text-sm text-stone-600">
              ATS Score: <strong>{generateMutation.data.ats_score ?? "—"}/100</strong>
            </p>
            {(generateMutation.data.ats_score ?? 0) < 90 && (
              <p className="mt-2 text-sm text-stone-700">
                This is the best match we could create from your current master resume.
              </p>
            )}
            {generateMutation.data.missing_keywords && generateMutation.data.missing_keywords.length > 0 && (
              <>
                <p className="mt-2 text-sm text-amber-800">
                  We didn&apos;t add these because they weren&apos;t on your resume. Learn these skills and add them to your master resume, then regenerate to aim for 90+.
                </p>
                <p className="mt-1 text-sm text-stone-600">
                  Missing keywords: {generateMutation.data.missing_keywords.join(", ")}
                </p>
              </>
            )}
            {downloadError && (
              <p className="mt-2 flex items-center gap-1 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" /> {downloadError}
              </p>
            )}
            <div className="mt-3 flex gap-2">
              <Button
                variant="outline"
                size="small"
                onClick={() => downloadWithAuth(generateMutation.data!.id, "docx")}
                type="button"
              >
                <Download className="mr-1 h-4 w-4" /> DOCX
              </Button>
              <Button
                variant="outline"
                size="small"
                onClick={() => downloadWithAuth(generateMutation.data!.id, "pdf")}
                type="button"
              >
                <Download className="mr-1 h-4 w-4" /> PDF
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
