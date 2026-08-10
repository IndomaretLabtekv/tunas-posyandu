"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { clearSession, getSession } from "@/lib/api";
import { labelForCode } from "@/lib/labels";

type Props = {
  title: string;
  description: string;
  children: ReactNode;
  backHref?: string;
};

export function AppShell({ title, description, children, backHref }: Props) {
  const router = useRouter();
  const session = getSession();

  const logout = () => {
    clearSession();
    router.replace("/login");
  };

  return (
    <main className="min-h-[100dvh] bg-[#f4f6fa]">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex min-h-16 max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link href="/" className="focus-ring flex items-center gap-3 rounded-xl">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-blue-800 text-sm font-black text-white">
              T
            </span>
            <span className="font-bold tracking-tight text-slate-950">Tunas</span>
          </Link>
          <div className="flex items-center gap-3">
            {session && (
              <span className="hidden text-sm text-slate-600 sm:block">
                {session.name} / {session.scope_key}
              </span>
            )}
            <button
              type="button"
              onClick={logout}
              className="focus-ring rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 active:translate-y-px"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 pb-24 pt-7 sm:px-6 sm:py-10">
        <div className="mb-8 flex items-start gap-4">
          {backHref && (
            <Link
              href={backHref}
              className="focus-ring mt-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
            >
              Kembali
            </Link>
          )}
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
              {title}
            </h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
              {description}
            </p>
          </div>
        </div>
        {children}
      </div>
    </main>
  );
}

export function LoadingBlock() {
  return (
    <div className="grid gap-3" aria-label="Memuat data">
      {[0, 1, 2].map((item) => (
        <div key={item} className="h-24 animate-pulse rounded-2xl bg-slate-200" />
      ))}
    </div>
  );
}

export function InlineError({ message }: { message: string }) {
  return (
    <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      {message}
    </div>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const urgent = ["urgent", "needs_review", "verified_risk", "referred"].includes(value);
  const done = ["normal", "resolved", "verified"].includes(value);
  const styles = urgent
    ? "border-amber-300 bg-amber-50 text-amber-900"
    : done
      ? "border-emerald-300 bg-emerald-50 text-emerald-800"
      : "border-slate-300 bg-slate-50 text-slate-700";
  return (
    <span className={`inline-flex rounded-lg border px-2 py-1 text-xs font-bold ${styles}`}>
      {labelForCode(value)}
    </span>
  );
}
