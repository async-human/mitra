"use client";

import React, {
  useState, useEffect, useRef, useCallback, Fragment,
} from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── Types ─────────────────────────────────────────────────────────────────────

interface JobPreview {
  title?: string;
  company?: string;
  stage?: string;
  sector?: string;
  location?: string;
  remote_policy?: string;
  employment?: string;
  salary_min_lpa?: number;
  salary_max_lpa?: number;
  stack?: string[];
  summary?: string;
}

interface ChatMessage {
  role: "mitra" | "user";
  text: string;
  jobPreview?: JobPreview;
  portalUrl?: string;
  isUpload?: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderInline(line: string): React.ReactNode[] {
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(line)) !== null) {
    if (m.index > last) nodes.push(line.slice(last, m.index));
    const s = m[0];
    if (s.startsWith("**")) nodes.push(<strong key={m.index}>{s.slice(2, -2)}</strong>);
    else nodes.push(<strong key={m.index}>{s.slice(1, -1)}</strong>);
    last = m.index + s.length;
  }
  if (last < line.length) nodes.push(line.slice(last));
  return nodes;
}

function renderText(text: string) {
  return text.split("\n").map((line, i) => (
    <Fragment key={i}>{i > 0 && <br />}{renderInline(line)}</Fragment>
  ));
}

function salaryLabel(min?: number, max?: number): string | null {
  if (!min && !max) return null;
  if (min && max && min !== max) return `₹${min}–${max}L / yr`;
  return `₹${min || max}L / yr`;
}

function remoteBadge(policy?: string): string {
  if (!policy) return "";
  return { remote: "Remote", hybrid: "Hybrid", onsite: "In-office" }[policy] ?? policy;
}

function employmentBadge(emp?: string): string {
  return { full_time: "Full-time", contract: "Contract", part_time: "Part-time" }[emp ?? ""] ?? "";
}

// ── Job preview card ──────────────────────────────────────────────────────────

function JobPreviewCard({
  job, onPost, onEdit, posting,
}: {
  job: JobPreview;
  onPost: () => void;
  onEdit: () => void;
  posting: boolean;
}) {
  const salary = salaryLabel(job.salary_min_lpa, job.salary_max_lpa);

  return (
    <div className="fjb-preview">
      <div className="fjb-preview-eyebrow">Preview — how candidates will see this role</div>

      <div className="fjb-preview-header">
        <div className="fjb-preview-av">
          {(job.company || "??").slice(0, 2).toUpperCase()}
        </div>
        <div>
          <h3 className="fjb-preview-title">{job.title || "Untitled role"}</h3>
          <p className="fjb-preview-company">{job.company}</p>
        </div>
      </div>

      <div className="fjb-preview-badges">
        {job.stage       && <span className="fjb-preview-badge">{job.stage}</span>}
        {job.sector      && <span className="fjb-preview-badge">{job.sector}</span>}
        {job.location    && <span className="fjb-preview-badge">{job.location}</span>}
        {job.remote_policy && <span className="fjb-preview-badge">{remoteBadge(job.remote_policy)}</span>}
        {job.employment  && job.employment !== "full_time" && <span className="fjb-preview-badge">{employmentBadge(job.employment)}</span>}
        {salary          && <span className="fjb-preview-badge fjb-preview-badge--salary">{salary}</span>}
      </div>

      {job.stack && job.stack.length > 0 && (
        <div className="fjb-preview-stack">
          {job.stack.map((t, i) => <span key={i} className="fjb-preview-tag">{t}</span>)}
        </div>
      )}

      {job.summary && (
        <p className="fjb-preview-summary">{job.summary}</p>
      )}

      <div className="fjb-preview-actions">
        <button
          className="fjb-preview-post-btn"
          onClick={onPost}
          disabled={posting}
        >
          {posting ? (
            <><span className="fjb-spinner" /> Posting…</>
          ) : (
            "Post this role →"
          )}
        </button>
        <button className="fjb-preview-edit-btn" onClick={onEdit} disabled={posting}>
          Edit something
        </button>
      </div>
    </div>
  );
}

// ── Portal success card ───────────────────────────────────────────────────────

function PortalSuccessCard({ portalUrl }: { portalUrl: string }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(portalUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  }, [portalUrl]);

  return (
    <div className="fjb-success">
      <div className="fjb-success-icon">✓</div>
      <h3 className="fjb-success-title">Role is live!</h3>
      <p className="fjb-success-sub">
        Mitra is now matching candidates. You&apos;ll see introductions appear in your portal as they come in.
      </p>
      <a href={portalUrl} className="fjb-success-portal-btn">
        Open founder portal →
      </a>
      <button className="fjb-success-copy-btn" onClick={copy}>
        {copied ? "Copied!" : "Copy portal link"}
      </button>
    </div>
  );
}

// ── Upload zone ───────────────────────────────────────────────────────────────

function UploadZone({ onFile, disabled }: { onFile: (f: File) => void; disabled: boolean }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFile(f);
  }, [onFile]);

  return (
    <div
      className={`fjb-upload-zone${dragging ? " fjb-upload-zone--drag" : ""}${disabled ? " fjb-upload-zone--disabled" : ""}`}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        style={{ display: "none" }}
        onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <path d="M4 14v3a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M11 4v9M8 7l3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>Upload JD <span className="fjb-upload-formats">PDF or Word</span></span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function FounderJobBuilder({
  authEmail,
  founderName,
}: {
  authEmail: string;
  founderName: string;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const [stage, setStage] = useState<"collecting" | "confirming" | "posted">("collecting");
  const [currentPreview, setCurrentPreview] = useState<JobPreview | null>(null);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialized = useRef(false);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 60);
  }, []);

  // ── API call ──────────────────────────────────────────────────────────────

  const callChat = useCallback(async (message: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/founder/job-builder/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: authEmail, message, auth_email: authEmail }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();

      setStage(data.stage);
      if (data.job_preview) setCurrentPreview(data.job_preview);
      if (data.portal_url)  setPortalUrl(data.portal_url);

      setMessages(prev => [
        ...prev,
        {
          role: "mitra",
          text: data.reply,
          jobPreview: data.stage === "confirming" ? (data.job_preview ?? undefined) : undefined,
          portalUrl:  data.stage === "posted"     ? (data.portal_url  ?? undefined) : undefined,
        },
      ]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "mitra",
        text: "Something went wrong. Please try again.",
      }]);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }, [authEmail, scrollToBottom]);

  // ── Init ──────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    callChat("");
  }, [callChat]);

  // ── Send message ──────────────────────────────────────────────────────────

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: trimmed }]);
    scrollToBottom();
    await callChat(trimmed);
  }, [loading, callChat, scrollToBottom]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }, [input, sendMessage]);

  // Auto-grow textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  }, []);

  // ── File upload ───────────────────────────────────────────────────────────

  const handleFile = useCallback(async (file: File) => {
    if (loading) return;
    setLoading(true);
    setMessages(prev => [...prev, { role: "user", text: `📎 ${file.name}`, isUpload: true }]);
    scrollToBottom();

    try {
      const form = new FormData();
      form.append("session_id", authEmail);
      form.append("auth_email", authEmail);
      form.append("file", file);

      const res = await fetch(`${API_URL}/founder/job-builder/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || `Upload failed (${res.status})`);
      }
      const data = await res.json();

      setStage(data.stage);
      if (data.job_preview) setCurrentPreview(data.job_preview);
      if (data.portal_url)  setPortalUrl(data.portal_url);

      setMessages(prev => [
        ...prev,
        {
          role: "mitra",
          text: data.reply,
          jobPreview: data.stage === "confirming" ? (data.job_preview ?? undefined) : undefined,
          portalUrl:  data.stage === "posted"     ? (data.portal_url  ?? undefined) : undefined,
        },
      ]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "mitra",
        text: e instanceof Error ? e.message : "Upload failed. Please try again.",
      }]);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }, [loading, authEmail, scrollToBottom]);

  // ── Post confirmation (from preview card button) ───────────────────────────

  const handlePostConfirm = useCallback(async () => {
    if (posting) return;
    setPosting(true);
    setMessages(prev => [...prev, { role: "user", text: "Post it" }]);
    scrollToBottom();
    try {
      const res = await fetch(`${API_URL}/founder/job-builder/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: authEmail, message: "Post it", auth_email: authEmail }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setStage(data.stage);
      if (data.portal_url) setPortalUrl(data.portal_url);
      setMessages(prev => [...prev, {
        role: "mitra",
        text: data.reply,
        portalUrl: data.portal_url ?? undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "mitra", text: "Something went wrong. Please try again." }]);
    } finally {
      setPosting(false);
      scrollToBottom();
    }
  }, [posting, authEmail, scrollToBottom]);

  const handleEditRequest = useCallback(() => {
    textareaRef.current?.focus();
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="fjb-root">
      {/* Topbar */}
      <header className="fjb-topbar">
        <Link href="/founder/setup" className="fjb-topbar-logo">
          Mitra<span className="fjb-topbar-dot">.</span>
        </Link>
        <div className="fjb-topbar-right">
          <Link href="/founder/setup" className="fjb-topbar-link">← My roles</Link>
        </div>
      </header>

      <main className="fjb-main">
        <div className="fjb-chat-wrap">

          {/* Upload zone — shown until first user message */}
          {messages.filter(m => m.role === "user").length === 0 && (
            <UploadZone onFile={handleFile} disabled={loading} />
          )}

          {/* Messages */}
          <div className="fjb-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`fjb-msg fjb-msg--${msg.role}`}>
                {msg.role === "mitra" && (
                  <div className="fjb-msg-av">M</div>
                )}
                <div className="fjb-msg-body">
                  <div className="fjb-msg-bubble">
                    {renderText(msg.text)}
                  </div>

                  {/* Job preview card — inline in chat */}
                  {msg.jobPreview && stage === "confirming" && (
                    <JobPreviewCard
                      job={msg.jobPreview}
                      onPost={handlePostConfirm}
                      onEdit={handleEditRequest}
                      posting={posting}
                    />
                  )}

                  {/* Portal success card */}
                  {msg.portalUrl && stage === "posted" && (
                    <PortalSuccessCard portalUrl={msg.portalUrl} />
                  )}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="fjb-msg fjb-msg--mitra">
                <div className="fjb-msg-av">M</div>
                <div className="fjb-msg-body">
                  <div className="fjb-msg-bubble fjb-msg-bubble--loading">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input row — hidden once posted */}
          {stage !== "posted" && (
            <div className="fjb-input-row">
              {messages.filter(m => m.role === "user").length > 0 && (
                <UploadZone onFile={handleFile} disabled={loading} />
              )}
              <div className="fjb-input-wrap">
                <textarea
                  ref={textareaRef}
                  className="fjb-input"
                  placeholder={
                    stage === "confirming"
                      ? "Say "post it" to go live, or describe what to change…"
                      : "Paste your job description, or describe the role…"
                  }
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  disabled={loading || posting}
                />
                <button
                  className="fjb-send-btn"
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || loading || posting}
                  aria-label="Send"
                >
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                    <path d="M15.5 9H2.5M9 3l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
