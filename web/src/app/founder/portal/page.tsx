import type { Metadata } from "next";
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
  return <FounderPortalClient token={token} />;
}
