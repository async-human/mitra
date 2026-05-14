import type { Metadata } from "next";
import { auth } from "@/auth";
import { FounderPortalClient } from "./FounderPortalClient";

export const metadata: Metadata = {
  title: "Founder Portal · Mitra",
  description: "Review candidates introduced by Mitra for your open role.",
};

export default async function FounderPortalPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const params = await searchParams;
  const token = params.token ?? "";
  const session = await auth();
  const sessionUser = session?.user?.email
    ? {
        name: session.user.name,
        email: session.user.email,
        image: session.user.image,
      }
    : undefined;
  return <FounderPortalClient token={token} sessionUser={sessionUser} />;
}
