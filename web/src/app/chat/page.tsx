import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { MitraChat } from "./MitraChat";

export const metadata: Metadata = {
  title: "Chat with Mitra",
};

type Props = {
  searchParams: Promise<{
    intent?: string;
    job_id?: string;
    company?: string;
    role?: string;
    missing?: string;
  }>;
};

export default async function ChatPage({ searchParams }: Props) {
  const [session, params] = await Promise.all([auth(), searchParams]);
  if (!session?.user) redirect("/sign-in");

  const strengthenIntro =
    params.intent === "strengthen_intro" && params.job_id
      ? {
          jobId: params.job_id,
          company: params.company ?? "",
          role: params.role ?? "",
          missing: (params.missing ?? "")
            .split("|")
            .map((s) => s.trim())
            .filter(Boolean),
        }
      : undefined;

  return (
    <MitraChat
      userName={session.user.name ?? undefined}
      userEmail={session.user.email!}
      userImage={session.user.image ?? undefined}
      intent={params.intent}
      strengthenIntro={strengthenIntro}
    />
  );
}
