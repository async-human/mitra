"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo, Fragment } from "react";
import { flushSync } from "react-dom";
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
interface WebSource { title: string; url: string }

function safeExternalUrl(raw: string): string | null {
  try {
    const u = new URL(raw.trim());
    if (u.protocol === "http:" || u.protocol === "https:") return u.toString();
  } catch { /* ignore */ }
  return null;
}

function normalizeWebSources(raw: unknown): WebSource[] {
  if (!Array.isArray(raw)) return [];
  const out: WebSource[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const rec = item as { url?: unknown; title?: unknown };
    const url = safeExternalUrl(String(rec.url ?? ""));
    if (!url) continue;
    const title = String(rec.title ?? "").trim() || new URL(url).hostname;
    out.push({ title: title.slice(0, 400), url });
  }
  return out;
}
interface Message {
  role: "mitra" | "user";
  text: string;
  jobCards?: JobCard[];
  pendingToolLabel?: string;
  webSources?: WebSource[];
}

/** Braille dot cycle for in-chat tool progress (matches CLI-style spinners). */
const TOOL_SPINNER_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"] as const;

const TOOL_DISPLAY: Record<string, string> = {
  search_jobs: "search jobs",
  remember_candidate_signals: "save profile",
  get_salary_benchmark: "salary data",
  web_market_research: "web research",
  request_intro: "intro request",
  check_intro_status: "intro status",
  parse_resume: "résumé",
};

function toolDisplayName(name: string): string {
  const d = TOOL_DISPLAY[name];
  if (d) return d;
  return name.replace(/_/g, " ");
}

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
  userName, userEmail, userImage, intent, strengthenIntro,
}: {
  userName?: string;
  userEmail: string;
  userImage?: string;
  intent?: string;
  strengthenIntro?: { jobId: string; company: string; role: string; missing: string[] };
}) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [storedMatchIds, setStoredMatchIds] = useState<string>("");
  const [toolSpinnerFrame, setToolSpinnerFrame] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialized = useRef(false);

  const hasPendingTool = useMemo(
    () => messages.some(m => m.role === "mitra" && m.pendingToolLabel),
    [messages],
  );

  useEffect(() => {
    if (!hasPendingTool) return;
    const id = window.setInterval(() => {
      setToolSpinnerFrame(f => (f + 1) % TOOL_SPINNER_FRAMES.length);
    }, 90);
    return () => window.clearInterval(id);
  }, [hasPendingTool]);

  // On mount: check localStorage for existing matches from a previous session
  useEffect(() => {
    try {
      const raw = localStorage.getItem(matchesKey(userEmail));
      if (raw) {
        const cards: JobCard[] = JSON.parse(raw);
        if (cards.length > 0) {
          const ids = cards.map(c => c.id.replace(/^job_/, "")).join(",");
          queueMicrotask(() => setStoredMatchIds(ids));
        }
      }
    } catch { /* ignore */ }
  }, [userEmail]);

  const callApi = useCallback(async (message: string, opts?: { web_intent?: string }) => {
    setLoading(true);
    // Add a placeholder message that we'll fill in as tokens arrive
    const placeholderIdx = { current: -1 };
    try {
      const res = await fetch(`${API_URL}/candidate/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: userEmail,
          message,
          user_name: userName,
          ...(opts?.web_intent ? { web_intent: opts.web_intent } : {}),
        }),
      });
      if (!res.ok || !res.body) throw new Error("failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let cards: JobCard[] = [];

      // Insert an empty mitra message — we'll stream text into it
      flushSync(() => {
        setMessages(prev => {
          placeholderIdx.current = prev.length;
          return [...prev, { role: "mitra", text: "" }];
        });
      });
      setLoading(false);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE lines: "data: {...}\n\n"
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.t === "tok") {
              setMessages(prev => {
                const next = [...prev];
                const idx = placeholderIdx.current;
                if (idx >= 0 && next[idx]) {
                  next[idx] = {
                    ...next[idx],
                    text: next[idx].text + event.v,
                    pendingToolLabel: undefined,
                  };
                }
                return next;
              });
            } else if (event.t === "tool") {
              const phase = event.phase as string | undefined;
              const name = event.name as string | undefined;
              if (!phase || !name) continue;
              if (phase === "start") {
                const label = toolDisplayName(name);
                setMessages(prev => {
                  const next = [...prev];
                  const idx = placeholderIdx.current;
                  if (idx >= 0 && next[idx]) {
                    next[idx] = { ...next[idx], pendingToolLabel: label };
                  }
                  return next;
                });
              }
              // Keep spinner visible until reply tokens stream (phase "end" is ignored on purpose).
            } else if (event.t === "end") {
              cards = event.cards ?? [];
              const webSources = normalizeWebSources(event.webSources);
              setMessages(prev => {
                if (cards.length === 0 && webSources.length === 0) return prev;
                const next = [...prev];
                const idx = placeholderIdx.current;
                if (idx >= 0 && next[idx]) {
                  const cur = next[idx];
                  next[idx] = {
                    ...cur,
                    ...(cards.length > 0 ? { jobCards: cards } : {}),
                    ...(webSources.length > 0 ? { webSources } : {}),
                  };
                }
                return next;
              });
              if (cards.length > 0) {
                const now = new Date().toISOString();
                const stamped = cards.map(c => ({ ...c, recommended_at: now }));
                localStorage.setItem(matchesKey(userEmail), JSON.stringify(stamped));
                const ids = cards.map(c => c.id.replace(/^job_/, "")).join(",");
                setStoredMatchIds(ids);
                setExiting(true);
                setTimeout(() => router.push(`/matches?ids=${ids}`), 550);
              }
            }
          } catch { /* malformed SSE line — ignore */ }
        }
      }
    } catch {
      if (placeholderIdx.current >= 0) {
        setMessages(prev => {
          const next = [...prev];
          next[placeholderIdx.current] = { role: "mitra", text: "Something went wrong — please try again.", pendingToolLabel: undefined };
          return next;
        });
      } else {
        setMessages(prev => [...prev, { role: "mitra", text: "Something went wrong — please try again.", pendingToolLabel: undefined }]);
      }
    } finally {
      setLoading(false);
    }
  }, [userEmail, userName]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    queueMicrotask(() => {
      if (intent === "update") {
        const msg = "I want to update my job search preferences";
        setMessages([{ role: "user", text: msg }]);
        callApi(msg);
      } else if (intent === "offer_coach") {
        const msg =
          "I'd like help thinking through an offer — what to ask for, how to compare terms, or how to word a reply to the company. I'm not looking for legal advice.";
        setMessages([{ role: "user", text: msg }]);
        callApi(msg, { web_intent: "offer_coach" });
      } else if (intent === "strengthen_intro" && strengthenIntro) {
        const { jobId, company, role, missing } = strengthenIntro;
        const missingLine =
          missing.length > 0
            ? ` I'm told the intro still needs: ${missing.join("; ")}.`
            : "";
        const msg =
          `I tried to request an intro for the **${role}** role at **${company}** ` +
          `(job ref: \`${jobId}\`).${missingLine} ` +
          `Please help me fill in whatever's still missing so Mitra can send a strong intro.`;
        setMessages([{ role: "user", text: msg }]);
        callApi(msg);
      } else {
        callApi("");
      }
    });
  }, [callApi, intent, strengthenIntro]);

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
                  {msg.pendingToolLabel && (
                    <div className="wc-tool-call" role="status" aria-live="polite">
                      <span className="wc-tool-spinner-char" aria-hidden>
                        {TOOL_SPINNER_FRAMES[toolSpinnerFrame]}
                      </span>
                      <span className="wc-tool-label">Calling {msg.pendingToolLabel}</span>
                    </div>
                  )}
                  <p className="wc-msg-mitra-text">{renderText(msg.text)}</p>
                  {msg.webSources && msg.webSources.length > 0 && (
                    <div className="wc-web-sources">
                      <div className="wc-web-sources-heading">Sources</div>
                      <ul className="wc-web-sources-list">
                        {msg.webSources.map((s, i) => (
                          <li key={`${s.url}-${i}`}>
                            <a
                              className="wc-web-source-link"
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <span className="wc-web-source-title">{s.title}</span>
                              <span className="wc-web-source-icon" aria-hidden>↗</span>
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
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
                              {"I'm interested →"}
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
