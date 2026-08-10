"use client";

import Link from "next/link";
import { useState } from "react";

export default function KaderPage() {
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done">("idle");

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("uploading");
    const url = URL.createObjectURL(file);
    setPreview(url);
    window.setTimeout(() => setStatus("done"), 600);
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

        <label className="inline-block cursor-pointer rounded-xl bg-leaf-500 px-5 py-3 font-medium text-white active:scale-[0.98]">
          {preview ? "Ganti foto" : "Ambil / unggah foto"}
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleFile}
          />
        </label>

        <p className="mt-3 text-xs text-leaf-700/70">
          Pastikan balita terbaring di alas marker ArUco dan pencahayaan cukup.
        </p>
      </section>

      {status === "done" && (
        <section className="mt-6 rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-semibold text-leaf-900">Hasil Sementara</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl bg-soil-50 p-3">
              <span className="block text-xs text-soil-600">Panjang badan</span>
              <span className="text-lg font-semibold">72,4 cm</span>
            </div>
            <div className="rounded-xl bg-soil-50 p-3">
              <span className="block text-xs text-soil-600">HAZ</span>
              <span className="text-lg font-semibold">-1,2</span>
            </div>
          </div>
          <p className="mt-3 text-xs text-leaf-700/70">
            Hasil di atas adalah simulasi UI. Integrasi model CV diimplementasikan
            setelah scaffold selesai.
          </p>
        </section>
      )}
    </main>
  );
}
