"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getToken } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { logout } = useAuth();

  useEffect(() => {
    if (typeof window !== "undefined" && !getToken()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <Link href="/dashboard" className="text-lg font-bold text-amber-700">
            Tailored Resume
          </Link>
          <Button variant="ghost" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
        {children}
      </main>
    </div>
  );
}
