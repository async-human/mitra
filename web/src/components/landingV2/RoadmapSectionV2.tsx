"use client";

import { useEffect, useRef, useState } from "react";
import s from "./landing-v2.module.css";

/* ── Types ────────────────────────────────────────────────── */

type PhaseStatus = "live" | "building" | "next" | "vision";

interface Phase {
  status: PhaseStatus;
  label: string;
  title: string;
  desc: string;
  features: { label: string; status: PhaseStatus }[];
}

/* ── Content ──────────────────────────────────────────────── */

const STATUS_LABELS: Record<PhaseStatus, string> = {
  live:     "Live today",
  building: "Building now",
  next:     "Coming next",
  vision:   "The vision",
};

const PHASES: Phase[] = [
  {
    status: "live",
    label: "Phase 1 — Now",
    title: "Foundation: conversation, matching, warm intros",
    desc:
      "The core loop is working. Candidates have a real WhatsApp conversation with Mitra, get semantically matched to funded startup roles, and receive warm introductions to founders with full context. The agent remembers across sessions. Engineers placed at Setu, CRED, and Razorpay.",
    features: [
      { label: "WhatsApp intake",        status: "live" },
      { label: "Semantic matching",      status: "live" },
      { label: "Warm intros",            status: "live" },
      { label: "Session memory",         status: "live" },
      { label: "Salary benchmarking",    status: "live" },
      { label: "Zero ghosting guarantee",status: "live" },
    ],
  },
  {
    status: "building",
    label: "Phase 2 — Building now",
    title: "Persistent identity: the agent that knows you",
    desc:
      "Moving from session memory to persistent identity models. The agent builds a behavioural profile that deepens with every interaction — communication style, ownership mindset, risk appetite, career trajectory. Every conversation makes the next one better. Supervised autonomy: Mitra prepares actions, you approve.",
    features: [
      { label: "Behavioural profiling",    status: "building" },
      { label: "Communication adaptation",  status: "building" },
      { label: "Trajectory inference",      status: "building" },
      { label: "Supervised autonomy",       status: "building" },
      { label: "Founder intelligence",      status: "building" },
      { label: "Proactive job alerts",      status: "building" },
    ],
  },
  {
    status: "next",
    label: "Phase 3 — Next",
    title: "Earned autonomy: the agent acts while you sleep",
    desc:
      "Once the agent has demonstrated reliable judgment, it earns the right to act without manual approval on high-confidence actions. Proactive outreach when conditions are right. Automatic follow-ups. Negotiation coaching triggered by offer signals. The agent has its own agenda — advancing your interests 24×7.",
    features: [
      { label: "Autonomous outreach",       status: "next" },
      { label: "Offer negotiation agent",   status: "next" },
      { label: "Autonomous follow-up",      status: "next" },
      { label: "30/90-day check-ins",       status: "next" },
      { label: "Market intelligence",       status: "next" },
    ],
  },
  {
    status: "vision",
    label: "Phase 4 — The vision",
    title: "Compounding intelligence: the network that learns",
    desc:
      "The full vision is not a smarter job board. It's a network where every interaction — every conversation, every intro, every placement outcome — compounds into hiring intelligence that no platform can replicate. Compatibility patterns. Founder personality models. Career trajectory prediction. A system that gets smarter every day without anyone training it.",
    features: [
      { label: "Compatibility prediction",     status: "vision" },
      { label: "Founder personality models",   status: "vision" },
      { label: "Cross-company continuity",     status: "vision" },
      { label: "Compounding placement data",   status: "vision" },
      { label: "Agentic talent network",       status: "vision" },
    ],
  },
];

/* ── Scroll-reveal ────────────────────────────────────────── */

function RevealRow({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`${s.roadmapRow} ${visible ? s.roadmapRowIn : ""}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

/* ── Component ────────────────────────────────────────────── */

export function RoadmapSectionV2() {
  return (
    <section className={s.sectionWrap} id="roadmap">
      <div className={s.sectionInner}>

        <p className={s.sectionLabel}>Where we&apos;re going</p>
        <h2 className={s.sectionTitle}>
          Built in the open.<br />No hidden roadmap.
        </h2>

        <p className={s.roadmapIntro}>
          Most products hide what they&apos;re building toward. We think transparency
          about the direction is itself a form of trust. Here is exactly where Mitra
          is today, what we&apos;re building next, and what the full vision looks like.
        </p>

        <div className={s.roadmapPhilosophy}>
          <span className={s.roadmapPhilosophyQuote}>&ldquo;</span>
          <p>
            <strong>The core belief:</strong> hiring is not a search problem — it&apos;s a
            relationship problem. The system that solves it is not a better database.
            It&apos;s persistent agents that represent humans continuously, learn from
            every interaction, and act on their behalf without being asked.
          </p>
        </div>

        <div className={s.roadmapTimeline}>
          {/* Vertical line */}
          <div className={s.roadmapLine} aria-hidden="true" />

          {PHASES.map((phase, i) => (
            <RevealRow key={phase.label} delay={i * 60}>
              {/* Dot on the line */}
              <div className={`${s.roadmapDot} ${s[`roadmapDot--${phase.status}`]}`} aria-hidden="true">
                {phase.status === "live" && <span className={s.roadmapDotCore} />}
              </div>

              <div className={s.roadmapCard}>
                {/* Header row */}
                <div className={s.roadmapCardHeader}>
                  <span className={s.roadmapPhaseLabel}>{phase.label}</span>
                  <span className={`${s.roadmapStatusBadge} ${s[`roadmapBadge--${phase.status}`]}`}>
                    {STATUS_LABELS[phase.status]}
                  </span>
                </div>

                <h3 className={s.roadmapCardTitle}>{phase.title}</h3>
                <p className={s.roadmapCardDesc}>{phase.desc}</p>

                <div className={s.roadmapFeatures}>
                  {phase.features.map(f => (
                    <span
                      key={f.label}
                      className={`${s.roadmapFeatureTag} ${s[`roadmapTag--${f.status}`]}`}
                    >
                      {f.label}
                    </span>
                  ))}
                </div>
              </div>
            </RevealRow>
          ))}
        </div>

      </div>
    </section>
  );
}
