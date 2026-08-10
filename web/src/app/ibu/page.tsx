"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppShell, InlineError, LoadingBlock, StatusBadge } from "@/components/AppShell";
import { createChild, listMotherChildren, submitGrowthCheck } from "@/lib/api";
import type { GrowthCheck, MotherChild } from "@/lib/types";
import { useRoleSession } from "@/lib/useRoleSession";

export default function MotherPage() {
  const session = useRoleSession("mother");
  const [children, setChildren] = useState<MotherChild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GrowthCheck | null>(null);
  const [selectedChild, setSelectedChild] = useState("");
  const [weight, setWeight] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [childForm, setChildForm] = useState({ name: "", sex: "F" as "M" | "F", birth_date: "" });

  const refresh = () => {
    setLoading(true);
    listMotherChildren()
      .then((items) => {
        setChildren(items);
        if (!selectedChild && items[0]) setSelectedChild(String(items[0].child_id));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Gagal memuat data."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (session) refresh();
  }, [session]);

  const addChild = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const child = await createChild(childForm);
      setChildForm({ name: "", sex: "F", birth_date: "" });
      setSelectedChild(String(child.child_id));
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anak tidak dapat ditambahkan.");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!image || !selectedChild) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const check = await submitGrowthCheck(Number(selectedChild), Number(weight), image);
      setResult(check);
      setWeight("");
      setImage(null);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pemeriksaan tidak dapat dikirim.");
    } finally {
      setBusy(false);
    }
  };

  if (!session) return <main className="min-h-[100dvh] bg-[#f4f6fa]" />;

  return (
    <AppShell title="Ruang keluarga" description="Kirim pemeriksaan bulanan dan pantau status verifikasi untuk setiap anak.">
      {error && <div className="mb-5"><InlineError message={error} /></div>}
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-slate-950">Anak terdaftar</h2>
            <span className="text-sm font-semibold text-slate-500">{children.length}</span>
          </div>
          <div className="mt-5">
            {loading ? <LoadingBlock /> : children.length === 0 ? (
              <p className="rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">Belum ada anak. Tambahkan profil pertama di bawah.</p>
            ) : (
              <div className="grid gap-3">
                {children.map((child) => (
                  <Link key={child.child_id} href={`/ibu/children/${child.child_id}`} className="focus-ring rounded-xl border border-slate-200 p-4 transition hover:border-blue-300 hover:bg-blue-50/40">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-bold text-slate-950">{child.name}</p>
                        <p className="mt-1 text-sm text-slate-600">Lahir {new Date(child.birth_date).toLocaleDateString("id-ID")}</p>
                      </div>
                      <span className="text-sm font-bold text-blue-800">Lihat riwayat</span>
                    </div>
                    <p className="mt-3 text-xs text-slate-500">Pemeriksaan berikutnya: {child.next_due_at ? new Date(child.next_due_at).toLocaleDateString("id-ID") : "belum dijadwalkan"}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <form onSubmit={addChild} className="mt-7 border-t border-slate-200 pt-6">
            <h3 className="font-bold text-slate-900">Tambah profil anak</h3>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-slate-800 sm:col-span-2">Nama anak<input required value={childForm.name} onChange={(event) => setChildForm({ ...childForm, name: event.target.value })} className="focus-ring rounded-xl border border-slate-300 px-4 py-3 font-normal" /></label>
              <label className="grid gap-2 text-sm font-semibold text-slate-800">Jenis kelamin<select value={childForm.sex} onChange={(event) => setChildForm({ ...childForm, sex: event.target.value as "M" | "F" })} className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal"><option value="F">Perempuan</option><option value="M">Laki-laki</option></select></label>
              <label className="grid gap-2 text-sm font-semibold text-slate-800">Tanggal lahir<input required type="date" value={childForm.birth_date} onChange={(event) => setChildForm({ ...childForm, birth_date: event.target.value })} className="focus-ring rounded-xl border border-slate-300 px-4 py-3 font-normal" /></label>
            </div>
            <button disabled={busy} className="focus-ring mt-4 rounded-xl border border-blue-800 px-4 py-3 text-sm font-bold text-blue-800 disabled:opacity-60">Simpan profil</button>
          </form>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <h2 className="text-lg font-bold text-slate-950">Pemeriksaan bulan ini</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">Foto diproses sementara. Sistem hanya menyimpan hasil terstruktur.</p>
          <form onSubmit={submit} className="mt-6 grid gap-5">
            <label className="grid gap-2 text-sm font-semibold text-slate-800">Pilih anak<select required value={selectedChild} onChange={(event) => setSelectedChild(event.target.value)} className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal"><option value="">Pilih profil</option>{children.map((child) => <option key={child.child_id} value={child.child_id}>{child.name}</option>)}</select></label>
            <label className="grid gap-2 text-sm font-semibold text-slate-800">Berat badan (kg)<input required min="0.1" step="0.1" type="number" value={weight} onChange={(event) => setWeight(event.target.value)} className="focus-ring rounded-xl border border-slate-300 px-4 py-3 font-normal" /></label>
            <label className="grid gap-2 text-sm font-semibold text-slate-800">Foto pengukuran<input required type="file" accept="image/*" capture="environment" onChange={(event) => setImage(event.target.files?.[0] || null)} className="focus-ring rounded-xl border border-dashed border-slate-400 bg-slate-50 px-4 py-6 text-sm font-normal file:mr-4 file:rounded-lg file:border-0 file:bg-blue-800 file:px-3 file:py-2 file:font-bold file:text-white" /><span className="font-normal leading-5 text-slate-500">Anak telentang, seluruh alas terlihat, dan cahaya cukup.</span></label>
            <button disabled={busy || children.length === 0} className="focus-ring rounded-xl bg-blue-800 px-5 py-3 font-bold text-white hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-60">{busy ? "Memproses..." : "Kirim pemeriksaan"}</button>
          </form>

          {result && (
            <div className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-bold text-slate-950">Hasil diterima</h3><StatusBadge value={result.screening_status} /></div>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div><dt className="text-slate-500">Panjang</dt><dd className="mt-1 font-bold text-slate-950">{result.length_cm ? `${result.length_cm.toFixed(1)} cm` : "Tidak tersedia"}</dd></div>
                <div><dt className="text-slate-500">Kepercayaan</dt><dd className="mt-1 font-bold text-slate-950">{Math.round(result.confidence * 100)}%</dd></div>
              </dl>
              <p className="mt-4 text-sm leading-6 text-slate-700">{result.screening_status === "needs_review" ? "Indikasi gangguan pertumbuhan atau kualitas ukur memerlukan verifikasi kader." : "Hasil skrining tercatat. Pemeriksaan berikutnya dijadwalkan 30 hari lagi."}</p>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
