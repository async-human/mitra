import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { MitraChat } from "./MitraChat";

export const metadata: Metadata = {
  title: "Chat with Mitra",
};

type Props = { searchParams: Promise<{ intent?: string }> };

export default async function ChatPage({ searchParams }: Props) {
  const [session, params] = await Promise.all([auth(), searchParams]);
  if (!session?.user) redirect("/sign-in");

  return (
    <MitraChat
      userName={session.user.name ?? undefined}
      userEmail={session.user.email!}
      userImage={session.user.image ?? undefined}
      intent={params.intent}
    />
  );
}
