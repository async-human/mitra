import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { MitraChat } from "./MitraChat";
import { isWhitelisted } from "@/lib/quota";

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

async function checkCandidateQuota(email: string): Promise<boolean> {
  if (isWhitelisted(email)) return false;
  const apiBase = (
    process.env.MITRA_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8080"
  ).replace(/\/$/, "");
  try {
    const res = await fetch(
      `${apiBase}/candidate/quota-status?session_id=${encodeURIComponent(email)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data.quota_exhausted);
  } catch {
    return false;
  }
}

function QuotaExceededView({ email }: { email: string }) {
  return (
    <div className="quota-gate-page">
      <div className="quota-gate-card">
        <div className="quota-gate-icon" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="11" stroke="currentColor" strokeWidth="1.6" />
            <path d="M14 8v7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="14" cy="19" r="1.2" fill="currentColor" />
          </svg>
        </div>
        <h1 className="quota-gate-title">You&apos;ve used your free conversation</h1>
        <p className="quota-gate-sub">
          During our early access, each account gets one full chat session with Mitra.
          Your recommendations and any intros you requested are still saved.
        </p>
        <p className="quota-gate-sub" style={{ marginTop: 8 }}>
          Want more? We&apos;re opening expanded access soon —{" "}
          <a
            href="mailto:hello@mitralabs.co?subject=Early access request"
            className="quota-gate-link"
          >
            reach out
          </a>{" "}
          and we&apos;ll prioritise you.
        </p>
        <div className="quota-gate-actions">
          <Link href="/dashboard" className="quota-gate-btn-primary">
            View my dashboard →
          </Link>
          <a
            href="mailto:hello@mitralabs.co?subject=Early access request&body=My email: {email}"
            className="quota-gate-btn-ghost"
          >
            Request more access
          </a>
        </div>
        <p className="quota-gate-fine">
          Signed in as <strong style={{ fontWeight: 500 }}>{email}</strong>
        </p>
      </div>
    </div>
  );
}

export default async function ChatPage({ searchParams }: Props) {
  const [session, params] = await Promise.all([auth(), searchParams]);
  if (!session?.user) redirect("/sign-in");

  const email = session.user.email!;
  const quotaExhausted = await checkCandidateQuota(email);
  if (quotaExhausted) {
    return <QuotaExceededView email={email} />;
  }

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
      userEmail={email}
      userImage={session.user.image ?? undefined}
      intent={params.intent}
      strengthenIntro={strengthenIntro}
    />
  );
}
