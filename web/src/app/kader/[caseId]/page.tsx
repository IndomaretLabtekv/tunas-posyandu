"use client";

import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AppShell, InlineError, LoadingBlock, StatusBadge } from "@/components/AppShell";
import { assignCase, getKaderCase, recordHomeVisit, verifyCase } from "@/lib/api";
import type { CaseDetail } from "@/lib/types";
import { useRoleSession } from "@/lib/useRoleSession";

export default function KaderCasePage() {
  const session = useRoleSession("kader");
  const caseId = Number(useParams().caseId);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState("");
  const [weight, setWeight] = useState("");
  const [length, setLength] = useState("");
  const [outcome, setOutcome] = useState<"verified_risk" | "resolved">("verified_risk");

  const load = () => getKaderCase(caseId).then(setDetail).catch((err) => setError(err instanceof Error ? err.message : "Kasus tidak dapat dimuat."));
  useEffect(() => { if (session && caseId) load(); }, [caseId, session]);

  const action = async (event: FormEvent) => {
    event.preventDefault();
    if (!detail) return;
    setBusy(true);
    setError("");
    try {
      let updated: CaseDetail;
      if (detail.case.status === "needs_review") updated = await assignCase(caseId, notes);
      else if (detail.case.status === "assigned") updated = await recordHomeVisit(caseId, { notes, weight_kg: weight ? Number(weight) : null, length_cm: length ? Number(length) : null });
      else updated = await verifyCase(caseId, { notes, weight_kg: Number(weight), length_cm: Number(length), outcome });
      setDetail(updated);
      setNotes("");
      setWeight("");
      setLength("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tindakan tidak dapat disimpan.");
    } finally {
      setBusy(false);
    }
  };

  if (!session) return <main className="min-h-[100dvh] bg-[#f4f6fa]" />;

  return (
    <AppShell title={detail?.case.child_name || "Detail kasus"} description="Submission awal tetap tersimpan. Pengukuran kader dicatat sebagai verifikasi terpisah." backHref="/kader">
      {error && <div className="mb-5"><InlineError message={error} /></div>}
      {!detail ? <LoadingBlock /> : (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="grid gap-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold text-slate-500">Kasus #{detail.case.case_id}</p><h2 className="mt-1 text-xl font-bold text-slate-950">Pemeriksaan dari rumah</h2></div><StatusBadge value={detail.case.status} /></div>
              <dl className="mt-6 grid grid-cols-2 gap-5 border-t border-slate-200 pt-5 sm:grid-cols-4">
                <div><dt className="text-xs font-semibold text-slate-500">Berat</dt><dd className="mt-1 font-bold">{detail.case.weight_kg.toFixed(1)} kg</dd></div>
                <div><dt className="text-xs font-semibold text-slate-500">Panjang</dt><dd className="mt-1 font-bold">{detail.case.length_cm ? `${detail.case.length_cm.toFixed(1)} cm` : "Tidak tersedia"}</dd></div>
                <div><dt className="text-xs font-semibold text-slate-500">Kepercayaan</dt><dd className="mt-1 font-bold">{Math.round(detail.case.confidence * 100)}%</dd></div>
                <div><dt className="text-xs font-semibold text-slate-500">Terlambat</dt><dd className="mt-1 font-bold">{detail.case.overdue ? "Ya" : "Tidak"}</dd></div>
              </dl>
              <p className="mt-5 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-900">Perlu verifikasi karena: {detail.case.reason_codes.join(", ")}.</p>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <h2 className="text-lg font-bold text-slate-950">Jejak tindakan</h2>
              {detail.actions.length === 0 ? <p className="mt-4 text-sm text-slate-600">Belum ada tindakan lapangan.</p> : (
                <div className="mt-5 grid gap-4">{detail.actions.map((item) => <div key={item.action_id} className="border-l-2 border-blue-300 pl-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-bold text-slate-900">{item.action_type.replaceAll("_", " ")}</p><time className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString("id-ID")}</time></div>{item.notes && <p className="mt-1 text-sm leading-6 text-slate-600">{item.notes}</p>}</div>)}</div>
              )}
            </section>
          </div>

          <section className="h-fit rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <h2 className="text-lg font-bold text-slate-950">Tindakan berikutnya</h2>
            {!["needs_review", "assigned", "home_visit"].includes(detail.case.status) ? (
              <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">Tahap kader selesai. Kasus sekarang berstatus <strong>{detail.case.status.replaceAll("_", " ")}</strong>.</p>
            ) : (
              <form onSubmit={action} className="mt-5 grid gap-4">
                <p className="rounded-xl bg-blue-50 p-4 text-sm font-semibold leading-6 text-blue-900">{detail.case.status === "needs_review" ? "Ambil tanggung jawab kasus ini." : detail.case.status === "assigned" ? "Catat kunjungan rumah tanpa menimpa data awal." : "Masukkan hasil ukur ulang dan hasil verifikasi."}</p>
                {(detail.case.status === "assigned" || detail.case.status === "home_visit") && <div className="grid grid-cols-2 gap-3"><label className="grid gap-2 text-sm font-semibold">Berat (kg)<input required={detail.case.status === "home_visit"} min="0.1" step="0.1" type="number" value={weight} onChange={(event) => setWeight(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-3 py-3 font-normal" /></label><label className="grid gap-2 text-sm font-semibold">Panjang (cm)<input required={detail.case.status === "home_visit"} min="1" step="0.1" type="number" value={length} onChange={(event) => setLength(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-3 py-3 font-normal" /></label></div>}
                {detail.case.status === "home_visit" && <label className="grid gap-2 text-sm font-semibold">Hasil verifikasi<select value={outcome} onChange={(event) => setOutcome(event.target.value as typeof outcome)} className="focus-ring rounded-xl border border-slate-300 bg-white px-3 py-3 font-normal"><option value="verified_risk">Perlu review ahli gizi</option><option value="resolved">Tidak ada risiko setelah ukur ulang</option></select></label>}
                <label className="grid gap-2 text-sm font-semibold">Catatan<textarea rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-3 py-3 font-normal" /></label>
                <button disabled={busy} className="focus-ring rounded-xl bg-blue-800 px-4 py-3 font-bold text-white hover:bg-blue-900 disabled:opacity-60">{busy ? "Menyimpan..." : detail.case.status === "needs_review" ? "Ambil kasus" : detail.case.status === "assigned" ? "Simpan kunjungan" : "Simpan verifikasi"}</button>
              </form>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
