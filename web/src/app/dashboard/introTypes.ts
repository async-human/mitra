/** Candidate intro row from GET /candidate/intros (shared by dashboard panels). */

export interface InterviewDetails {
  scheduled_at?: string;      // pre-formatted human string from Cal.com OR ISO if manually set
  scheduled_at_iso?: string;  // raw ISO UTC string — always use this for Date parsing
  format?: string;
  link?: string;
  notes?: string;
  booking_uid?: string;
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
  updated_at?: string | null;
  interview_details?: InterviewDetails | null;
  offer_details?: OfferDetails | null;
  booking_link?: string | null;
}
