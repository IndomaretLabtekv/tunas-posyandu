const LABELS: Record<string, string> = {
  unverified: "Belum diverifikasi",
  verified: "Terverifikasi",
  normal: "Normal",
  needs_review: "Perlu ditinjau",
  assigned: "Ditangani kader",
  home_visit: "Kunjungan rumah",
  verified_risk: "Risiko terverifikasi",
  referred: "Dirujuk",
  resolved: "Selesai",
  urgent: "Mendesak",
  review: "Perlu ditinjau",
  overdue: "Terlambat",
  low_confidence: "Keyakinan hasil pengukuran rendah",
  estimate_mode: "Panjang badan masih berupa estimasi",
  growth_signal: "Pola pertumbuhan memerlukan perhatian",
  cv_rejected: "Foto belum dapat dianalisis",
  assigned_case: "Kasus diambil kader",
};

export function labelForCode(value: string) {
  return LABELS[value] || value.replaceAll("_", " ");
}

export function joinLabels(values: string[]) {
  return values.map(labelForCode).join(", ");
}
