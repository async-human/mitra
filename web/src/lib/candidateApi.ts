/** Shared helpers for candidate-facing API calls from the Next.js app. */

export function getCandidateApiBase(): string {
  return (
    process.env.MITRA_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8080"
  ).replace(/\/$/, "");
}

/** Upsert the signed-in candidate in Postgres (idempotent). */
export async function registerCandidateSession(
  email: string,
  userName?: string | null,
): Promise<void> {
  if (!email.includes("@")) return;

  const apiBase = getCandidateApiBase();
  try {
    await fetch(`${apiBase}/candidate/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: email,
        user_name: userName?.trim() || undefined,
      }),
      cache: "no-store",
    });
  } catch {
    // Non-critical — chat/resume flows still create the row later.
  }
}
