"use client";

import React, { useState, useEffect, useRef, useCallback, Fragment } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface JobCard { id: string; title: string; description: string; why?: string; recommended_at?: string; }

function parseJobCard(card: JobCard): { company: string; fit: string; tags: string[] } {
  const parts = card.description.split(" · ").map(s => s.trim()).filter(Boolean);
  const fitIdx = parts.findIndex(p => p.includes("% fit") || p.includes("%fit"));
  const fit = fitIdx >= 0 ? parts[fitIdx] : "";
  const company = fitIdx > 0 ? parts[0] : (fitIdx === 0 ? "" : parts[0]) ;
  const tags = parts.filter((_, i) => i !== 0 && i !== fitIdx);
  return { company, fit, tags };
}
interface Message { role: "mitra" | "user"; text: string; jobCards?: JobCard[]; }

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function renderInline(line: string): React.ReactNode[] {
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)/g;
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(line)) !== null) {
    if (m.index > last) nodes.push(line.slice(last, m.index));
    const s = m[0];
    if (s.startsWith("**")) nodes.push(<strong key={m.index}>{s.slice(2, -2)}</strong>);
    else if (s.startsWith("*"))  nodes.push(<strong key={m.index}>{s.slice(1, -1)}</strong>);
    else if (s.startsWith("_"))  nodes.push(<em key={m.index}>{s.slice(1, -1)}</em>);
    last = m.index + s.length;
  }
  if (last < line.length) nodes.push(line.slice(last));
  return nodes;
}

function renderText(text: string) {
  const lines = text.split("\n");
  return lines.map((line, i) => (
    <Fragment key={i}>
      {i > 0 && <br />}
      {renderInline(line)}
    </Fragment>
  ));
}

function matchesKey(email: string) {
  return `mitra-matches-${email}`;
}

export function MitraChat({
  userName, userEmail, userImage, intent,
}: { userName?: string; userEmail: string; userImage?: string; intent?: string }) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [storedMatchIds, setStoredMatchIds] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialized = useRef(false);

  // On mount: check localStorage for existing matches from a previous session
  useEffect(() => {
    try {
      const raw = localStorage.getItem(matchesKey(userEmail));
      if (raw) {
        const cards: JobCard[] = JSON.parse(raw);
        if (cards.length > 0) {
          const ids = cards.map(c => c.id.replace(/^job_/, "")).join(",");
          setStoredMatchIds(ids);
        }
      }
    } catch { /* ignore */ }
  }, [userEmail]);

  const callApi = useCallback(async (message: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/candidate/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: userEmail, message, user_name: userName }),
      });
      if (!res.ok) throw new Error("failed");
      const data = await res.json();
      const cards: JobCard[] = data.job_cards ?? [];
      setMessages(prev => [...prev, {
        role: "mitra", text: data.reply,
        jobCards: cards.length ? cards : undefined,
      }]);
      if (cards.length > 0) {
        const now = new Date().toISOString();
        const stamped = cards.map(c => ({ ...c, recommended_at: now }));
        localStorage.setItem(matchesKey(userEmail), JSON.stringify(stamped));
        const ids = cards.map(c => c.id.replace(/^job_/, "")).join(",");
        setStoredMatchIds(ids);
        setExiting(true);
        setTimeout(() => router.push(`/matches?ids=${ids}`), 550);
      }
    } catch {
      setMessages(prev => [...prev, { role: "mitra", text: "Something went wrong — please try again." }]);
    } finally {
      setLoading(false);
    }
  }, [userEmail, userName]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    if (intent === "update") {
      const msg = "I want to update my job search preferences";
      setMessages([{ role: "user", text: msg }]);
      callApi(msg);
    } else {
      callApi("");
    }
  }, [callApi, intent]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  }, [input]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text }]);
    await callApi(text);
  }, [input, loading, callApi]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const hasMatches = messages.some(m => m.jobCards && m.jobCards.length > 0) || !!storedMatchIds;

  return (
    <div className={`wc-root${exiting ? " wc-root--exiting" : ""}`}>
      {/* Top bar */}
      <header className="wc-topbar">
        <div className="wc-logo">
          <div className="wc-logo-mark">M</div>
          <span className="wc-logo-text">Mitra.</span>
        </div>
        <div className="wc-topbar-right">
          {userName && <span className="wc-username">{userName.split(" ")[0]}</span>}
          <Link href="/dashboard" className="wc-back">← Dashboard</Link>
        </div>
      </header>

      {/* Step progress */}
      <div className="wc-steps">
        <div className="wc-step wc-step--active">
          <div className="wc-step-dot">1</div>
          <span>Tell us about you</span>
        </div>
        <div className="wc-step-track">
          <div className={`wc-step-fill ${hasMatches ? "wc-step-fill--done" : ""}`} />
        </div>
        {hasMatches && storedMatchIds ? (
          <Link href={`/matches?ids=${storedMatchIds}`} className="wc-step wc-step--active wc-step--done-link">
            <div className="wc-step-dot wc-step-dot--done">✓</div>
            <span>Review roles</span>
          </Link>
        ) : (
          <div className={`wc-step ${hasMatches ? "wc-step--active" : ""}`}>
            <div className="wc-step-dot">2</div>
            <span>Review roles</span>
          </div>
        )}
      </div>

      {/* Chat card */}
      <div className="wc-card-wrap">
        <div className="wc-card">
          {/* Card header */}
          <div className="wc-card-header">
            <div className="wc-agent-av">M</div>
            <span className="wc-agent-name">Mitra</span>
          </div>

          {/* Messages */}
          <div className="wc-messages">

            {/* Matches-ready pinned card — lives inside the message stream when shortlist exists */}
            {storedMatchIds && !exiting && (
              <Link href={`/matches?ids=${storedMatchIds}`} className="wc-shortlist-card">
                <div className="wc-shortlist-card-icon">✦</div>
                <div className="wc-shortlist-card-body">
                  <p className="wc-shortlist-card-title">Your shortlist is ready</p>
                  <p className="wc-shortlist-card-sub">View your curated roles →</p>
                </div>
              </Link>
            )}

            {messages.map((msg, i) =>
              msg.role === "mitra" ? (
                <div key={i} className="wc-msg-mitra">
                  <p className="wc-msg-mitra-text">{renderText(msg.text)}</p>
                  {msg.jobCards && msg.jobCards.length > 0 && (
                    <div className="wc-job-cards">
                      {msg.jobCards.map(card => {
                        const { company, fit, tags } = parseJobCard(card);
                        return (
                          <div key={card.id} className="wc-job-card">
                            <div className="wc-job-card-top">
                              <div className="wc-job-card-titles">
                                <span className="wc-job-role">{card.title}</span>
                                {company && <span className="wc-job-company">{company}</span>}
                              </div>
                              {fit && <span className="wc-job-fit">{fit}</span>}
                            </div>
                            {tags.length > 0 && (
                              <div className="wc-job-tags">
                                {tags.map((tag, ti) => (
                                  <span key={ti} className="wc-job-tag">{tag}</span>
                                ))}
                              </div>
                            )}
                            <button className="wc-job-cta"
                              onClick={() => {
                                const q = `I'm interested in the ${card.title} role at ${company || "this company"} — tell me more`;
                                setMessages(prev => [...prev, { role: "user", text: q }]);
                                callApi(q);
                              }}>
                              I'm interested →
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <div key={i} className="wc-msg-user-wrap">
                  <div className="wc-msg-user">{msg.text}</div>
                </div>
              )
            )}

            {loading && (
              <div className="wc-msg-mitra">
                <div className="wc-typing"><span /><span /><span /></div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="wc-input-bar">
            <textarea
              ref={textareaRef}
              className="wc-input"
              placeholder="Message Mitra…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
            />
            <button className="wc-send" onClick={handleSend} disabled={!input.trim() || loading} aria-label="Send">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M13.5 8L2.5 2.5l2 5.5-2 5.5L13.5 8z" fill="currentColor" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
