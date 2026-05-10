"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export function TokenInput() {
  const [token, setToken] = useState("");
  const [checking, setChecking] = useState(false);
  const [err, setErr] = useState("");

  async function go() {
    const t = token.trim();
    if (!t) return;
    setChecking(true);
    setErr("");
    try {
      const r = await fetch(`${API_URL}/founder/portal?token=${encodeURIComponent(t)}`);
      if (!r.ok) {
        setErr(r.status === 404 ? "Token not found — double-check and try again." : `Error ${r.status}`);
        setChecking(false);
        return;
      }
      // Token valid — navigate to the portal
      window.location.href = `/founder/portal?token=${encodeURIComponent(t)}`;
    } catch {
      setErr("Could not reach the server. Check your connection.");
      setChecking(false);
    }
  }

  return (
    <div className="fp-token-input-row">
      <input
        className="fp-token-input"
        type="text"
        placeholder="Paste portal token…"
        value={token}
        onChange={e => { setToken(e.target.value); setErr(""); }}
        onKeyDown={e => e.key === "Enter" && go()}
        disabled={checking}
      />
      <button
        className="fp-setup-btn fp-setup-btn--primary fp-token-go-btn"
        onClick={go}
        disabled={!token.trim() || checking}
      >
        {checking ? "Checking…" : "Go →"}
      </button>
      {err && <p className="fp-token-err">{err}</p>}
    </div>
  );
}
