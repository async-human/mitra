"use client";

import { useState, useEffect, useRef, useCallback, Fragment } from "react";
import Link from "next/link";

interface JobCard { id: string; title: string; }
interface Message { role: "mitra" | "user"; text: string; jobCards?: JobCard[]; }

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function renderText(text: string) {
  return text.split(/(\*[^*\n]+\*|_[^_\n]+_|\n)/g).map((seg, i) => {
    if (seg.startsWith("*") && seg.endsWith("*")) return <strong key={i}>{seg.slice(1, -1)}</strong>;
    if (seg.startsWith("_") && seg.endsWith("_")) return <em key={i}>{seg.slice(1, -1)}</em>;
    if (seg === "\n") return <br key={i} />;
    return <Fragment key={i}>{seg}</Fragment>;
  });
}

export function MitraChat({
  userName, userEmail, userImage,
}: { userName?: string; userEmail: string; userImage?: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialized = useRef(false);

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
      setMessages(prev => [...prev, {
        role: "mitra", text: data.reply,
        jobCards: data.job_cards?.length ? data.job_cards : undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "mitra", text: "Something went wrong — please try again." }]);
    } finally {
      setLoading(false);
    }
  }, [userEmail, userName]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    callApi("");
  }, [callApi]);

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

  const hasMatches = messages.some(m => m.jobCards && m.jobCards.length > 0);

  return (
    <div className="wc-root">
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
        <div className={`wc-step ${hasMatches ? "wc-step--active" : ""}`}>
          <div className="wc-step-dot">2</div>
          <span>Review roles</span>
        </div>
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
            {messages.map((msg, i) =>
              msg.role === "mitra" ? (
                <div key={i} className="wc-msg-mitra">
                  <p className="wc-msg-mitra-text">{renderText(msg.text)}</p>
                  {msg.jobCards && msg.jobCards.length > 0 && (
                    <div className="wc-cards">
                      {msg.jobCards.map(card => (
                        <button key={card.id} className="wc-card-chip"
                          onClick={() => {
                            const q = `Tell me more about the ${card.title} role`;
                            setMessages(prev => [...prev, { role: "user", text: q }]);
                            callApi(q);
                          }}>
                          {card.title} →
                        </button>
                      ))}
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
