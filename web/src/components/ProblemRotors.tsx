"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  type ProblemScenario,
  PROBLEM_CANDIDATE_SCENARIOS,
  PROBLEM_FOUNDER_SCENARIOS,
} from "@/lib/landingDynamic";

const ROTATE_MS = 8000;

function usePrefersReducedMotion(): boolean {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduce(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return reduce;
}

function ScenarioRotor({
  label,
  labelClass,
  title,
  scenarios,
  reduceMotion,
}: {
  label: string;
  labelClass: "for-c" | "for-f";
  title: ReactNode;
  scenarios: ProblemScenario[];
  reduceMotion: boolean;
}) {
  const baseId = useId().replace(/:/g, "");
  const [idx, setIdx] = useState(0);
  const timerRef = useRef<number | null>(null);

  const tick = useCallback(() => {
    setIdx((i) => (i + 1) % scenarios.length);
  }, [scenarios.length]);

  useEffect(() => {
    if (reduceMotion) return;
    timerRef.current = window.setInterval(tick, ROTATE_MS);
    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
      }
    };
  }, [reduceMotion, tick]);

  const s = scenarios[idx]!;

  return (
    <div className="prob-card prob-card--live">
      <div className="prob-live-top">
        <div className={`prob-for ${labelClass}`}>{label}</div>
        <p className="prob-card-title prob-card-title--compact">{title}</p>
      </div>

      <div
        id={`${baseId}-panel`}
        className="prob-rotor"
        role="region"
        aria-roledescription="Rotating examples"
        aria-label={`${label}: real situations we hear often`}
        aria-live={reduceMotion ? "off" : "polite"}
      >
        <div key={s.id} className="prob-rotor-pane">
          <p className="prob-live-hook">&ldquo;{s.hook}&rdquo;</p>
          <p className="prob-live-detail">{s.detail}</p>
          <span className="prob-live-tag">{s.tag}</span>
        </div>
      </div>

      {!reduceMotion && (
        <div
          className="prob-rotor-dots"
          role="tablist"
          aria-label="Choose example"
        >
          {scenarios.map((sc, i) => (
            <button
              key={sc.id}
              type="button"
              role="tab"
              aria-selected={i === idx}
              aria-controls={`${baseId}-panel`}
              className={`prob-dot${i === idx ? " on" : ""}`}
              onClick={() => setIdx(i)}
            />
          ))}
        </div>
      )}

      {reduceMotion && (
        <p className="prob-rotor-static-hint">
          Showing one example. Enable motion in your system settings to rotate
          through more.
        </p>
      )}
    </div>
  );
}

import { useAudience } from "./AudienceContext";

export function ProblemRotors() {
  const reduceMotion = usePrefersReducedMotion();
  const { audience } = useAudience();

  if (audience === "candidate") {
    return (
      <div className="prob-grid-single">
        <ScenarioRotor
          label="What we hear every week"
          labelClass="for-c"
          title={<>You&apos;re qualified.<br />The system ignores you.</>}
          scenarios={PROBLEM_CANDIDATE_SCENARIOS}
          reduceMotion={reduceMotion}
        />
      </div>
    );
  }

  return (
    <div className="prob-grid-single">
      <ScenarioRotor
        label="What founders tell us"
        labelClass="for-f"
        title={<>You&apos;re drowning in noise.<br />You need signal.</>}
        scenarios={PROBLEM_FOUNDER_SCENARIOS}
        reduceMotion={reduceMotion}
      />
    </div>
  );
}
