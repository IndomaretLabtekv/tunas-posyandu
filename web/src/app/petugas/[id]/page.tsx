import { redirect } from "next/navigation";

export default async function LegacyPetugasDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/ahli-gizi/${id}`);
}
