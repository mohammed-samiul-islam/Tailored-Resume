"use client";

import { useRouter } from "next/navigation";
import { getToken, setToken, clearToken } from "@/services/api";

export function useAuth() {
  const router = useRouter();
  const token = typeof window !== "undefined" ? getToken() : null;
  const isLoggedIn = !!token;

  const login = (t: string) => {
    setToken(t);
    router.push("/dashboard");
    router.refresh();
  };

  const logout = () => {
    clearToken();
    router.push("/");
    router.refresh();
  };

  return { isLoggedIn, login, logout, token };
}
