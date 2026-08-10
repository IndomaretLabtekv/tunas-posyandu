import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-leaf-500 shadow-lg">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            className="h-10 w-10 text-white"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 22v-9" />
            <path d="M12 13a7 7 0 0 1 7-7h0a7 7 0 0 1-7 7Z" />
            <path d="M12 13a7 7 0 0 0-7-7h0a7 7 0 0 0 7 7Z" />
            <path d="M12 22a9 9 0 0 0 9-9h-2a7 7 0 0 1-7 7v2Z" />
            <path d="M12 22a9 9 0 0 1-9-9h2a7 7 0 0 0 7 7v2Z" />
          </svg>
        </div>
        <h1 className="mb-2 text-3xl font-bold tracking-tight text-leaf-900">
          Tunas
        </h1>
        <p className="mb-10 text-leaf-700">
          Ukur tumbuhnya. Dahulukan yang perlu.
        </p>

        <div className="grid gap-4">
          <Link
            href="/kader"
            className="group rounded-2xl bg-leaf-500 px-6 py-5 text-left text-white shadow transition active:scale-[0.98]"
          >
            <span className="block text-sm font-medium opacity-90">Mode</span>
            <span className="block text-xl font-semibold">Kader Posyandu</span>
            <span className="mt-1 block text-sm opacity-90">
              Ambil foto dan ukur pertumbuhan balita
            </span>
          </Link>

          <Link
            href="/petugas"
            className="group rounded-2xl bg-soil-500 px-6 py-5 text-left text-white shadow transition active:scale-[0.98]"
          >
            <span className="block text-sm font-medium opacity-90">Mode</span>
            <span className="block text-xl font-semibold">Petugas Gizi</span>
            <span className="mt-1 block text-sm opacity-90">
              Lihat prioritas intervensi dan penjelasan
            </span>
          </Link>
        </div>

        <p className="mt-8 text-xs text-leaf-700/70">
          Decision-support tool. Keputusan medis tetap di tangan tenaga kesehatan.
        </p>
      </div>
    </main>
  );
}
