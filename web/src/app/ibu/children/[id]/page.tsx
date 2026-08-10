"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell, InlineError, LoadingBlock, StatusBadge } from "@/components/AppShell";
import { getMotherTimeline } from "@/lib/api";
import type { MotherTimeline } from "@/lib/types";
import { useRoleSession } from "@/lib/useRoleSession";

export default function MotherTimelinePage() {
  const session = useRoleSession("mother");
  const params = useParams();
  const id = Number(params.id);
  const [timeline, setTimeline] = useState<MotherTimeline | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session || !id) return;
    getMotherTimeline(id)
      .then(setTimeline)
      .catch((err) => setError(err instanceof Error ? err.message : "Riwayat tidak dapat dimuat."));
  }, [id, session]);

  if (!session) return <main className="min-h-[100dvh] bg-[#f4f6fa]" />;

  return (
    <AppShell title={timeline?.child.name || "Riwayat anak"} description="Sumber pengukuran, status verifikasi, dan tindak lanjut tersimpan sebagai riwayat terpisah." backHref="/ibu">
      {error ? <InlineError message={error} /> : !timeline ? <LoadingBlock /> : timeline.checks.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center"><h2 className="font-bold text-slate-950">Belum ada pemeriksaan</h2><p className="mt-2 text-sm text-slate-600">Kirim pemeriksaan bulanan pertama dari ruang keluarga.</p></div>
      ) : (
        <div className="grid gap-4">
          {timeline.checks.slice().reverse().map((check) => (
            <article key={check.growth_check_id} className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><p className="text-sm font-semibold text-slate-500">{new Date(check.measured_at).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}</p><h2 className="mt-1 text-lg font-bold text-slate-950">{check.source === "mother" ? "Pemeriksaan dari rumah" : "Pengukuran verifikasi"}</h2></div>
                <div className="flex flex-wrap gap-2"><StatusBadge value={check.verification_status} /><StatusBadge value={check.case_status || check.screening_status} /></div>
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-slate-200 pt-5 sm:grid-cols-4">
                <div><dt className="text-xs font-semibold text-slate-500">Berat</dt><dd className="mt-1 font-bold text-slate-950">{check.weight_kg.toFixed(1)} kg</dd></div>
                <div><dt className="text-xs font-semibold text-slate-500">Panjang</dt><dd className="mt-1 font-bold text-slate-950">{check.length_cm == null ? "Tidak tersedia" : `${check.length_cm.toFixed(1)} cm`}</dd></div>
                <div><dt className="text-xs font-semibold text-slate-500">HAZ</dt><dd className="mt-1 font-bold text-slate-950">{check.haz == null ? "Tidak tersedia" : check.haz.toFixed(2)}</dd></div>
                <div><dt className="text-xs font-semibold text-slate-500">Kepercayaan</dt><dd className="mt-1 font-bold text-slate-950">{Math.round(check.confidence * 100)}%</dd></div>
              </dl>
              {check.qc_reasons.length > 0 && <p className="mt-4 rounded-xl bg-amber-50 p-3 text-sm leading-6 text-amber-900">Catatan kualitas: {check.qc_reasons.join(", ")}</p>}
              <p className="mt-4 text-xs text-slate-500">Pemeriksaan berikutnya: {new Date(check.next_due_at).toLocaleDateString("id-ID")}</p>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  );
}
