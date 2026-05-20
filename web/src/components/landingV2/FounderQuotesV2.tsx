"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { FOUNDER_TESTIMONIALS } from "@/lib/landingDynamic";
import s from "./landing-v2.module.css";

const ROTATE_MS = 9000;

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

export function FounderQuotesV2() {
  const baseId = useId().replace(/:/g, "");
  const reduceMotion = usePrefersReducedMotion();
  const [idx, setIdx] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);
  const [entered, setEntered] = useState(false);

  const tick = useCallback(() => {
    setIdx((i) => (i + 1) % FOUNDER_TESTIMONIALS.length);
  }, []);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setEntered(true);
          obs.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (reduceMotion || !entered) return;
    const id = window.setInterval(tick, ROTATE_MS);
    return () => window.clearInterval(id);
  }, [reduceMotion, entered, tick]);

  const q = FOUNDER_TESTIMONIALS[idx]!;

  return (
    <section
      ref={sectionRef}
      className={`${s.fqSection} ${entered ? s.fqSectionInView : ""}`}
      aria-labelledby={`${baseId}-title`}
    >
      <div className={s.sectionInner}>
        <p className={s.sectionLabel}>From founders</p>
        <h2 id={`${baseId}-title`} className={s.sectionTitle}>
          Signal, not spray-and-pray.
        </h2>

        <div
          id={`${baseId}-panel`}
          className={s.fqCard}
          role="region"
          aria-roledescription="Rotating testimonials"
          aria-live={reduceMotion ? "off" : "polite"}
        >
          <span className={s.fqMark} aria-hidden="true">
            &ldquo;
          </span>
          <div key={q.id} className={s.fqPane}>
            <p className={s.fqText}>{q.quote}</p>
            <p className={s.fqAttr}>{q.attr}</p>
          </div>
        </div>

        <div className={s.fqDots} role="tablist" aria-label="Testimonial">
          {FOUNDER_TESTIMONIALS.map((item, i) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={i === idx}
              aria-controls={`${baseId}-panel`}
              className={`${s.fqDot} ${i === idx ? s.fqDotActive : ""}`}
              onClick={() => setIdx(i)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
