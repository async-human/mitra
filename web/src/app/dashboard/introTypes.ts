/** Candidate intro row from GET /candidate/intros (shared by dashboard panels). */

export interface InterviewDetails {
  scheduled_at?: string;
  format?: string;
  link?: string;
  notes?: string;
}

export interface OfferDetails {
  salary_lpa?: number;
  equity_percent?: number;
  start_date?: string;
  notes?: string;
}

export interface CandidateIntro {
  intro_id: number;
  job_id: number;
  job_title: string;
  company: string;
  status: string;
  sent_at: string | null;
  interview_details?: InterviewDetails | null;
  offer_details?: OfferDetails | null;
}
