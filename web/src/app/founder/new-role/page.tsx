import { auth } from "@/auth";
import { redirect } from "next/navigation";
import type { Metadata } from "next";
import { FounderJobBuilder } from "./FounderJobBuilder";

export const metadata: Metadata = { title: "Post a role · Mitra" };

export default async function FounderNewRolePage() {
  const session = await auth();
  if (!session?.user?.email) redirect("/sign-in?role=founder");

  return (
    <FounderJobBuilder
      authEmail={session.user.email}
      founderName={session.user.name?.split(" ")[0] ?? ""}
    />
  );
}
