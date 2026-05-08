"use client";

/**
 * Animated WhatsApp-style demo with multiple scripted scenarios.
 * Conversation copy and the recommended-role card rotate each loop cycle.
 */

import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

type ChatMsg = {
  from: "in" | "out";
  text: string;
  time: string;
};

/** Data for the recommended-job card at the end of each scenario. */
export type MatchCardData = {
  role: string;
  company: string;
  scoreLabel: string;
  tags: [string, string, string];
};

/** Each scenario: exactly 5 alternating chat lines + one rich match card. */
const MESSAGES_PER_SCENARIO = 5;

export type DemoScenario = {
  id: string;
  messages: ChatMsg[];
  /** Shown on the rich match bubble footer */
  matchTime: string;
  card: MatchCardData;
};

const SCENARIOS: DemoScenario[] = [
  {
    id: "staff-eng-infra",
    matchTime: "10:16",
    messages: [
      {
        from: "in",
        text: "Hey 👋 I'm Mitra. Before roles — what's the one thing you'd change about work tomorrow if you could?",
        time: "10:14",
      },
      {
        from: "out",
        text: "Stop babysitting legacy. I want to own systems end-to-end and actually ship.",
        time: "10:14",
      },
      {
        from: "in",
        text: "Got it. Proudest thing you've shipped lately — even if nobody asked?",
        time: "10:15",
      },
      {
        from: "out",
        text: "Fraud-detection rewrite. Cut false positives ~40%. Turned three weeks on-call into sane alerts.",
        time: "10:15",
      },
      {
        from: "in",
        text: "That's the arc Setu cares about — Series B infra, merchant platforms. Want a warm intro to their eng lead?",
        time: "10:16",
      },
    ],
    card: {
      role: "Staff Engineer",
      company: "Setu",
      scoreLabel: "96% fit",
      tags: ["Series B · Fintech", "₹42–52L", "Remote"],
    },
  },
  {
    id: "pm-growth",
    matchTime: "11:42",
    messages: [
      {
        from: "in",
        text: "Hi, I'm Mitra. Which roadmap bet are you itching to prove — monetisation, retention, or something else?",
        time: "11:40",
      },
      {
        from: "out",
        text: "Monetisation. We circle the drain on experiments but never GA the ones that compound.",
        time: "11:40",
      },
      {
        from: "in",
        text: "When did you last kill something your gut said was noise?",
        time: "11:41",
      },
      {
        from: "out",
        text: "Sunset a BNPL pilot — churn data was ugly. Wrapped it in ten days instead of debating for a quarter.",
        time: "11:41",
      },
      {
        from: "in",
        text: "Merchant growth at Razorpay is looking for exactly that ruthlessness. Shall I tee up their PM lead?",
        time: "11:42",
      },
    ],
    card: {
      role: "Senior PM · Growth",
      company: "Razorpay",
      scoreLabel: "92% fit",
      tags: ["Series D · Payments", "₹45–62L", "Hybrid · BLR"],
    },
  },
  {
    id: "backend-platform",
    matchTime: "16:03",
    messages: [
      {
        from: "in",
        text: "Hey — Mitra here. One messy system you'd refactor first Monday morning?",
        time: "16:01",
      },
      {
        from: "out",
        text: "Card billing adapters. Cascading timeouts; every deploy feels like bingo.",
        time: "16:01",
      },
      {
        from: "in",
        text: "Reliability win nobody asked you for?",
        time: "16:02",
      },
      {
        from: "out",
        text: "Idempotent payouts + DLQ everywhere. Sev-2s went from dozens a quarter to barely one.",
        time: "16:02",
      },
      {
        from: "in",
        text: "Hyperface is rebuilding payouts stack — they'd love that profile. Intro you Monday?",
        time: "16:03",
      },
    ],
    card: {
      role: "Backend Engineer",
      company: "Hyperface",
      scoreLabel: "89% fit",
      tags: ["Series A · Cards", "₹38–50L", "Hybrid · BLR"],
    },
  },
  {
    id: "frontend-craft",
    matchTime: "09:07",
    messages: [
      {
        from: "in",
        text: "Morning — Mitra 🤙 One UI tweak you'd sneak in if nobody could block it?",
        time: "09:05",
      },
      {
        from: "out",
        text: "App shell hydration. We'd claw back hundreds of ms and first paint would stop feeling heavy.",
        time: "09:05",
      },
      {
        from: "in",
        text: "Show me the experiment or launch you're proudest of.",
        time: "09:06",
      },
      {
        from: "out",
        text: "Rebuilt onboarding with motion + locales — completions +22% in A/B.",
        time: "09:06",
      },
      {
        from: "in",
        text: "Finbox is hiring for that blend of craft + performance. Warm intro?",
        time: "09:07",
      },
    ],
    card: {
      role: "Senior Frontend",
      company: "Finbox",
      scoreLabel: "94% fit",
      tags: ["Series B · Lending", "₹40–54L", "Remote-first"],
    },
  },
  {
    id: "ml-infra",
    matchTime: "14:52",
    messages: [
      {
        from: "in",
        text: "Hi, Mitra speaking. Models or infra — what's the bottleneck on your radar right now?",
        time: "14:49",
      },
      {
        from: "out",
        text: "Feature store drift. Offline metrics look heroic; prod degrades silently.",
        time: "14:50",
      },
      {
        from: "in",
        text: "Fix you're most proud of in the last sprint?",
        time: "14:50",
      },
      {
        from: "out",
        text: "Shadow traffic + gated rollouts caught a bad cohort before we'd shipped to 100%.",
        time: "14:51",
      },
      {
        from: "in",
        text: "CRED wants someone who guards quality like that across risk models — intro to their DS lead?",
        time: "14:52",
      },
    ],
    card: {
      role: "ML Engineer",
      company: "CRED",
      scoreLabel: "91% fit",
      tags: ["Late-stage · Wealth", "₹48–70L", "Hybrid · BLR"],
    },
  },
];

function assertScenarioShape(s: DemoScenario): void {
  if (s.messages.length !== MESSAGES_PER_SCENARIO) {
    console.warn(
      `[PhoneMockup] Scenario "${s.id}" must have exactly ${MESSAGES_PER_SCENARIO} messages.`,
    );
  }
}
SCENARIOS.forEach(assertScenarioShape);

type BubbleItem =
  | { sortKey: number; kind: "msg"; msg: ChatMsg }
  | {
      sortKey: number;
      kind: "match";
      time: string;
      card: MatchCardData;
    };

type Step =
  | { type: "typing"; actor: "in" | "out"; ms: number }
  | { type: "message"; idx: number; pauseMs: number }
  | { type: "match"; pauseMs: number }
  | { type: "wait"; ms: number }
  | { type: "typing_pause"; pauseMs: number };

const SEQUENCE: Step[] = [
  { type: "wait", ms: 400 },
  { type: "typing", actor: "in", ms: 1100 },
  { type: "message", idx: 0, pauseMs: 420 },
  { type: "wait", ms: 380 },
  { type: "typing", actor: "out", ms: 700 },
  { type: "message", idx: 1, pauseMs: 440 },
  { type: "wait", ms: 400 },
  { type: "typing", actor: "in", ms: 950 },
  { type: "message", idx: 2, pauseMs: 400 },
  { type: "wait", ms: 320 },
  { type: "typing", actor: "out", ms: 800 },
  { type: "message", idx: 3, pauseMs: 420 },
  { type: "wait", ms: 420 },
  { type: "typing", actor: "in", ms: 1000 },
  { type: "message", idx: 4, pauseMs: 450 },
  { type: "wait", ms: 450 },
  { type: "typing", actor: "in", ms: 1200 },
  { type: "match", pauseMs: 500 },
  { type: "typing_pause", pauseMs: 1800 },
  { type: "wait", ms: 2800 },
];

function MitraAvatar() {
  return (
    <div className="pm-avatar" aria-hidden="true">
      M
    </div>
  );
}

function StatusBar() {
  return (
    <div className="pm-statusbar">
      <span className="pm-time">9:41</span>
      <div className="pm-status-right">
        <span className="pm-signal" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </span>
        <span className="pm-wifi" aria-hidden="true" />
        <span className="pm-battery" aria-hidden="true">
          <span className="pm-battery-fill" />
        </span>
      </div>
    </div>
  );
}

function HeaderBar() {
  return (
    <div className="pm-header">
      <span className="pm-back" aria-hidden="true">
        ‹
      </span>
      <MitraAvatar />
      <div className="pm-header-meta">
        <div className="pm-header-name">
          Mitra
          <span className="pm-verified" aria-label="Verified business account">
            ✓
          </span>
        </div>
        <div className="pm-header-status">online</div>
      </div>
      <span className="pm-header-icon" aria-hidden="true">
        ⌕
      </span>
    </div>
  );
}

function Bubble({
  msg,
  showTicks,
}: {
  msg: ChatMsg;
  showTicks?: boolean;
}) {
  return (
    <div className={`pm-bubble pm-bubble-${msg.from} pm-enter-fade`}>
      <div className="pm-bubble-text">{msg.text}</div>
      <div className="pm-bubble-meta">
        <span className="pm-bubble-time">{msg.time}</span>
        {msg.from === "out" && showTicks && (
          <span className="pm-ticks" aria-label="Read">
            ✓✓
          </span>
        )}
      </div>
    </div>
  );
}

function MatchCardBubble({
  time,
  card,
}: {
  time: string;
  card: MatchCardData;
}) {
  return (
    <div className="pm-bubble pm-bubble-in pm-bubble-rich pm-enter-fade">
      <MatchCard card={card} />
      <div className="pm-bubble-meta">
        <span className="pm-bubble-time">{time}</span>
      </div>
    </div>
  );
}

function MatchCard({ card }: { card: MatchCardData }) {
  return (
    <div className="pm-match">
      <div className="pm-match-row">
        <span className="pm-match-role">
          {card.role} · {card.company}
        </span>
        <span className="pm-match-score">{card.scoreLabel}</span>
      </div>
      <div className="pm-match-tags">
        {card.tags.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
      <div className="pm-match-cta">View intro →</div>
    </div>
  );
}

function TypingDots({ actor }: { actor: "in" | "out" }) {
  const label = actor === "in" ? "Mitra is typing" : "Typing a reply";
  return (
    <div
      className={`pm-typing pm-typing-${actor}`}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <span aria-hidden="true" />
      <span aria-hidden="true" />
      <span aria-hidden="true" />
    </div>
  );
}

function InputBar() {
  return (
    <div className="pm-input">
      <span className="pm-input-emoji" aria-hidden="true">
        ☺
      </span>
      <div className="pm-input-field">Reply to Mitra…</div>
      <span className="pm-input-attach" aria-hidden="true">
        ＋
      </span>
      <span className="pm-input-mic" aria-hidden="true">
        🎤
      </span>
    </div>
  );
}

function buildStaticItems(
  scenario: DemoScenario,
  startKey: number,
): BubbleItem[] {
  const out: BubbleItem[] = [];
  let k = startKey;
  scenario.messages.forEach((msg) => {
    out.push({ sortKey: k++, kind: "msg", msg });
  });
  out.push({
    sortKey: k++,
    kind: "match",
    time: scenario.matchTime,
    card: scenario.card,
  });
  return out;
}

export type PhoneMockupProps = {
  /** Tighter chrome + flat device (sharp text, less hero whitespace). */
  layout?: "hero";
};

export function PhoneMockup({ layout }: PhoneMockupProps) {
  const demoId = useId().replace(/:/g, "");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const innerRef = useRef<HTMLDivElement | null>(null);
  const runIdRef = useRef(0);
  const timeoutsRef = useRef<number[]>([]);
  /** Current scenario index for the timed animation loop (ref for stable closure). */
  const scenarioIdxRef = useRef(0);

  const [reduceMotion, setReduceMotion] = useState(false);
  const [items, setItems] = useState<BubbleItem[]>([]);
  const [typingActor, setTypingActor] = useState<null | "in" | "out">(null);

  /** For reduced-motion: rotate static snapshot so visitors still see variety. */
  const [staticVariant, setStaticVariant] = useState(0);

  const clearTimers = useCallback(() => {
    timeoutsRef.current.forEach((tid) => window.clearTimeout(tid));
    timeoutsRef.current = [];
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduceMotion(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    if (!reduceMotion) return;
    const tid = window.setInterval(() => {
      setStaticVariant((v) => (v + 1) % SCENARIOS.length);
    }, 52000);
    return () => clearInterval(tid);
  }, [reduceMotion]);

  useLayoutEffect(() => {
    scrollToBottom();
  }, [items, typingActor, scrollToBottom]);

  useEffect(() => {
    const outer = scrollRef.current;
    const inner = innerRef.current;
    if (!outer || !inner) return;
    const ro = new ResizeObserver(() => {
      outer.scrollTop = outer.scrollHeight;
    });
    ro.observe(inner);
    return () => ro.disconnect();
  }, []);

  /** Reduced motion: single static transcript; rotate snapshots on an interval */
  useEffect(() => {
    if (!reduceMotion) return;
    clearTimers();
    queueMicrotask(() => {
      setTypingActor(null);
      const scenario = SCENARIOS[staticVariant];
      setItems(buildStaticItems(scenario, 0));
    });
  }, [reduceMotion, staticVariant, clearTimers]);

  /** Animated: scripted timeline loops; advances to the next scenario after each cycle */
  useEffect(() => {
    if (reduceMotion) return;

    clearTimers();
    scenarioIdxRef.current = 0;

    const runDemo = () => {
      const run = ++runIdRef.current;
      let sortKey = 0;
      let stepIndex = 0;

      const pickScenario = (): DemoScenario => {
        const s = SCENARIOS[scenarioIdxRef.current % SCENARIOS.length]!;
        scenarioIdxRef.current += 1;
        return s;
      };

      let scenario = pickScenario();

      setItems([]);
      setTypingActor(null);

      const schedule = (ms: number, fn: () => void) => {
        const id = window.setTimeout(() => {
          if (runIdRef.current !== run) return;
          fn();
        }, ms);
        timeoutsRef.current.push(id);
      };

      const runStep = (): void => {
        if (runIdRef.current !== run) return;

        if (stepIndex >= SEQUENCE.length) {
          setTypingActor(null);
          schedule(120, () => {
            scenario = pickScenario();
            setItems([]);
            sortKey = 0;
            stepIndex = 0;
            schedule(240, runStep);
          });
          return;
        }

        const step = SEQUENCE[stepIndex++]!;
        switch (step.type) {
          case "wait": {
            schedule(step.ms, runStep);
            break;
          }
          case "typing": {
            setTypingActor(step.actor);
            schedule(step.ms, () => {
              setTypingActor(null);
              schedule(40, runStep);
            });
            break;
          }
          case "message": {
            const msg = scenario.messages[step.idx];
            if (!msg) break;
            setItems((prev) => [
              ...prev,
              { sortKey: sortKey++, kind: "msg", msg },
            ]);
            schedule(step.pauseMs, runStep);
            break;
          }
          case "match": {
            setItems((prev) => [
              ...prev,
              {
                sortKey: sortKey++,
                kind: "match",
                time: scenario.matchTime,
                card: scenario.card,
              },
            ]);
            schedule(step.pauseMs, runStep);
            break;
          }
          case "typing_pause": {
            setTypingActor("in");
            schedule(step.pauseMs, () => {
              setTypingActor(null);
              schedule(120, runStep);
            });
            break;
          }
          default:
            break;
        }
      };

      schedule(280, runStep);
    };

    runDemo();

    return () => {
      runIdRef.current += 1;
      clearTimers();
    };
  }, [reduceMotion, clearTimers]);

  const stageClass =
    layout === "hero" ? "pm-stage pm-stage--hero" : "pm-stage";

  return (
    <div className={stageClass}>
      <div
        className="pm-frame"
        role="region"
        aria-roledescription="Simulated WhatsApp preview"
        aria-label="Sample WhatsApp conversation with Mitra, animated with rotating examples"
      >
        <div className="pm-screen">
          <div className="pm-island" aria-hidden="true" />
          <StatusBar />
          <HeaderBar />

          <div className="pm-body" ref={scrollRef}>
            <div className="pm-body-inner" ref={innerRef}>
              <div className="pm-day">TODAY</div>
              {items.map((it) =>
                it.kind === "msg" ? (
                  <Bubble
                    key={`${demoId}-${it.sortKey}-${it.msg.time}-${it.msg.text.slice(0, 12)}`}
                    msg={it.msg}
                    showTicks
                  />
                ) : (
                  <MatchCardBubble
                    key={`${demoId}-c-${it.sortKey}-${it.card.company}`}
                    time={it.time}
                    card={it.card}
                  />
                ),
              )}
              {typingActor && <TypingDots actor={typingActor} />}
            </div>
          </div>

          <InputBar />
        </div>

        <span className="pm-btn pm-btn-silent" aria-hidden="true" />
        <span className="pm-btn pm-btn-vol-up" aria-hidden="true" />
        <span className="pm-btn pm-btn-vol-down" aria-hidden="true" />
        <span className="pm-btn pm-btn-power" aria-hidden="true" />
      </div>
    </div>
  );
}
