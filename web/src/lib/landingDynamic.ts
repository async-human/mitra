/**
 * Rotating landing copy — concrete vignettes, not generic claims.
 * Edit here as you refine positioning; components only handle display + motion.
 */

export type ProblemScenario = {
  id: string;
  /** One sharp line — the emotional hook */
  hook: string;
  /** Supporting line — grounds it in behaviour */
  detail: string;
  /** Tiny context label */
  tag: string;
};

export const PROBLEM_CANDIDATE_SCENARIOS: ProblemScenario[] = [
  {
    id: "c-silence",
    hook: "Forty-seven applications in six weeks. Two automated rejections. The rest — silence.",
    detail:
      "The pipeline optimises for volume, not for getting you in front of someone who can say yes.",
    tag: "Senior IC · pan-India",
  },
  {
    id: "c-ats",
    hook: "You're staff-level, but the ATS scores you “mid” because your title never said Senior.",
    detail:
      "Keyword gates hide real trajectory — and nobody reads the cover note you spent an hour on.",
    tag: "Backend / platform",
  },
  {
    id: "c-access",
    hook: "The founder you actually want to work for doesn't live inside Naukri inmail.",
    detail:
      "Warm access beats cold apply every time — but networks are unevenly distributed.",
    tag: "Product & eng",
  },
  {
    id: "c-agency",
    hook: "The recruiter who called optimises for their fee, not for whether you'd take the offer.",
    detail:
      "Misaligned incentives show up as rushed shortlists and vague JD fit.",
    tag: "Job switchers",
  },
  {
    id: "c-screen",
    hook: "You get a “quick call” that turns out to be a thirty-minute form in disguise.",
    detail:
      "Intent never surfaces — so the next round starts from zero again.",
    tag: "Experienced hires",
  },
];

export const PROBLEM_FOUNDER_SCENARIOS: ProblemScenario[] = [
  {
    id: "f-volume",
    hook: "One hundred eighty-four applicants for a single backend role. Twelve can explain your stack.",
    detail:
      "Volume isn’t the problem — signal is. Screening swallows your team’s calendar.",
    tag: "Series A–B · BLR",
  },
  {
    id: "f-passive",
    hook: "The person you’d hire in a heartbeat never applied — they’re not on the board this week.",
    detail:
      "The best candidates are introduced, not harvested from a keyword search.",
    tag: "Founding team hire",
  },
  {
    id: "f-time",
    hook: "Engineers spent a sprint on screens that went nowhere — and the role is still open.",
    detail:
      "Every bad intro is tax on builders who should be shipping.",
    tag: "Small eng team",
  },
  {
    id: "f-agency",
    hook: "The agency’s “top five” included three people who wanted fully remote US hours.",
    detail:
      "Generic shortlists waste founder energy and burn candidate trust.",
    tag: "High bar role",
  },
  {
    id: "f-motivation",
    hook: "You need someone who cares about your problem — not someone spray-applying to every Series B.",
    detail:
      "Motivation and stage-fit don’t show up on a two-page PDF.",
    tag: "Mission-critical role",
  },
];

export type ConvoQuote = {
  id: string;
  quote: string;
  attr: string;
};

export type FounderTestimonial = ConvoQuote & {
  tags: string[];
  metric: { value: string; label: string };
};

export const FOUNDER_TESTIMONIALS: FounderTestimonial[] = [
  {
    id: "f1",
    quote:
      "We stopped reading CVs. Mitra sends three people who already want to work on our problem — with context we'd have taken twenty minutes to write.",
    attr: "Founder · Series A fintech · Bangalore",
    tags: ["Series A", "Fintech", "Pre-qualified"],
    metric: { value: "3", label: "intros per batch" },
  },
  {
    id: "f2",
    quote:
      "First intro in five days. Every candidate knew our stack and our stage — none of the 'spray apply' noise we get from job boards.",
    attr: "CTO · B2B SaaS · 12-person eng team",
    tags: ["B2B SaaS", "5-day intro", "Stack-aware"],
    metric: { value: "5d", label: "to first intro" },
  },
  {
    id: "f3",
    quote:
      "The shortlist got sharper after our second hire. Mitra learned we care about ownership evidence more than pedigree.",
    attr: "Founding engineer turned CEO · healthtech",
    tags: ["Healthtech", "Learning bar", "Ownership"],
    metric: { value: "2×", label: "sharper shortlist" },
  },
  {
    id: "f4",
    quote:
      "Eight percent fee with a written replacement guarantee — and the first two placements were free. Easiest hiring decision we made.",
    attr: "Head of Engineering · payments infra",
    tags: ["8% fee", "90-day guarantee", "2 free hires"],
    metric: { value: "8%", label: "success fee" },
  },
];

export const CONVO_QUOTES: ConvoQuote[] = [
  {
    id: "q1",
    quote:
      "Mitra asked me why I was really thinking of moving — not what my skills were. That was the moment I knew this was different.",
    attr: "Candidate placed at payments infrastructure scale-up · India",
  },
  {
    id: "q2",
    quote:
      "On every other platform I was a row in a spreadsheet. Here it felt like someone actually read what I’d built.",
    attr: "Senior engineer · fintech",
  },
  {
    id: "q3",
    quote:
      "I didn’t want another ‘culture fit’ screen. I wanted one honest conversation about what I won’t compromise on.",
    attr: "Product lead · payments",
  },
  {
    id: "q4",
    quote:
      "The intro to the founder wasn’t a forward of my CV — it was context I would have taken twenty minutes to explain.",
    attr: "Backend engineer · Series B",
  },
];
