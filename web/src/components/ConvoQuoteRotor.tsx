"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { CONVO_QUOTES } from "@/lib/landingDynamic";

const ROTATE_MS = 10000;

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

export function ConvoQuoteRotor() {
  const baseId = useId().replace(/:/g, "");
  const reduceMotion = usePrefersReducedMotion();
  const [idx, setIdx] = useState(0);
  const timerRef = useRef<number | null>(null);

  const tick = useCallback(() => {
    setIdx((i) => (i + 1) % CONVO_QUOTES.length);
  }, []);

  useEffect(() => {
    if (reduceMotion) return;
    timerRef.current = window.setInterval(tick, ROTATE_MS);
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
    };
  }, [reduceMotion, tick]);

  const q = CONVO_QUOTES[idx]!;

  return (
    <div className="convo-quote-shell">
      <div
        id={`${baseId}-quote`}
        className="convo-quote-inner"
        role="region"
        aria-roledescription="Rotating quotes"
        aria-label="What candidates say about talking to Mitra"
        aria-live={reduceMotion ? "off" : "polite"}
      >
        <div key={q.id} className="convo-quote-pane">
          <p className="convo-quote-text">&ldquo;{q.quote}&rdquo;</p>
          <p className="convo-quote-attr">{q.attr}</p>
        </div>
      </div>

      {!reduceMotion && (
        <div className="convo-quote-dots" role="tablist" aria-label="Quote">
          {CONVO_QUOTES.map((item, i) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={i === idx}
              aria-controls={`${baseId}-quote`}
              className={`convo-qdot${i === idx ? " on" : ""}`}
              onClick={() => setIdx(i)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
