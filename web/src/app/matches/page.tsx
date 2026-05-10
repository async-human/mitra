import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { MatchesView } from "./MatchesView";

export const metadata: Metadata = { title: "Your Matches · Mitra" };

export default async function MatchesPage() {
  const session = await auth();
  if (!session?.user) redirect("/sign-in");
  return <MatchesView userName={session.user.name ?? undefined} />;
}
