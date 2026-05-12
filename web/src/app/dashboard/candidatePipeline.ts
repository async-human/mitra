/** Shared intro ordering and labels for dashboard panels. */

export interface IntroLike {
  job_id: number;
  status: string;
  sent_at: string | null;
}

const STATUS_RANK: Record<string, number> = {
  offer: 0,
  interview: 1,
  acknowledged: 2,
  sent: 3,
  ghosted: 4,
  hired: 5,
  declined: 6,
};

export function rankIntroStatus(status: string): number {
  return STATUS_RANK[status] ?? 50;
}

/** Need attention first; outcomes (hired / declined) last; newer intros before older within the same band. */
export function sortIntrosByPriority<T extends IntroLike>(intros: T[]): T[] {
  return [...intros].sort((a, b) => {
    const dr = rankIntroStatus(a.status) - rankIntroStatus(b.status);
    if (dr !== 0) return dr;
    const ta = a.sent_at ? new Date(a.sent_at).getTime() : 0;
    const tb = b.sent_at ? new Date(b.sent_at).getTime() : 0;
    return tb - ta;
  });
}

export const INTRO_STATUS_META: Record<
  string,
  { label: string; color: string; bg: string; dot: string; pulse?: boolean }
> = {
  sent: { label: "Intro sent", color: "#059669", bg: "#ECFDF5", dot: "#34D399" },
  acknowledged: { label: "Interested ✦", color: "#7C3AED", bg: "#F5F3FF", dot: "#A78BFA", pulse: true },
  interview: { label: "Interview booked", color: "#D97706", bg: "#FFFBEB", dot: "#FCD34D", pulse: true },
  offer: { label: "Offer received", color: "#059669", bg: "#ECFDF5", dot: "#6EE7B7", pulse: true },
  hired: { label: "Hired 🎉", color: "#059669", bg: "#ECFDF5", dot: "#6EE7B7" },
  declined: { label: "Not a fit", color: "#6B7280", bg: "#F3F4F6", dot: "#D1D5DB" },
  ghosted: { label: "Awaiting reply", color: "#9CA3AF", bg: "#F9FAFB", dot: "#E5E7EB" },
};

export function introStatusMeta(status: string) {
  return (
    INTRO_STATUS_META[status] ?? {
      label: status,
      color: "#6B7280",
      bg: "#F3F4F6",
      dot: "#D1D5DB",
    }
  );
}

export function isTerminalIntroStatus(status: string): boolean {
  return status === "hired" || status === "declined";
}
