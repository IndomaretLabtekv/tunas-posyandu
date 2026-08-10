import Link from "next/link";

const roles = [
  {
    name: "Ibu dan keluarga",
    body: "Catat pemeriksaan bulanan, unggah foto, dan pantau tindak lanjut.",
  },
  {
    name: "Kader Posyandu",
    body: "Kelola antrean verifikasi, kunjungan rumah, dan pengukuran ulang.",
  },
  {
    name: "Ahli gizi",
    body: "Tinjau hasil terverifikasi, tentukan aksi, dan catat rujukan.",
  },
];

export default function Home() {
  return (
    <main className="min-h-[100dvh] bg-[#eef2f8] px-4 py-5 sm:px-6 sm:py-8">
      <div className="mx-auto grid min-h-[calc(100dvh-4rem)] max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex flex-col justify-between bg-[#173f9f] p-7 text-white sm:p-10 lg:p-14">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-white text-lg font-black text-blue-900">
              T
            </span>
            <span className="text-lg font-bold tracking-tight">Tunas</span>
          </div>
          <div className="py-16 lg:py-8">
            <p className="mb-4 text-sm font-semibold text-blue-100">Pemantauan pertumbuhan 0-23 bulan</p>
            <h1 className="max-w-xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Satu alur dari rumah sampai Puskesmas.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-blue-100">
              Hasil foto adalah sinyal skrining. Setiap temuan berisiko tetap melalui verifikasi manusia.
            </p>
          </div>
          <p className="text-xs leading-5 text-blue-200">
            Bukan alat diagnosis. Keputusan klinis tetap berada pada tenaga kesehatan.
          </p>
        </section>

        <section className="flex flex-col justify-center p-7 sm:p-10 lg:p-14">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-950">Masuk sesuai peran</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Akun menentukan data dan tindakan yang dapat diakses.
            </p>
          </div>
          <div className="mt-8 grid gap-3">
            {roles.map((role) => (
              <div key={role.name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="font-bold text-slate-900">{role.name}</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">{role.body}</p>
              </div>
            ))}
          </div>
          <Link
            href="/login"
            className="focus-ring mt-7 rounded-xl bg-blue-800 px-5 py-3 text-center font-bold text-white transition hover:bg-blue-900 active:translate-y-px"
          >
            Masuk ke Tunas
          </Link>
        </section>
      </div>
    </main>
  );
}
