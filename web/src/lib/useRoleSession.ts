"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession } from "./api";
import type { Role, Session } from "./types";

export function useRoleSession(role: Role): Session | null {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    const current = getSession();
    if (!current || current.role !== role) {
      router.replace("/login");
      return;
    }
    setSession(current);
  }, [role, router]);

  return session;
}
