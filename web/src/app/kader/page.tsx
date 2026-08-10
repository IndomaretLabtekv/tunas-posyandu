"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell, InlineError, LoadingBlock, StatusBadge } from "@/components/AppShell";
import { listKaderCases } from "@/lib/api";
import type { CaseSummary } from "@/lib/types";
import { joinLabels } from "@/lib/labels";
import { useRoleSession } from "@/lib/useRoleSession";

export default function KaderPage() {
  const session = useRoleSession("kader");
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    listKaderCases().then(setCases).catch((err) => setError(err instanceof Error ? err.message : "Antrean tidak dapat dimuat."));
  }, [session]);

  if (!session) return <main className="min-h-[100dvh] bg-[#f4f6fa]" />;

  return (
    <AppShell title="Antrean tindak lanjut" description="Kasus diurutkan dari sinyal mendesak, terlambat ditangani, lalu kasus tertua.">
      {error ? <InlineError message={error} /> : cases === null ? <LoadingBlock /> : cases.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center"><h2 className="font-bold text-slate-950">Antrean kosong</h2><p className="mt-2 text-sm text-slate-600">Belum ada pemeriksaan yang membutuhkan verifikasi pada scope ini.</p></div>
      ) : (
        <div className="grid gap-3">
          {cases.map((item) => (
            <Link key={item.case_id} href={`/kader/${item.case_id}`} className="focus-ring grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-blue-300 sm:grid-cols-[1fr_auto] sm:items-center">
              <div>
                <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold text-slate-950">{item.child_name}</h2><StatusBadge value={item.status} />{item.overdue && <StatusBadge value="overdue" />}</div>
                <p className="mt-2 text-sm text-slate-600">{item.age_days} hari / {item.weight_kg.toFixed(1)} kg / {item.length_cm ? `${item.length_cm.toFixed(1)} cm` : "panjang belum tersedia"}</p>
                <p className="mt-2 text-sm font-semibold text-blue-800">Skor prioritas model {item.risk_score.toFixed(3)}</p>
                <p className="mt-2 text-xs text-slate-500">Alasan: {joinLabels(item.reason_codes)} · dikirim {item.days_since_submission} hari lalu</p>
              </div>
              <span className="font-bold text-blue-800">Buka kasus</span>
            </Link>
          ))}
        </div>
      )}
    </AppShell>
  );
}
