"use client";

import { Reveal } from "./Reveal";
import { ProblemRotors } from "./ProblemRotors";
import { useAudience } from "./AudienceContext";

const COPY = {
  candidate: {
    h2: <>The job search in India<br />is <em>broken for builders.</em></>,
    sub: "You're applying to 60 roles. You're qualified. You hear nothing. The ATS filters you out on keywords. Recruiters call and disappear. The roles that would be perfect for you are never posted anywhere. Below are situations we hear every week.",
  },
  founder: {
    h2: <>Hiring at a startup in India<br />is <em>broken for founders.</em></>,
    sub: "You post a role and get 200 CVs — 180 of which have zero startup intent. Agencies charge 15% and send you the same list. Your best hires came through someone you knew. But you can't rely on your network forever. Below are situations we hear from founders every week.",
  },
};

export function Problem() {
  const { audience } = useAudience();
  const copy = COPY[audience];

  return (
    <section className="problem">
      <div className="prob-inner">
        <div className="prob-text">
          <div className="prob-eyebrow">The problem we solve</div>
          <Reveal as="h2" className="prob-h2">{copy.h2}</Reveal>
          <Reveal as="p" className="prob-sub" delay={1}>{copy.sub}</Reveal>
        </div>
        <Reveal delay={2}>
          <ProblemRotors />
        </Reveal>
      </div>
    </section>
  );
}
