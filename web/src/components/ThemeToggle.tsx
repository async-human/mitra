"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

function SunIcon({ className }: { className?: string }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden
    >
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden
    >
      <path
        d="M21 13.23A8.97 8.97 0 0110.94 4.94 7 7 0 007 19a9 9 0 009-5.77z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** OS / automatic — cycles with light and dark */
function SystemIcon({ className }: { className?: string }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden
    >
      <rect
        x="3"
        y="4"
        width="18"
        height="12"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path d="M8 20h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M12 16v4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="9" cy="10" r="1" fill="currentColor" />
      <circle cx="12.5" cy="10" r="1" fill="currentColor" />
      <circle cx="16" cy="10" r="1" fill="currentColor" />
    </svg>
  );
}

type StoredTheme = "light" | "dark" | "system";

/** Cycles preference: system → light → dark → system (resolved appearance still follows OS in “system”). */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      setMounted(true);
    });
  }, []);

  const preference: StoredTheme =
    theme === "light" || theme === "dark" ? theme : "system";

  const cycle = () => {
    if (preference === "system") setTheme("light");
    else if (preference === "light") setTheme("dark");
    else setTheme("system");
  };

  const label =
    preference === "system"
      ? "Automatic (follows device)"
      : preference === "light"
        ? "Light"
        : "Dark";

  const nextHint =
    preference === "system"
      ? "Next: Light"
      : preference === "light"
        ? "Next: Dark"
        : "Next: Automatic";

  let icon = <SystemIcon />;
  if (mounted && preference === "light") icon = <SunIcon />;
  if (mounted && preference === "dark") icon = <MoonIcon />;

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={cycle}
      aria-label={mounted ? `Theme: ${label}. ${nextHint}.` : "Choose theme"}
      disabled={!mounted}
      title={mounted ? `Theme · ${label} — click for ${preference === "system" ? "light" : preference === "light" ? "dark" : "automatic"}` : "Choose theme"}
    >
      {!mounted ? <span className="theme-toggle-skel" aria-hidden /> : icon}
    </button>
  );
}
