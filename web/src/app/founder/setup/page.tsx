import { auth } from "@/auth";
import { redirect } from "next/navigation";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Setting up your portal · Mitra",
};

/**
 * Smart router for signed-in founders:
 *  - If they already have a job onboarded → redirect to their portal
 *  - Otherwise → send them to the onboarding chat to post a role
 */
export default async function FounderSetupPage() {
  const session = await auth();

  if (!session?.user?.email) {
    redirect("/sign-in?role=founder");
  }

  const email = session.user.email;
  const apiBase = process.env.MITRA_API_BASE_URL ?? "http://localhost:8080";

  let portalUrl: string | null = null;

  try {
    const res = await fetch(
      `${apiBase}/founder/portal-link-by-email?email=${encodeURIComponent(email)}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const data = await res.json();
      portalUrl = data.portal_url ?? null;
    }
  } catch {
    // Network error — treat as no job found, fall through to onboarding
  }

  if (portalUrl) {
    redirect(portalUrl);
  }

  // No existing job → take them through onboarding to post their first role
  redirect("/onboarding");
}
