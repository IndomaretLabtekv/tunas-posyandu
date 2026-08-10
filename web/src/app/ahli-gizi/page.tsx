"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell, InlineError, LoadingBlock, StatusBadge } from "@/components/AppShell";
import { listNutritionistCases } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { joinLabels } from "@/lib/labels";
import { useRoleSession } from "@/lib/useRoleSession";

export default function NutritionistPage() {
  const session = useRoleSession("nutritionist");
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    listNutritionistCases().then(setCases).catch((err) => setError(err instanceof Error ? err.message : "Dashboard tidak dapat dimuat."));
  }, [session]);

  if (!session) return <main className="min-h-[100dvh] bg-[#f4f6fa]" />;
  const active = cases?.filter((item) => item.status !== "resolved") || [];

  return (
    <AppShell title="Review ahli gizi" description="Tinjau pengukuran terverifikasi, catat intervensi, dan kelola rujukan dalam scope Puskesmas.">
      {error ? <InlineError message={error} /> : cases === null ? <LoadingBlock /> : (
        <>
          <section className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-blue-900 p-5 text-white"><p className="text-sm text-blue-200">Kasus aktif</p><p className="mt-2 text-3xl font-bold">{active.length}</p></div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Terverifikasi</p><p className="mt-2 text-3xl font-bold text-slate-950">{cases.filter((item) => item.status === "verified_risk").length}</p></div>
            <div className="col-span-2 rounded-2xl border border-slate-200 bg-white p-5 sm:col-span-1"><p className="text-sm text-slate-500">Dalam rujukan</p><p className="mt-2 text-3xl font-bold text-slate-950">{cases.filter((item) => item.status === "referred").length}</p></div>
          </section>
          {cases.length === 0 ? <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center"><h2 className="font-bold text-slate-950">Belum ada kasus</h2><p className="mt-2 text-sm text-slate-600">Kasus yang dibuat dari alur keluarga dan kader akan muncul di sini.</p></div> : (
            <div className="grid gap-3">
              {cases.map((item) => (
                <Link key={item.case_id} href={`/ahli-gizi/${item.case_id}`} className="focus-ring grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-blue-300 sm:grid-cols-[1fr_auto] sm:items-center">
                  <div><div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold text-slate-950">{item.child_name}</h2><StatusBadge value={item.status} /></div><p className="mt-2 text-sm font-semibold text-blue-800">Skor prioritas model {item.risk_score.toFixed(3)}</p><p className="mt-2 text-sm text-slate-600">HAZ {item.haz == null ? "belum tersedia" : item.haz.toFixed(2)} · panjang {item.length_cm == null ? "belum tersedia" : `${item.length_cm.toFixed(1)} cm`}</p><p className="mt-2 text-xs text-slate-500">{new Date(item.submitted_at).toLocaleDateString("id-ID")} · {joinLabels(item.reason_codes)}</p></div>
                  <span className="font-bold text-blue-800">Tinjau</span>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
