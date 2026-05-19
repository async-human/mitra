import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { UserMenu } from "@/app/dashboard/UserMenu";
import styles from "./dashboard.module.css";

export const metadata: Metadata = {
  title: "Dashboard · Mitra",
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface FounderJob {
  job_id: number;
  title: string;
  company: string;
  stage: string | null;
  portal_url: string;
  total_intros: number;
  to_review: number;
}

interface PortalStats {
  total: number;
  interested: number;
  interview: number;
  offer: number;
  hired: number;
  declined: number;
}

interface JobWithStats extends FounderJob {
  stats: PortalStats | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function companyInitials(s: string): string {
  const words = s.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return s.slice(0, 2).toUpperCase();
}

function formatDate(): string {
  return new Date().toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

async function fetchPortalStats(apiBase: string, portalUrl: string): Promise<PortalStats | null> {
  try {
    // portal_url is "{web_base}/founder/portal?token=..." — extract the token
    const token = new URL(portalUrl).searchParams.get("token");
    if (!token) return null;
    const res = await fetch(
      `${apiBase}/founder/portal?token=${encodeURIComponent(token)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    const data = await res.json();
    return (data.stats as PortalStats) ?? null;
  } catch {
    return null;
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function FounderDashboardPage() {
  const session = await auth();

  if (!session?.user?.email) {
    redirect("/sign-in?role=founder");
  }

  const email   = session.user.email;
  const name    = session.user.name?.split(" ")[0] ?? "there";
  const apiBase = (
    process.env.MITRA_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8080"
  ).replace(/\/$/, "");

  let jobs: FounderJob[]         = [];
  let lookupError                = false;

  try {
    const res = await fetch(
      `${apiBase}/founder/all-portals-by-email?email=${encodeURIComponent(email)}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      jobs = (await res.json()).jobs ?? [];
    } else {
      // Fallback for older backends
      const fb = await fetch(
        `${apiBase}/founder/portal-link-by-email?email=${encodeURIComponent(email)}`,
        { cache: "no-store" },
      );
      if (fb.ok) {
        const d = await fb.json();
        if (d.portal_url) {
          jobs = [{
            job_id: d.job_id ?? 0,
            title: "Your role",
            company: "",
            stage: null,
            portal_url: d.portal_url,
            total_intros: 0,
            to_review: 0,
          }];
        }
      }
    }
  } catch {
    lookupError = true;
  }

  // Fetch per-job pipeline stats in parallel using the portal token
  let jobsWithStats: JobWithStats[] = jobs.map(j => ({ ...j, stats: null }));
  if (jobs.length > 0 && !lookupError) {
    const statsArr = await Promise.all(
      jobs.map(j => fetchPortalStats(apiBase, j.portal_url)),
    );
    jobsWithStats = jobs.map((j, i) => ({ ...j, stats: statsArr[i] }));
  }

  // Aggregate header stats
  const totalIntros    = jobs.reduce((s, j) => s + j.total_intros, 0);
  const totalReview    = jobs.reduce((s, j) => s + j.to_review, 0);
  const totalInterview = jobsWithStats.reduce((s, j) => s + (j.stats?.interview ?? 0), 0);
  const totalHired     = jobsWithStats.reduce((s, j) => s + (j.stats?.hired ?? 0), 0);

  return (
    <main className={styles.page}>

      {/* ── TOPBAR ──────────────────────────────────────────────────────────── */}
      <header className={styles.topbar}>
        <Link href="/" className={styles.logo}>
          <div className={styles.logoBox}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
              <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className={styles.logoName}>Mitra<span className={styles.logoDot}>.</span></span>
        </Link>
        <div className={styles.topbarRight}>
          <UserMenu
            name={session.user.name}
            email={session.user.email}
            image={session.user.image}
          />
        </div>
      </header>

      {/* ── CONTENT ─────────────────────────────────────────────────────────── */}
      <div className={styles.content}>

        {/* Greeting */}
        <div className={styles.greeting}>
          <div>
            <h1 className={styles.greetTitle}>Welcome back, {name}</h1>
            <p className={styles.greetSub}>{formatDate()}</p>
          </div>
          <Link href="/onboarding" className={styles.primaryBtn}>
            + Post a new role
          </Link>
        </div>

        {/* Stats row — 4 funnel metrics */}
        {!lookupError && (
          <div className={styles.statsRow}>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{jobs.length}</div>
              <div className={styles.statLabel}>Active roles</div>
            </div>
            <div className={`${styles.statCard} ${totalReview > 0 ? styles.statAmber : ''}`}>
              <div className={styles.statValue}>{totalIntros}</div>
              <div className={styles.statLabel}>Intros sent</div>
              {totalReview > 0 && (
                <div className={styles.statSub}>{totalReview} awaiting review</div>
              )}
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{totalInterview}</div>
              <div className={styles.statLabel}>Interviewing</div>
            </div>
            <div className={`${styles.statCard} ${totalHired > 0 ? styles.statGreen : ''}`}>
              <div className={styles.statValue}>{totalHired}</div>
              <div className={styles.statLabel}>Hired</div>
            </div>
          </div>
        )}

        {/* Error notice */}
        {lookupError && (
          <div className={styles.notice}>
            Couldn&apos;t reach the server.{" "}
            <Link href="/founder/dashboard" className={styles.noticeLink}>Try again</Link>
          </div>
        )}

        {/* Roles */}
        {!lookupError && (
          <section className={styles.section}>
            <div className={styles.sectionHead}>
              <span className={styles.sectionTitle}>Open roles</span>
              {jobs.length > 0 && (
                <span className={styles.sectionCount}>{jobs.length}</span>
              )}
            </div>

            {jobs.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <rect x="3" y="7" width="18" height="13" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M8 7V5a4 4 0 0 1 8 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </div>
                <p className={styles.emptyTitle}>No roles posted yet</p>
                <p className={styles.emptySub}>
                  Post your first role and Mitra will start sending matched candidates within 48 hours.
                </p>
                <Link href="/onboarding" className={styles.primaryBtn}>
                  Post your first role →
                </Link>
              </div>
            ) : (
              <div className={styles.roleList}>
                {jobsWithStats.map(job => {
                  const s = job.stats;
                  // "Sent" = intros not yet acted on
                  const sentCount = s
                    ? Math.max(0, s.total - s.interested - s.interview - s.offer - s.hired - s.declined)
                    : job.to_review;

                  return (
                    <a key={job.job_id} href={job.portal_url} className={styles.roleCard}>

                      {/* Avatar */}
                      <div className={styles.roleAv}>
                        {companyInitials(job.company || job.title)}
                      </div>

                      {/* Info */}
                      <div className={styles.roleInfo}>
                        <div className={styles.roleTitle}>{job.title}</div>
                        {job.company && (
                          <div className={styles.roleCompany}>{job.company}</div>
                        )}

                        {/* Pipeline mini-row */}
                        <div className={styles.pipeline}>
                          {job.total_intros > 0 ? (
                            <>
                              <span className={styles.pipeItem} data-stage="sent">
                                <span className={styles.pipeDot} />
                                {job.total_intros} introduced
                              </span>
                              {sentCount > 0 && (
                                <span className={styles.pipeItem} data-stage="review">
                                  <span className={styles.pipeDot} />
                                  {sentCount} to review
                                </span>
                              )}
                              {s && s.interested > 0 && (
                                <span className={styles.pipeItem} data-stage="interested">
                                  <span className={styles.pipeDot} />
                                  {s.interested} interested
                                </span>
                              )}
                              {s && s.interview > 0 && (
                                <span className={styles.pipeItem} data-stage="interview">
                                  <span className={styles.pipeDot} />
                                  {s.interview} interviewing
                                </span>
                              )}
                              {s && s.offer > 0 && (
                                <span className={styles.pipeItem} data-stage="offer">
                                  <span className={styles.pipeDot} />
                                  {s.offer} offer
                                </span>
                              )}
                              {s && s.hired > 0 && (
                                <span className={styles.pipeItem} data-stage="hired">
                                  <span className={styles.pipeDot} />
                                  {s.hired} hired
                                </span>
                              )}
                            </>
                          ) : (
                            <span className={styles.pipeEmpty}>No intros yet</span>
                          )}
                        </div>
                      </div>

                      {/* Right: stage + arrow */}
                      <div className={styles.roleRight}>
                        {job.stage && (
                          <span className={styles.stageBadge}>{job.stage}</span>
                        )}
                        {job.to_review > 0 && (
                          <span className={styles.reviewBadge}>{job.to_review} to review</span>
                        )}
                      </div>

                      <svg className={styles.arrow} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </a>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* Add a role */}
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTitle}>Add a role</span>
          </div>
          <div className={styles.addRow}>
            <Link href="/onboarding" className={styles.addCard}>
              <div className={styles.addCardIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 2a10 10 0 1 1 0 20A10 10 0 0 1 12 2Z" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
              </div>
              <div className={styles.addCardBody}>
                <div className={styles.addCardTitle}>Start with AI brief</div>
                <div className={styles.addCardSub}>
                  2-minute guided chat — Mitra researches your company automatically
                </div>
              </div>
              <svg className={styles.addCardArrow} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>

            <Link href="/onboarding?upload=1" className={styles.addCard}>
              <div className={styles.addCardIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  <polyline points="14 2 14 8 20 8" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  <line x1="12" y1="11" x2="12" y2="17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <polyline points="9 14 12 11 15 14" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className={styles.addCardBody}>
                <div className={styles.addCardTitle}>Upload a JD</div>
                <div className={styles.addCardSub}>
                  Drop a PDF or Word file — Mitra extracts the brief for you
                </div>
              </div>
              <svg className={styles.addCardArrow} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>
          </div>
        </section>

      </div>
    </main>
  );
}
