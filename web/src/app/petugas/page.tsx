"use client";

import Link from "next/link";

const dummyChildren = [
  { id: 1, name: "Ani (3 th 2 bln)", score: 0.91, risk: "Tinggi", lastVisit: "2 hari lalu" },
  { id: 2, name: "Budi (2 th 8 bln)", score: 0.84, risk: "Tinggi", lastVisit: "kemarin" },
  { id: 3, name: "Citra (1 th 5 bln)", score: 0.62, risk: "Sedang", lastVisit: "3 hari lalu" },
  { id: 4, name: "Dedi (4 th 0 bln)", score: 0.41, risk: "Rendah", lastVisit: "minggu lalu" },
];

export default function PetugasPage() {
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
          <h1 className="text-xl font-bold text-leaf-900">Prioritas Intervensi</h1>
          <p className="text-sm text-leaf-700">Mode Petugas Gizi</p>
        </div>
      </header>

      <section className="mb-4 rounded-2xl bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between text-sm">
          <span className="text-leaf-700">Total balita dipantau</span>
          <span className="font-semibold">124</span>
        </div>
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className="text-leaf-700">Butuh tindak lanjut hari ini</span>
          <span className="font-semibold text-red-600">18</span>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-leaf-700">
          Urutan prioritas
        </h2>
        <ul className="space-y-3">
          {dummyChildren.map((child, idx) => (
            <li
              key={child.id}
              className="flex items-center gap-4 rounded-2xl bg-white p-4 shadow-sm"
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-leaf-100 text-sm font-bold text-leaf-700">
                {idx + 1}
              </span>
              <div className="flex-1">
                <p className="font-semibold text-leaf-900">{child.name}</p>
                <p className="text-xs text-leaf-700/70">{child.lastVisit}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-leaf-900">
                  {(child.score * 100).toFixed(0)}%
                </p>
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    child.risk === "Tinggi"
                      ? "bg-red-100 text-red-700"
                      : child.risk === "Sedang"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-leaf-100 text-leaf-700"
                  }`}
                >
                  {child.risk}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
