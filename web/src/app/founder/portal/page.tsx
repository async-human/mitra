import type { Metadata } from "next";
import { FounderPortalClient } from "./FounderPortalClient";

export const metadata: Metadata = {
  title: "Founder Portal · Mitra",
  description: "Review candidates introduced by Mitra for your open role.",
};

export default function FounderPortalPage({
  searchParams,
}: {
  searchParams: { token?: string };
}) {
  const token = searchParams.token ?? "";
  return <FounderPortalClient token={token} />;
}
