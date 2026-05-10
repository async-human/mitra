import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { MatchesView } from "./MatchesView";

export const metadata: Metadata = { title: "Your Matches · Mitra" };

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: Promise<{ ids?: string }>;
}) {
  const session = await auth();
  if (!session?.user) redirect("/sign-in");
  const params = await searchParams;
  return <MatchesView userName={session.user.name ?? undefined} userEmail={session.user.email ?? undefined} urlIds={params.ids} />;
}
