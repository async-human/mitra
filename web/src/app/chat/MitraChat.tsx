"use client";

import { useState, useEffect, useRef, useCallback, Fragment } from "react";
import Link from "next/link";
import { Logo } from "@/components/Logo";

interface JobCard {
  id: string;
  title: string;
}

interface Message {
  role: "mitra" | "user";
  text: string;
  jobCards?: JobCard[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function renderText(text: string) {
  const segments = text.split(/(\*[^*\n]+\*|_[^_\n]+_|\n)/g);
  return segments.map((seg, i) => {
    if (seg.startsWith("*") && seg.endsWith("*"))
      return <strong key={i}>{seg.slice(1, -1)}</strong>;
    if (seg.startsWith("_") && seg.endsWith("_"))
      return <em key={i}>{seg.slice(1, -1)}</em>;
    if (seg === "\n") return <br key={i} />;
    return <Fragment key={i}>{seg}</Fragment>;
  });
}

export function MitraChat({
  userName,
  userEmail,
  userImage,
}: {
  userName?: string;
  userEmail: string;
  userImage?: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialized = useRef(false);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const callApi = useCallback(
    async (message: string) => {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/candidate/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: userEmail, message, user_name: userName }),
        });
        if (!res.ok) throw new Error("request failed");
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "mitra",
            text: data.reply,
            jobCards: data.job_cards?.length ? data.job_cards : undefined,
          },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "mitra", text: "Something went wrong on my end — please try again." },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [userEmail, userName],
  );

  // Load opening greeting once on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    callApi("");
  }, [callApi]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  // Auto-resize textarea
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
    setMessages((prev) => [...prev, { role: "user", text }]);
    await callApi(text);
  }, [input, loading, callApi]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const firstName = userName?.split(" ")[0];

  return (
    <div className="wchat-root">
      {/* Top bar */}
      <header className="wchat-topbar">
        <Logo />
        <div className="wchat-topbar-right">
          {firstName && <span className="wchat-topbar-name">{firstName}</span>}
          <Link href="/dashboard" className="wchat-back">← Dashboard</Link>
        </div>
      </header>

      {/* Messages */}
      <div className="wchat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`wchat-row wchat-row--${msg.role}`}>
            {msg.role === "mitra" && (
              <div className="wchat-av wchat-av--mitra" aria-hidden="true">M</div>
            )}

            <div className="wchat-bubble-wrap">
              <div className={`wchat-bubble wchat-bubble--${msg.role}`}>
                {renderText(msg.text)}
              </div>

              {msg.jobCards && msg.jobCards.length > 0 && (
                <div className="wchat-cards">
                  {msg.jobCards.map((card) => (
                    <button
                      key={card.id}
                      className="wchat-card"
                      onClick={() => {
                        const q = `Tell me more about the ${card.title} role`;
                        setMessages((prev) => [...prev, { role: "user", text: q }]);
                        callApi(q);
                      }}
                    >
                      <span className="wchat-card-title">{card.title}</span>
                      <span className="wchat-card-cta">Tell me more →</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              userImage ? (
                <img src={userImage} alt="" className="wchat-av wchat-av--user" referrerPolicy="no-referrer" />
              ) : (
                <div className="wchat-av wchat-av--user">
                  {(userName?.[0] ?? "U").toUpperCase()}
                </div>
              )
            )}
          </div>
        ))}

        {loading && (
          <div className="wchat-row wchat-row--mitra">
            <div className="wchat-av wchat-av--mitra" aria-hidden="true">M</div>
            <div className="wchat-bubble wchat-bubble--mitra wchat-bubble--typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="wchat-inputbar">
        <textarea
          ref={textareaRef}
          className="wchat-input"
          placeholder="Message Mitra…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={loading}
        />
        <button
          className="wchat-send"
          onClick={handleSend}
          disabled={!input.trim() || loading}
          aria-label="Send"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M13.5 8L2.5 2.5l2 5.5-2 5.5L13.5 8z" fill="currentColor" />
          </svg>
        </button>
      </div>
    </div>
  );
}
