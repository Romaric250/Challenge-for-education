"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const result = await api.GET("/api/v1/auth/me");
      if (!result.data) {
        throw new Error("signed out");
      }
      return result.data;
    },
    retry: false,
    retryOnMount: false,
    refetchOnWindowFocus: false,
  });
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  const letters = parts.map((part) => part[0] ?? "").join("");
  return letters.toUpperCase() || "?";
}
