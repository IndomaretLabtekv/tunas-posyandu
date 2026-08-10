"use client";

import { useParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AppShell, InlineError, LoadingBlock, StatusBadge } from "@/components/AppShell";
import { getNutritionistCase, recordDecision, referCase } from "@/lib/api";
import type { CaseDetail } from "@/lib/types";
import { joinLabels, labelForCode } from "@/lib/labels";
import { useRoleSession } from "@/lib/useRoleSession";

export default function NutritionistCasePage() {
  const session = useRoleSession("nutritionist");
  const caseId = Number(useParams().caseId);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"decision" | "referral">("decision");
  const [action, setAction] = useState("");
  const [destination, setDestination] = useState("");
  const [notes, setNotes] = useState("");

  const load = () => getNutritionistCase(caseId).then(setDetail).catch((err) => setError(err instanceof Error ? err.message : "Kasus tidak dapat dimuat."));
  useEffect(() => { if (session && caseId) load(); }, [caseId, session]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const updated = mode === "referral" ? await referCase(caseId, destination, notes) : await recordDecision(caseId, { action, notes, resolve: true });
      setDetail(updated);
      setAction("");
      setDestination("");
      setNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Keputusan tidak dapat disimpan.");
    } finally {
      setBusy(false);
    }
  };

  if (!session) return <main className="min-h-[100dvh] bg-[#f4f6fa]" />;

  return (
    <AppShell title={detail?.case.child_name || "Tinjau kasus"} description="Bandingkan sumber data sebelum mencatat keputusan, intervensi, atau rujukan." backHref="/ahli-gizi">
      {error && <div className="mb-5"><InlineError message={error} /></div>}
      {!detail ? <LoadingBlock /> : (
        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="grid gap-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-semibold text-slate-500">Kasus #{detail.case.case_id}</p><h2 className="mt-1 text-xl font-bold text-slate-950">Ringkasan skrining</h2></div><StatusBadge value={detail.case.status} /></div>
              <p className="mt-5 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-900">Alasan kasus perlu ditinjau: {joinLabels(detail.case.reason_codes).toLowerCase()}.</p>
              <div className="mt-4 rounded-xl bg-blue-50 p-4 text-sm text-blue-950"><p className="font-bold">Skor prioritas model {detail.case.risk_score.toFixed(3)}</p><p className="mt-1 leading-6 text-blue-800">Faktor utama: {detail.case.risk_factors.map((factor) => factor.label).join(", ")}. Nilai ini membantu menentukan urutan tinjauan, bukan diagnosis.</p></div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <h2 className="text-lg font-bold text-slate-950">Riwayat pengukuran</h2>
              <div className="mt-5 grid gap-4">{detail.checks.slice().reverse().map((check) => <article key={check.growth_check_id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-bold text-slate-950">{check.source === "mother" ? "Submission keluarga" : "Verifikasi kader"}</p><p className="mt-1 text-xs text-slate-500">{new Date(check.measured_at).toLocaleString("id-ID")}</p></div><StatusBadge value={check.verification_status} /></div><dl className="mt-4 grid grid-cols-3 gap-3 text-sm"><div><dt className="text-slate-500">Berat</dt><dd className="mt-1 font-bold">{check.weight_kg.toFixed(1)} kg</dd></div><div><dt className="text-slate-500">Panjang</dt><dd className="mt-1 font-bold">{check.length_cm ? `${check.length_cm.toFixed(1)} cm` : "-"}</dd></div><div><dt className="text-slate-500">HAZ</dt><dd className="mt-1 font-bold">{check.haz == null ? "-" : check.haz.toFixed(2)}</dd></div></dl></article>)}</div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <h2 className="text-lg font-bold text-slate-950">Catatan kasus</h2>
              <div className="mt-5 grid gap-4">{detail.actions.map((item) => <div key={item.action_id} className="border-l-2 border-blue-300 pl-4"><div className="flex flex-wrap justify-between gap-2"><p className="font-bold text-slate-900">{labelForCode(item.action_type)}</p><time className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString("id-ID")}</time></div>{item.notes && <p className="mt-1 text-sm leading-6 text-slate-600">{item.notes}</p>}</div>)}</div>
            </section>
          </div>

          <section className="h-fit rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <h2 className="text-lg font-bold text-slate-950">Keputusan ahli gizi</h2>
            {!['verified_risk', 'referred'].includes(detail.case.status) ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">Kasus belum siap untuk keputusan atau sudah selesai.</p> : (
              <form onSubmit={submit} className="mt-5 grid gap-4">
                {detail.case.status === "verified_risk" && <div className="grid grid-cols-2 rounded-xl bg-slate-100 p-1 text-sm"><button type="button" onClick={() => setMode("decision")} className={`rounded-lg px-3 py-2 font-bold ${mode === "decision" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"}`}>Intervensi</button><button type="button" onClick={() => setMode("referral")} className={`rounded-lg px-3 py-2 font-bold ${mode === "referral" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"}`}>Rujukan</button></div>}
                {mode === "decision" || detail.case.status === "referred" ? <label className="grid gap-2 text-sm font-semibold">Aksi<input required value={action} onChange={(event) => setAction(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-3 py-3 font-normal" placeholder="Contoh: konseling pemberian makan" /></label> : <label className="grid gap-2 text-sm font-semibold">Tujuan rujukan<input required value={destination} onChange={(event) => setDestination(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-3 py-3 font-normal" placeholder="Contoh: Poli Gizi Puskesmas" /></label>}
                <label className="grid gap-2 text-sm font-semibold">Catatan<textarea rows={5} value={notes} onChange={(event) => setNotes(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-3 py-3 font-normal" /></label>
                <button disabled={busy} className="focus-ring rounded-xl bg-blue-800 px-4 py-3 font-bold text-white hover:bg-blue-900 disabled:opacity-60">{busy ? "Menyimpan..." : mode === "referral" && detail.case.status !== "referred" ? "Simpan rujukan" : "Simpan dan selesaikan"}</button>
              </form>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
