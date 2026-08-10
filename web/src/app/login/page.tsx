"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { demoLogin, login, registerMother, roleHome, saveSession } from "@/lib/api";
import type { AuthResponse, Role } from "@/lib/types";

const SproutScene = dynamic(() => import("@/components/SproutScene"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full animate-pulse rounded-2xl bg-blue-900/20" />
  ),
});

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [scopeKey, setScopeKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [demoRole, setDemoRole] = useState<Role | null>(null);
  const [error, setError] = useState("");

  const completeAuth = (auth: AuthResponse) => {
    const session = saveSession(auth);
    router.replace(roleHome(session.role));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const auth = mode === "login"
        ? await login(name, password, scopeKey)
        : await registerMother(name, password, scopeKey);
      completeAuth(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tidak dapat masuk.");
    } finally {
      setBusy(false);
    }
  };

  const loginAsDemo = async (role: Role) => {
    setBusy(true);
    setDemoRole(role);
    setError("");
    try {
      completeAuth(await demoLogin(role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tidak dapat masuk sebagai akun demo.");
    } finally {
      setBusy(false);
      setDemoRole(null);
    }
  };

  const demoAccounts: Array<{ role: Role; label: string; initial: string }> = [
    { role: "mother", label: "Ibu Demo", initial: "I" },
    { role: "kader", label: "Kader Demo", initial: "K" },
    { role: "nutritionist", label: "Ahli Gizi Demo", initial: "A" },
  ];

  return (
    <main className="grid min-h-[100dvh] place-items-center bg-[#eef2f8] px-4 py-4 sm:py-8">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_24px_70px_rgba(29,48,85,0.12)] lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative min-h-[280px] overflow-hidden bg-gradient-to-br from-blue-950 via-blue-900 to-blue-700 p-6 text-white sm:min-h-[320px] sm:p-8 lg:min-h-[680px] lg:p-10">
          <Link href="/" className="focus-ring relative z-20 flex w-fit items-center gap-3 rounded-xl">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-white font-black text-blue-900 shadow-lg shadow-blue-950/20">T</span>
            <span className="font-bold">Tunas</span>
          </Link>

          <div className="relative z-10 mt-7 max-w-[190px] sm:mt-9 sm:max-w-xs lg:mt-12">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-blue-200 sm:text-xs">
              Pemantauan 0-23 bulan
            </p>
            <h1 className="mt-2 text-xl font-bold leading-tight tracking-tight sm:mt-3 sm:text-3xl lg:text-4xl">
              Tumbuh bersama, dipantau bersama.
            </h1>
            <p className="mt-3 hidden text-sm leading-6 text-blue-100 sm:block">
              Satu alur untuk keluarga, kader, dan ahli gizi.
            </p>
          </div>

          <div className="pointer-events-none absolute -bottom-16 -left-16 h-52 w-52 rounded-full bg-blue-400/10 blur-3xl" />
          <SproutScene className="absolute -right-[12%] bottom-0 left-[28%] h-[230px] sm:-right-[6%] sm:left-[35%] sm:h-[290px] lg:inset-x-0 lg:h-[470px]" />
        </section>

        <section className="flex items-center p-6 sm:p-8 lg:p-10">
          <div className="w-full">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">
                  Portal Tunas
                </p>
                <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
                  {mode === "login" ? "Masuk ke ruang kerja" : "Buat akun keluarga"}
                </h2>
              </div>
              <div className="flex shrink-0 rounded-xl bg-slate-100 p-1 text-sm">
                <button disabled={busy} type="button" onClick={() => setMode("login")} className={`rounded-lg px-3 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-60 ${mode === "login" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"}`}>Masuk</button>
                <button disabled={busy} type="button" onClick={() => setMode("register")} className={`rounded-lg px-3 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-60 ${mode === "register" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"}`}>Daftar ibu</button>
              </div>
            </div>

            <p className="mt-3 text-sm leading-6 text-slate-600">
              Akun kader dan ahli gizi dibuat oleh pengelola demo.
            </p>

            <form onSubmit={submit} className="mt-7 grid gap-5">
              <label className="grid gap-2 text-sm font-semibold text-slate-800">
                Nama akun
                <input disabled={busy} required value={name} onChange={(event) => setName(event.target.value)} className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal text-slate-950 placeholder:text-slate-500 disabled:cursor-not-allowed disabled:bg-slate-50" placeholder="Contoh: Ibu Ani" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-800">
                Scope Posyandu
                <input disabled={busy} required value={scopeKey} onChange={(event) => setScopeKey(event.target.value)} className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal text-slate-950 placeholder:text-slate-500 disabled:cursor-not-allowed disabled:bg-slate-50" placeholder="Contoh: posyandu-a" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-slate-800">
                Kata sandi
                <input disabled={busy} required minLength={mode === "register" ? 8 : 1} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-50" />
              </label>
              {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
              <button disabled={busy} className="focus-ring rounded-xl bg-blue-800 px-5 py-3 font-bold text-white transition hover:bg-blue-900 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60">
                {busy ? "Memproses..." : mode === "login" ? "Masuk" : "Buat akun"}
              </button>
            </form>

            <div className="mt-7 hidden border-t border-slate-200 pt-6 lg:block">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-bold text-slate-950">Quick login demo</p>
                  <p className="mt-1 text-xs text-slate-500">Pilih role untuk langsung masuk.</p>
                </div>
                <span className="rounded-full bg-blue-50 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-blue-700">Desktop</span>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                {demoAccounts.map((account) => (
                  <button
                    key={account.role}
                    type="button"
                    disabled={busy}
                    aria-label={`Masuk sebagai ${account.label}`}
                    onClick={() => loginAsDemo(account.role)}
                    className="focus-ring group grid min-h-24 place-items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-2 py-3 text-center transition hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="grid h-9 w-9 place-items-center rounded-xl bg-blue-800 text-sm font-black text-white transition group-hover:bg-blue-900">
                      {account.initial}
                    </span>
                    <span className="text-xs font-bold leading-4 text-slate-800">
                      {demoRole === account.role ? "Memproses..." : account.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
