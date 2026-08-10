"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type PriorityChild = {
  rank: number;
  child_id: string;
  name: string;
  sex: string;
  age_days: number;
  score: number;
  risk_label: string;
  latest_haz: number;
  last_visit_days_ago: number;
  top_factors: {
    feature: string;
    label: string;
    value: number;
    shap_value: number;
    direction: string;
  }[];
};

type PriorityResponse = {
  children: PriorityChild[];
  total: number;
};

function daysToAgeLabel(d: number): string {
  const years = Math.floor(d / 365);
  const months = Math.floor((d % 365) / 30);
  if (years > 0) return `${years} th ${months} bln`;
  return `${months} bln`;
}

function riskColor(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("tinggi") || l.includes("high"))
    return "bg-red-100 text-red-700";
  if (l.includes("sedang") || l.includes("medium"))
    return "bg-yellow-100 text-yellow-700";
  return "bg-leaf-100 text-leaf-700";
}

export default function PetugasPage() {
  const [data, setData] = useState<PriorityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/priority`)
      .then((r) => {
        if (!r.ok) throw new Error(`Gagal memuat data (${r.status})`);
        return r.json();
      })
      .then(setData)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Terjadi kesalahan.")
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen px-5 py-6">
        <header className="mb-6 flex items-center gap-3">
          <Link
            href="/"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
          >
            ←
          </Link>
          <div>
            <h1 className="text-xl font-bold text-leaf-900">
              Prioritas Intervensi
            </h1>
            <p className="text-sm text-leaf-700">Mode Petugas Gizi</p>
          </div>
        </header>
        <div className="flex items-center justify-center py-20">
          <p className="text-sm text-leaf-600">Memuat data prioritas…</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen px-5 py-6">
        <header className="mb-6 flex items-center gap-3">
          <Link
            href="/"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
          >
            ←
          </Link>
          <div>
            <h1 className="text-xl font-bold text-leaf-900">
              Prioritas Intervensi
            </h1>
            <p className="text-sm text-leaf-700">Mode Petugas Gizi</p>
          </div>
        </header>
        <div className="rounded-2xl bg-red-50 p-5">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      </main>
    );
  }

  if (!data || data.children.length === 0) {
    return (
      <main className="min-h-screen px-5 py-6">
        <header className="mb-6 flex items-center gap-3">
          <Link
            href="/"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
          >
            ←
          </Link>
          <div>
            <h1 className="text-xl font-bold text-leaf-900">
              Prioritas Intervensi
            </h1>
            <p className="text-sm text-leaf-700">Mode Petugas Gizi</p>
          </div>
        </header>
        <div className="flex items-center justify-center py-20">
          <p className="text-sm text-leaf-600">Belum ada data balita.</p>
        </div>
      </main>
    );
  }

  const highCount = data.children.filter(
    (c) => c.risk_label.toLowerCase().includes("tinggi")
  ).length;

  return (
    <main className="min-h-screen px-5 py-6">
      <header className="mb-6 flex items-center gap-3">
        <Link
          href="/"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
        >
          ←
        </Link>
        <div>
          <h1 className="text-xl font-bold text-leaf-900">
            Prioritas Intervensi
          </h1>
          <p className="text-sm text-leaf-700">Mode Petugas Gizi</p>
        </div>
      </header>

      <section className="mb-4 rounded-2xl bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between text-sm">
          <span className="text-leaf-700">Total balita dipantau</span>
          <span className="font-semibold">{data.total}</span>
        </div>
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className="text-leaf-700">Butuh tindak lanjut hari ini</span>
          <span className="font-semibold text-red-600">{highCount}</span>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-leaf-700">
          Urutan prioritas
        </h2>
        <ul className="space-y-3">
          {data.children.map((child) => (
            <li key={child.child_id}>
              <Link
                href={`/petugas/${child.child_id}`}
                className="flex items-center gap-4 rounded-2xl bg-white p-4 shadow-sm transition active:scale-[0.99]"
              >
                <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-leaf-100 text-sm font-bold text-leaf-700">
                  {child.rank}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-leaf-900">
                    {child.name || child.child_id}
                  </p>
                  <p className="text-xs text-leaf-700/70">
                    {daysToAgeLabel(child.age_days)} · terakhir{" "}
                    {child.last_visit_days_ago === 0
                      ? "hari ini"
                      : `${child.last_visit_days_ago} hari lalu`}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-bold text-leaf-900">
                    {(child.score * 100).toFixed(0)}%
                  </p>
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${riskColor(child.risk_label)}`}
                  >
                    {child.risk_label}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
