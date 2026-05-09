"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const STORAGE_KEY = "mitra-cookie-consent";

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) setVisible(true);
  }, []);

  function accept() {
    localStorage.setItem(STORAGE_KEY, "all");
    setVisible(false);
  }

  function essential() {
    localStorage.setItem(STORAGE_KEY, "essential");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="cookie-bar" role="region" aria-label="Cookie consent">
      <p className="cookie-text">
        We use essential cookies to run the site, and optional analytics to understand how people use Mitra.{" "}
        <Link href="/cookies" className="cookie-link">Cookie policy</Link>
      </p>
      <div className="cookie-actions">
        <button className="cookie-btn cookie-btn--ess" onClick={essential}>
          Essential only
        </button>
        <button className="cookie-btn cookie-btn--acc" onClick={accept}>
          Accept all
        </button>
      </div>
    </div>
  );
}
