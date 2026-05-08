"use client";

import { useEffect, useRef, useState, type ReactNode, type ElementType, type CSSProperties } from "react";

type RevealProps = {
  children: ReactNode;
  /** Tailwind/CSS delay class (`d1`–`d4`) */
  delay?: 1 | 2 | 3 | 4;
  className?: string;
  as?: ElementType;
  style?: CSSProperties;
};

/**
 * Wraps content in a `.reveal` element that animates in when it scrolls
 * into view. Mirrors the behavior of the original landing page.
 */
export function Reveal({
  children,
  delay,
  className = "",
  as: Tag = "div",
  style,
}: RevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            obs.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -48px 0px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const delayClass = delay ? ` d${delay}` : "";
  const inClass = visible ? " in" : "";

  return (
    <Tag
      ref={ref as never}
      className={`reveal${delayClass}${inClass} ${className}`.trim()}
      style={style}
    >
      {children}
    </Tag>
  );
}
