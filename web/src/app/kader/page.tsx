"use client";

import Link from "next/link";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type MeasurementResult = {
  mode: string;
  length_cm: number | null;
  confidence: number;
  low_confidence: boolean;
  qc_reasons: string[];
  haz: number | null;
  child_id: string;
  visit_id: string;
};

export default function KaderPage() {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [sex, setSex] = useState<"M" | "F">("M");
  const [ageDays, setAgeDays] = useState("");
  const [status, setStatus] = useState<
    "idle" | "uploading" | "done" | "error"
  >("idle");
  const [result, setResult] = useState<MeasurementResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const handleSubmit = async () => {
    if (!file) return;
    if (!ageDays || isNaN(Number(ageDays)) || Number(ageDays) <= 0) {
      setErrorMsg("Masukkan usia balita dalam hari (angka positif).");
      return;
    }
    setStatus("uploading");
    setErrorMsg("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", file);
    formData.append("sex", sex);
    formData.append("age_days", String(Math.round(Number(ageDays))));
    if (name.trim()) formData.append("name", name.trim());

    try {
      const res = await fetch(`${API_URL}/measurements`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => "");
        throw new Error(errText || `Server error (${res.status})`);
      }
      const data: MeasurementResult = await res.json();
      setResult(data);
      setStatus("done");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Terjadi kesalahan.";
      setErrorMsg(msg);
      setStatus("error");
    }
  };

  const hazLabel = (haz: number) => {
    if (haz < -3) return "Sangat pendek (severely stunted)";
    if (haz < -2) return "Pendek (stunted)";
    if (haz < -1) return "Berisiko pendek";
    return "Normal";
  };

  return (
    <main className="min-h-screen px-5 py-6">
      <header className="mb-6 flex items-center gap-3">
        <Link
          href="/"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-leaf-100 text-leaf-700"
        >
          ←
        </Link>
        <div>
          <h1 className="text-xl font-bold text-leaf-900">Pengukuran Balita</h1>
          <p className="text-sm text-leaf-700">Mode Kader Posyandu</p>
        </div>
      </header>

      {/* Input form */}
      <section className="mb-5 space-y-4 rounded-2xl bg-white p-5 shadow-sm">
        <div>
          <label className="mb-1 block text-sm font-medium text-leaf-800">
            Nama balita (opsional)
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="cth: Ani"
            className="w-full rounded-xl border border-leaf-200 bg-soil-50 px-4 py-2.5 text-sm text-leaf-900 placeholder:text-leaf-400 focus:border-leaf-500 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-leaf-800">
              Jenis kelamin
            </label>
            <div className="flex gap-2">
              {(["M", "F"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSex(s)}
                  className={`flex-1 rounded-xl border-2 py-2.5 text-sm font-medium transition ${
                    sex === s
                      ? "border-leaf-500 bg-leaf-100 text-leaf-800"
                      : "border-leaf-200 bg-soil-50 text-leaf-600"
                  }`}
                >
                  {s === "M" ? "Laki-laki" : "Perempuan"}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-leaf-800">
              Usia (hari)
            </label>
            <input
              type="number"
              min="1"
              value={ageDays}
              onChange={(e) => setAgeDays(e.target.value)}
              placeholder="cth: 365"
              className="w-full rounded-xl border border-leaf-200 bg-soil-50 px-4 py-2.5 text-sm text-leaf-900 placeholder:text-leaf-400 focus:border-leaf-500 focus:outline-none"
            />
          </div>
        </div>
      </section>

      {/* Photo upload */}
      <section className="rounded-2xl border-2 border-dashed border-leaf-300 bg-white p-6 text-center">
        {preview ? (
          <img
            src={preview}
            alt="Preview"
            className="mx-auto mb-4 h-48 w-full rounded-xl object-cover"
          />
        ) : (
          <div className="mx-auto mb-4 flex h-32 w-32 items-center justify-center rounded-full bg-leaf-50 text-4xl">
            📷
          </div>
        )}

        <label className="mr-2 inline-block cursor-pointer rounded-xl bg-leaf-500 px-5 py-3 font-medium text-white active:scale-[0.98]">
          {preview ? "Ganti foto" : "Ambil / unggah foto"}
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleFile}
          />
        </label>

        {file && (
          <button
            onClick={handleSubmit}
            disabled={status === "uploading"}
            className="rounded-xl bg-soil-500 px-5 py-3 font-medium text-white active:scale-[0.98] disabled:opacity-50"
          >
            {status === "uploading" ? "Memproses..." : "Ukur"}
          </button>
        )}

        <p className="mt-3 text-xs text-leaf-700/70">
          Pastikan balita terbaring di alas marker ArUco dan pencahayaan cukup.
        </p>
      </section>

      {/* Error */}
      {status === "error" && (
        <section className="mt-5 rounded-2xl bg-red-50 p-5 shadow-sm">
          <h2 className="mb-2 font-semibold text-red-700">Terjadi Kesalahan</h2>
          <p className="text-sm text-red-600">{errorMsg}</p>
          <p className="mt-2 text-xs text-red-500">
            Jika foto ditolak, coba masukkan hasil ukur manual ke petugas gizi.
          </p>
        </section>
      )}

      {/* Result */}
      {status === "done" && result && (
        <section className="mt-6 space-y-4">
          <div className="rounded-2xl bg-white p-5 shadow-sm">
            <h2 className="mb-3 font-semibold text-leaf-900">Hasil Pengukuran</h2>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-soil-50 p-3">
                <span className="block text-xs text-soil-600">Mode</span>
                <span className="text-base font-semibold capitalize">
                  {result.mode}
                </span>
              </div>
              <div className="rounded-xl bg-soil-50 p-3">
                <span className="block text-xs text-soil-600">Panjang badan</span>
                <span className="text-lg font-semibold">
                  {result.length_cm != null ? `${result.length_cm.toFixed(1)} cm` : "-"}
                </span>
              </div>
              <div className="rounded-xl bg-soil-50 p-3">
                <span className="block text-xs text-soil-600">HAZ</span>
                <span className="text-lg font-semibold">
                  {result.haz != null ? result.haz.toFixed(2) : "-"}
                </span>
              </div>
              <div className="rounded-xl bg-soil-50 p-3">
                <span className="block text-xs text-soil-600">Kepercayaan</span>
                <span className="text-lg font-semibold">
                  {(result.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <p className="mt-3 text-xs text-leaf-700/70">
              Status: {result.haz != null ? hazLabel(result.haz) : "-"}
            </p>
          </div>

          {/* QC reasons */}
          {result.qc_reasons.length > 0 && (
            <div className="rounded-2xl bg-yellow-50 p-5 shadow-sm">
              <h3 className="mb-2 text-sm font-semibold text-yellow-800">
                Catatan Kualitas Foto
              </h3>
              <ul className="list-inside list-disc text-sm text-yellow-700">
                {result.qc_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Low confidence fallback */}
          {result.low_confidence && (
            <div className="rounded-2xl bg-red-50 p-5 shadow-sm">
              <h3 className="mb-2 text-sm font-semibold text-red-700">
                Kepercayaan Rendah
              </h3>
              <p className="text-sm text-red-600">
                Hasil estimasi dari foto ini kurang akurat. Disarankan untuk
                mengukur ulang dengan pencahayaan lebih baik, atau masukkan
                hasil ukur manual melalui petugas gizi.
              </p>
            </div>
          )}

          {result.child_id && (
            <p className="text-center text-xs text-leaf-700/50">
              ID Anak: {result.child_id} · Kunjungan: {result.visit_id}
            </p>
          )}
        </section>
      )}
    </main>
  );
}
