import type { CandidateIntro } from "./introTypes";

/** Shape of job cards saved from chat / matches (localStorage). */
export interface StoredMatchCard {
  id: string;
  title: string;
  description: string;
  why?: string;
}

/**
 * Rebuilds a minimal shortlist from intro rows (API-backed).
 * Used when localStorage is empty — e.g. user switched site origin (custom domain)
 * so prior `mitra-matches-*` keys are not visible.
 */
export function deriveMatchCardsFromIntros(intros: CandidateIntro[]): StoredMatchCard[] {
  const seen = new Set<number>();
  const out: StoredMatchCard[] = [];
  for (const i of intros) {
    if (seen.has(i.job_id)) continue;
    seen.add(i.job_id);
    out.push({
      id: `job_${i.job_id}`,
      title: i.job_title,
      description: i.company,
    });
  }
  return out;
}
