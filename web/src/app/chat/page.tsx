import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { MitraChat } from "./MitraChat";

export const metadata: Metadata = {
  title: "Chat with Mitra",
};

export default async function ChatPage() {
  const session = await auth();
  if (!session?.user) redirect("/sign-in");

  return (
    <MitraChat
      userName={session.user.name ?? undefined}
      userEmail={session.user.email!}
      userImage={session.user.image ?? undefined}
    />
  );
}
