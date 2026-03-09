import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-stone-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
          <span className="text-xl font-bold text-amber-700">Tailored Resume</span>
          <nav className="flex gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-stone-600 hover:text-stone-900"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
            >
              Sign up
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-20">
        <h1 className="text-4xl font-bold tracking-tight text-stone-900 sm:text-5xl">
          Resumes tailored to every job
        </h1>
        <p className="mt-4 max-w-xl text-center text-stone-600">
          Upload your master resume, paste a job description, and get an ATS-optimized
          resume. We aim for a score of 90+ and show you exactly what’s missing.
        </p>
        <div className="mt-10 flex gap-4">
          <Link
            href="/register"
            className="rounded-lg bg-amber-600 px-6 py-3 text-sm font-medium text-white hover:bg-amber-700"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-stone-300 px-6 py-3 text-sm font-medium text-stone-700 hover:bg-stone-50"
          >
            Log in
          </Link>
        </div>
      </main>
    </div>
  );
}
