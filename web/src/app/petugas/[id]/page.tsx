"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Visit = {
  visit_id: string;
  age_days: number;
  mode: string;
  length_cm: number | null;
  confidence: number;
  haz: number | null;
  qc_reasons: string[];
  measured_at: string;
};

type ShapFactor = {
  feature: string;
  label: string;
  value: number;
  shap_value: number;
  direction: string;
};

type ChildDetail = {
  child_id: string;
  name: string;
  sex: string;
  age_days: number;
  score: number;
  risk_label: string;
  latest_haz: number | null;
  top_factors: ShapFactor[];
  visits: Visit[];
  disclaimer: string;
};

function daysToAgeLabel(d: number): string {
  const years = Math.floor(d / 365);
  const months = Math.floor((d % 365) / 30);
  if (years > 0) return `${years} th ${months} bln`;
  return `${months} bln`;
}

function hazLabel(haz: number): string {
  if (haz < -3) return "Sangat pendek";
  if (haz < -2) return "Pendek (stunted)";
  if (haz < -1) return "Berisiko pendek";
  return "Normal";
}

function riskColor(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("tinggi") || l.includes("high"))
    return "bg-red-100 text-red-700";
  if (l.includes("sedang") || l.includes("medium"))
    return "bg-yellow-100 text-yellow-700";
  return "bg-leaf-100 text-leaf-700";
}

/* Simple horizontal SHAP bar */
function ShapBar({ factor, maxAbs }: { factor: ShapFactor; maxAbs: number }) {
  const pct = maxAbs > 0 ? (Math.abs(factor.shap_value) / maxAbs) * 100 : 0;
  const isPositive = factor.shap_value > 0;
  const isNeutral = Math.abs(factor.shap_value) < 0.001;
  const barColor = isNeutral
    ? "bg-gray-300"
    : isPositive
      ? "bg-red-400"
      : "bg-green-400";
  const label = isNeutral
    ? "netral"
    : isPositive
      ? "menaikkan risiko"
      : "menurunkan risiko";

  return (
    <div className="mb-3">
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="font-medium text-leaf-800">{factor.label}</span>
        <span className="text-leaf-600">
          {factor.shap_value >= 0 ? "+" : ""}
          {factor.shap_value.toFixed(3)}{" "}
          <span className="text-[10px] text-leaf-500">({label})</span>
        </span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-soil-100">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${Math.max(pct, 4)}%` }}
        />
      </div>
    </div>
  );
}

/* Simple growth table — no heavy chart lib */
function GrowthTable({ visits }: { visits: Visit[] }) {
  if (visits.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-leaf-600">
        Belum ada riwayat kunjungan.
      </p>
    );
  }

  const sorted = [...visits].sort((a, b) => a.age_days - b.age_days);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-leaf-200 text-left text-xs text-leaf-600">
            <th className="pb-2 pr-3 font-medium">Usia</th>
            <th className="pb-2 pr-3 font-medium">Panjang (cm)</th>
            <th className="pb-2 pr-3 font-medium">HAZ</th>
            <th className="pb-2 font-medium">Mode</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((v) => (
            <tr key={v.visit_id} className="border-b border-soil-100">
              <td className="py-2 pr-3 text-leaf-800">
                {daysToAgeLabel(v.age_days)}
              </td>
              <td className="py-2 pr-3 text-leaf-800">
                {v.length_cm != null ? v.length_cm.toFixed(1) : "-"}
              </td>
              <td
                className={`py-2 pr-3 font-medium ${
                  v.haz != null && v.haz < -2 ? "text-red-600" : "text-leaf-800"
                }`}
              >
                {v.haz != null ? v.haz.toFixed(2) : "-"}
              </td>
              <td className="py-2 text-leaf-600 capitalize">{v.mode}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ChildDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [data, setData] = useState<ChildDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    fetch(`${API_URL}/children/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Gagal memuat data (${r.status})`);
        return r.json();
      })
      .then(setData)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Terjadi kesalahan.")
      )
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <main className="min-h-screen px-5 py-6">
        <header className="mb-6 flex items-center gap-3">
          <Link
            href="/petugas"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
          >
            ←
          </Link>
          <div>
            <h1 className="text-xl font-bold text-leaf-900">Detail Anak</h1>
          </div>
        </header>
        <div className="flex items-center justify-center py-20">
          <p className="text-sm text-leaf-600">Memuat detail…</p>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen px-5 py-6">
        <header className="mb-6 flex items-center gap-3">
          <Link
            href="/petugas"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
          >
            ←
          </Link>
          <div>
            <h1 className="text-xl font-bold text-leaf-900">Detail Anak</h1>
          </div>
        </header>
        <div className="rounded-2xl bg-red-50 p-5">
          <p className="text-sm text-red-600">{error || "Data tidak ditemukan."}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-5 py-6">
      <header className="mb-6 flex items-center gap-3">
        <Link
          href="/petugas"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-soil-100 text-soil-700"
        >
          ←
        </Link>
        <div>
          <h1 className="text-xl font-bold text-leaf-900">Detail Anak</h1>
          <p className="text-sm text-leaf-700">{data.child_id}</p>
        </div>
      </header>

      {/* Child info card */}
      <section className="mb-5 rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-leaf-900">
          {data.name || data.child_id}
        </h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-xl bg-soil-50 p-3">
            <span className="block text-xs text-soil-600">Jenis kelamin</span>
            <span className="font-medium">
              {data.sex === "M" ? "Laki-laki" : "Perempuan"}
            </span>
          </div>
          <div className="rounded-xl bg-soil-50 p-3">
            <span className="block text-xs text-soil-600">Usia</span>
            <span className="font-medium">{daysToAgeLabel(data.age_days)}</span>
          </div>
          <div className="rounded-xl bg-soil-50 p-3">
            <span className="block text-xs text-soil-600">Skor risiko</span>
            <span className="text-lg font-bold text-leaf-900">
              {(data.score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="rounded-xl bg-soil-50 p-3">
            <span className="block text-xs text-soil-600">Label risiko</span>
            <span
              className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${riskColor(data.risk_label)}`}
            >
              {data.risk_label}
            </span>
          </div>
          <div className="rounded-xl bg-soil-50 p-3">
            <span className="block text-xs text-soil-600">HAZ terakhir</span>
            <span
              className={`text-lg font-bold ${data.latest_haz != null && data.latest_haz < -2 ? "text-red-600" : "text-leaf-900"}`}
            >
              {data.latest_haz != null ? data.latest_haz.toFixed(2) : "-"}
            </span>
          </div>
          <div className="rounded-xl bg-soil-50 p-3">
            <span className="block text-xs text-soil-600">Status</span>
            <span className="font-medium">
              {data.latest_haz != null ? hazLabel(data.latest_haz) : "-"}
            </span>
          </div>
        </div>
      </section>

      {/* SHAP factors */}
      {data.top_factors.length > 0 && (() => {
        const maxAbs =
          Math.max(...data.top_factors.map((f) => Math.abs(f.shap_value)), 0.01);
        return (
          <section className="mb-5 rounded-2xl bg-white p-5 shadow-sm">
            <h2 className="mb-4 font-semibold text-leaf-900">
              Faktor Penentu Risiko
            </h2>
            {data.top_factors.map((f, i) => (
              <ShapBar key={i} factor={f} maxAbs={maxAbs} />
            ))}
            <p className="mt-2 text-[11px] text-leaf-500">
              Bar merah = menaikkan risiko, hijau = menurunkan risiko, abu-abu =
              netral.
            </p>
          </section>
        );
      })()}

      {/* Visit history / growth chart */}
      <section className="mb-5 rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="mb-4 font-semibold text-leaf-900">
          Riwayat Pertumbuhan
        </h2>
        <GrowthTable visits={data.visits} />
      </section>

      {/* Disclaimer */}
      {data.disclaimer && (
        <section className="rounded-2xl bg-soil-100 p-4">
          <p className="text-xs text-soil-700">{data.disclaimer}</p>
        </section>
      )}
    </main>
  );
}
