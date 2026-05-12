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
  exp_min_yrs?: number;
  exp_max_yrs?: number;
  stack?: string[];
  summary?: string;
  responsibilities?: string[];
  requirements?: string[];
  nice_to_have?: string[];
}

interface ChatMsg {
  role: "mitra" | "user";
  text: string;
  jobPreview?: JobPreview;
  portalUrl?: string;
  isFile?: boolean;
}

// ── Text rendering ────────────────────────────────────────────────────────────

function renderInline(line: string): React.ReactNode[] {
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const nodes: React.ReactNode[] = [];
  let last = 0, m: RegExpExecArray | null;
  while ((m = regex.exec(line)) !== null) {
    if (m.index > last) nodes.push(line.slice(last, m.index));
    const s = m[0];
    nodes.push(<strong key={m.index}>{s.startsWith("**") ? s.slice(2, -2) : s.slice(1, -1)}</strong>);
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

// ── Helpers ───────────────────────────────────────────────────────────────────

function salaryLabel(min?: number, max?: number) {
  if (!min && !max) return null;
  if (min && max && min !== max) return `₹${min}–${max}L / yr`;
  return `₹${min || max}L / yr`;
}

function expLabel(min?: number, max?: number) {
  if (!min && !max) return null;
  if (min && max && min !== max) return `${min}–${max} yrs exp`;
  return `${min || max}+ yrs exp`;
}

const REMOTE_LABEL: Record<string, string> = {
  remote: "Remote", hybrid: "Hybrid", onsite: "In-office",
};
const EMP_LABEL: Record<string, string> = {
  full_time: "Full-time", contract: "Contract", part_time: "Part-time",
};

// ── JD Extraction Loader ──────────────────────────────────────────────────────

const EXTRACT_STEPS = [
  "Parsing document structure",
  "Reading role title & company",
  "Extracting location & work type",
  "Identifying experience range",
  "Parsing tech stack & skills",
  "Reading key responsibilities",
  "Extracting qualifications",
  "Writing candidate summary",
];

// Cumulative delays (ms) — starts fast, slows for later steps
const STEP_DELAYS = [300, 950, 1700, 2600, 3600, 4700, 5900, 7200];

function JDExtractionLoader() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    // Skip the last timer — final step stays "active" (spinning) until the
    // API actually responds and the loader unmounts.
    const timers = STEP_DELAYS.slice(0, EXTRACT_STEPS.length - 1).map((delay, i) =>
      setTimeout(() => setPhase(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="fjb-extractor">
      <div className="fjb-extractor-icon">
        <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
          <rect x="4" y="2" width="15" height="20" rx="2.5" stroke="#1C1917" strokeWidth="1.4" />
          <path d="M8 7h8M8 11h8M8 15h5" stroke="#1C1917" strokeWidth="1.3" strokeLinecap="round" />
          <circle cx="20" cy="20" r="4" fill="#FAF8F5" stroke="#1C1917" strokeWidth="1.2" />
          <path d="M18.5 20h3M20 18.5v3" stroke="#16A34A" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
        <div className="fjb-extractor-scan" />
      </div>

      <p className="fjb-extractor-title">Reading your JD</p>
      <p className="fjb-extractor-sub">Extracting all sections & requirements</p>

      <ol className="fjb-extractor-steps">
        {EXTRACT_STEPS.map((label, i) => {
          const isDone   = i < phase;
          const isActive = i === phase && phase < EXTRACT_STEPS.length;
          const status   = isDone ? "done" : isActive ? "active" : "pending";
          return (
            <li key={i} className={`fjb-extractor-step fjb-extractor-step--${status}`}>
              <span className="fjb-extractor-step-icon">
                {isDone ? (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                    <path d="M2 5l2.5 2.5L8 2.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : isActive ? (
                  <span className="fjb-extractor-spinner" />
                ) : (
                  <span className="fjb-extractor-dot" />
                )}
              </span>
              {label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// ── Job preview card ──────────────────────────────────────────────────────────

function JobPreviewCard({ job, onPost, onEdit, posting }: {
  job: JobPreview; onPost: () => void; onEdit: () => void; posting: boolean;
}) {
  const salary = salaryLabel(job.salary_min_lpa, job.salary_max_lpa);
  const exp    = expLabel(job.exp_min_yrs, job.exp_max_yrs);
  const badges = [
    job.stage, job.sector,
    job.location,
    job.remote_policy ? REMOTE_LABEL[job.remote_policy] : null,
    job.employment && job.employment !== "full_time" ? EMP_LABEL[job.employment] : null,
  ].filter(Boolean) as string[];

  return (
    <div className="fjb-preview">

      {/* Eyebrow */}
      <p className="fjb-preview-eyebrow">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" style={{ display:"inline",verticalAlign:"middle",marginRight:5 }}>
          <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.3" />
          <path d="M6 4v3M6 8.5v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
        Preview — how candidates will see this role
      </p>

      {/* Block 1: Header */}
      <div className="fjb-preview-block fjb-preview-block--header">
        <div className="fjb-preview-av">
          {(job.company || "??").slice(0, 2).toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 className="fjb-preview-title">{job.title || "Untitled role"}</h3>
          <p className="fjb-preview-company">{job.company}</p>
        </div>
        <div className="fjb-preview-meta-pills">
          {salary && <span className="fjb-preview-salary">{salary}</span>}
          {exp    && <span className="fjb-preview-exp">{exp}</span>}
        </div>
      </div>

      {/* Block 2: Meta strip — badges + stack */}
      {(badges.length > 0 || (job.stack && job.stack.length > 0)) && (
        <div className="fjb-preview-block fjb-preview-block--meta">
          {badges.length > 0 && (
            <div className="fjb-preview-badges">
              {badges.map((b, i) => <span key={i} className="fjb-preview-badge">{b}</span>)}
            </div>
          )}
          {job.stack && job.stack.length > 0 && (
            <div className="fjb-preview-stack">
              {job.stack.map((t, i) => <span key={i} className="fjb-preview-tag">{t}</span>)}
            </div>
          )}
        </div>
      )}

      {/* Block 3: About the Role */}
      {job.summary && (
        <div className="fjb-preview-block">
          <p className="fjb-preview-block-title">About the Role</p>
          <p className="fjb-preview-block-text">{job.summary}</p>
        </div>
      )}

      {/* Block 4: Key Responsibilities */}
      {job.responsibilities && job.responsibilities.length > 0 && (
        <div className="fjb-preview-block">
          <p className="fjb-preview-block-title">Key Responsibilities</p>
          <ul className="fjb-preview-block-list">
            {job.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {/* Block 5: Required Skills & Experience */}
      {job.requirements && job.requirements.length > 0 && (
        <div className="fjb-preview-block">
          <p className="fjb-preview-block-title">Required Skills & Experience</p>
          <ul className="fjb-preview-block-list">
            {job.requirements.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {/* Block 6: Preferred Qualifications */}
      {job.nice_to_have && job.nice_to_have.length > 0 && (
        <div className="fjb-preview-block">
          <p className="fjb-preview-block-title">Preferred Qualifications</p>
          <ul className="fjb-preview-block-list fjb-preview-block-list--muted">
            {job.nice_to_have.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="fjb-preview-actions">
        <button className="fjb-preview-post-btn" onClick={onPost} disabled={posting}>
          {posting
            ? <><span className="fjb-btn-spinner" /> Posting…</>
            : <>Post this role <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 7h8M8 4l3 3-3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg></>
          }
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
    try { await navigator.clipboard.writeText(portalUrl); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    catch { /* ignore */ }
  }, [portalUrl]);

  return (
    <div className="fjb-success">
      <div className="fjb-success-check">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M4 10l5 5 7-8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="fjb-success-text">
        <p className="fjb-success-title">Role is live — candidates incoming</p>
        <p className="fjb-success-sub">Mitra is now matching engineers to this role. You&apos;ll see introductions in your portal.</p>
      </div>
      <div className="fjb-success-btns">
        <a href={portalUrl} className="fjb-success-portal-btn">Open portal →</a>
        <button className="fjb-success-copy-btn" onClick={copy}>{copied ? "Copied!" : "Copy link"}</button>
      </div>
    </div>
  );
}

// ── Hero (initial state before first message) ─────────────────────────────────

function Hero({ onFile, onText, disabled }: {
  onFile: (f: File) => void;
  onText: (t: string) => void;
  disabled: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const [input, setInput] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFile(f);
  }, [onFile]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (input.trim()) { onText(input.trim()); setInput(""); } }
  }, [input, onText]);

  return (
    <div className="fjb-hero">
      <div className="fjb-hero-icon">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <rect width="28" height="28" rx="8" fill="#1C1917" />
          <path d="M7 21V10l7-3 7 3v11l-7 2-7-2Z" stroke="white" strokeWidth="1.4" strokeLinejoin="round" />
          <path d="M14 7v14M7 10l7 3 7-3" stroke="white" strokeWidth="1.4" strokeLinejoin="round" />
        </svg>
      </div>
      <h1 className="fjb-hero-title">Post a role in minutes</h1>
      <p className="fjb-hero-sub">Upload a JD or describe the role — Mitra extracts all the details, writes a candidate-facing summary, and posts it for you.</p>

      {/* Drop zone */}
      <div
        className={`fjb-drop${dragging ? " fjb-drop--active" : ""}${disabled ? " fjb-drop--disabled" : ""}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && fileRef.current?.click()}
      >
        <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" style={{ display: "none" }}
          onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f); }} />
        <div className="fjb-drop-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 4v10M8 8l4-4 4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M4 17v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </div>
        <p className="fjb-drop-label">{dragging ? "Drop it here" : "Drag & drop your JD here"}</p>
        <p className="fjb-drop-formats">PDF or Word · up to 10 MB · <span className="fjb-drop-browse">browse files</span></p>
      </div>

      <div className="fjb-hero-divider"><span>or describe the role</span></div>

      {/* Inline text input in hero */}
      <div className="fjb-hero-input-wrap">
        <textarea
          className="fjb-hero-input"
          placeholder="e.g. Senior Backend Engineer at Finstack, Series A fintech. Remote, 30–40 LPA. Python, FastAPI, PostgreSQL."
          value={input}
          rows={3}
          disabled={disabled}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className="fjb-hero-send"
          disabled={!input.trim() || disabled}
          onClick={() => { if (input.trim()) { onText(input.trim()); setInput(""); } }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M14 8H2M8 3l6 5-6 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function FounderJobBuilder({ authEmail, founderName }: {
  authEmail: string; founderName: string;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHint, setLoadingHint] = useState("")
  const [posting, setPosting] = useState(false);
  const [stage, setStage] = useState<"collecting" | "confirming" | "posted">("collecting");
  const [currentPreview, setCurrentPreview] = useState<JobPreview | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const initialized = useRef(false);

  const hasUserMessage = messages.some(m => m.role === "user");

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
  }, []);

  // ── API ────────────────────────────────────────────────────────────────────

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

      setMessages(prev => [...prev, {
        role: "mitra",
        text: data.reply,
        jobPreview: data.stage === "confirming" ? (data.job_preview ?? undefined) : undefined,
        portalUrl:  data.stage === "posted"     ? (data.portal_url  ?? undefined) : undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "mitra", text: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }, [authEmail, scrollToBottom]);

  // Init — just load greeting, don't show it until hero is dismissed
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    // Pre-warm session silently — greeting shows after first user action
  }, []);

  // ── Send text ──────────────────────────────────────────────────────────────

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    setInput("");
    // On first message, get greeting + response together
    if (!hasUserMessage) {
      setMessages([{ role: "user", text: text.trim() }]);
    } else {
      setMessages(prev => [...prev, { role: "user", text: text.trim() }]);
    }
    scrollToBottom();
    await callChat(text.trim());
  }, [loading, hasUserMessage, callChat, scrollToBottom]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  }, [input, sendMessage]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  }, []);

  // ── Upload ─────────────────────────────────────────────────────────────────

  const handleFile = useCallback(async (file: File) => {
    if (loading) return;
    setLoading(true);
    setLoadingHint("Reading your JD…");
    setMessages(prev => [...prev, { role: "user", text: file.name, isFile: true }]);
    scrollToBottom();
    try {
      const form = new FormData();
      form.append("session_id", authEmail);
      form.append("auth_email", authEmail);
      form.append("file", file);

      const res = await fetch(`${API_URL}/founder/job-builder/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || `Upload failed (${res.status})`);
      }
      const data = await res.json();
      setStage(data.stage);
      if (data.job_preview) setCurrentPreview(data.job_preview);
      setMessages(prev => [...prev, {
        role: "mitra",
        text: data.reply,
        jobPreview: data.stage === "confirming" ? (data.job_preview ?? undefined) : undefined,
        portalUrl:  data.stage === "posted"     ? (data.portal_url  ?? undefined) : undefined,
      }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "mitra", text: e instanceof Error ? e.message : "Upload failed." }]);
    } finally {
      setLoading(false);
      setLoadingHint("");
      scrollToBottom();
    }
  }, [loading, authEmail, scrollToBottom]);

  // ── Confirm post ───────────────────────────────────────────────────────────

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
      setMessages(prev => [...prev, {
        role: "mitra", text: data.reply,
        portalUrl: data.portal_url ?? undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "mitra", text: "Something went wrong. Please try again." }]);
    } finally {
      setPosting(false);
      scrollToBottom();
    }
  }, [posting, authEmail, scrollToBottom]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="fjb-root">
      {/* Topbar */}
      <header className="fjb-topbar">
        <Link href="/founder/setup" className="fjb-topbar-logo">
          Mitra<span className="fjb-topbar-dot">.</span>
        </Link>
        <nav className="fjb-topbar-nav">
          <Link href="/founder/setup" className="fjb-topbar-link">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M9 11L5 7l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            My roles
          </Link>
        </nav>
      </header>

      <main className="fjb-main">
        {/* Hero — shown before first user message */}
        {!hasUserMessage && (
          <Hero onFile={handleFile} onText={sendMessage} disabled={loading} />
        )}

        {/* Chat — shown after first user message */}
        {hasUserMessage && (
          <div className="fjb-chat">
            <div className="fjb-messages">
              {messages.map((msg, i) => (
                <div key={i} className={`fjb-msg fjb-msg--${msg.role}`}>
                  {msg.role === "mitra" && <div className="fjb-av">M</div>}

                  <div className="fjb-msg-body">
                    {msg.isFile ? (
                      <div className="fjb-file-pill">
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                          <path d="M3 1h6l3 3v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                          <path d="M8 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                        </svg>
                        {msg.text}
                      </div>
                    ) : !msg.jobPreview && !msg.portalUrl ? (
                      <div className="fjb-bubble">{renderText(msg.text)}</div>
                    ) : null}

                    {/* Preview card — rendered alone, no duplicate text bubble */}
                    {msg.jobPreview && stage === "confirming" && (
                      <JobPreviewCard
                        job={msg.jobPreview}
                        onPost={handlePostConfirm}
                        onEdit={() => textareaRef.current?.focus()}
                        posting={posting}
                      />
                    )}

                    {/* Success card */}
                    {msg.portalUrl && stage === "posted" && (
                      <PortalSuccessCard portalUrl={msg.portalUrl} />
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                loadingHint === "Reading your JD…" ? (
                  <JDExtractionLoader />
                ) : (
                  <div className="fjb-msg fjb-msg--mitra">
                    <div className="fjb-av">M</div>
                    <div className="fjb-msg-body">
                      <div className="fjb-bubble fjb-bubble--typing">
                        <span /><span /><span />
                        {loadingHint && <span className="fjb-typing-hint">{loadingHint}</span>}
                      </div>
                    </div>
                  </div>
                )
              )}

              <div ref={bottomRef} />
            </div>

            {/* Input bar */}
            {stage !== "posted" && (
              <div className="fjb-inputbar-wrap">
                <div className="fjb-inputbar">
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.doc"
                    style={{ display: "none" }}
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); if (e.target) e.target.value = ""; }} />

                  <button className="fjb-attach-btn" onClick={() => fileRef.current?.click()}
                    disabled={loading || posting} title="Upload JD" aria-label="Upload JD">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                      <path d="M8 2v8M5 5l3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M2 12v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </button>

                  <textarea
                    ref={textareaRef}
                    className="fjb-input"
                    placeholder={stage === "confirming"
                      ? `Say "post it" to go live, or describe what to change…`
                      : "Ask a follow-up or add more details…"}
                    value={input}
                    rows={1}
                    disabled={loading || posting}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                  />

                  <button className="fjb-send-btn"
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim() || loading || posting}
                    aria-label="Send">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                      <path d="M14 8H2M9 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
