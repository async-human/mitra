'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import styles from './onboarding.module.css'

// ── Types ────────────────────────────────────────────────────────────────────

type Message = {
  id: string
  role: 'in' | 'out'
  text: string
  time: string
  attachment?: { name: string; size: number }
}

type Signals = Record<string, string>

type ChatResponse = {
  reply: string
  signals: Signals
  step: string
  progress: number
  complete: boolean
  quick_replies: string[]
}

// ── Config ───────────────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

// ── Helpers ──────────────────────────────────────────────────────────────────

function getTime(): string {
  const d = new Date()
  const h = d.getHours()
  const m = d.getMinutes()
  return `${h}:${m < 10 ? '0' : ''}${m} ${h < 12 ? 'AM' : 'PM'}`
}

function makeId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

// ── Component ────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const { data: authSession } = useSession()
  const authEmail = authSession?.user?.email ?? ''

  const [messages, setMessages]         = useState<Message[]>([])
  const [visibleIds, setVisibleIds]     = useState<Set<string>>(new Set())
  const [signals, setSignals]           = useState<Signals>({})
  const [step, setStep]                 = useState<string>('role')
  const [progress, setProgress]         = useState(5)
  const [complete, setComplete]         = useState(false)
  const [quickReplies, setQuickReplies] = useState<string[]>([])
  const [isWaiting, setIsWaiting]       = useState(false)
  const [inputValue, setInputValue]     = useState('')
  const [initDone, setInitDone]         = useState(false)
  const [portalUrl, setPortalUrl]       = useState<string>('')
  const [portalLoading, setPortalLoading] = useState(false)

  // Pre-chat form state
  const [phase, setPhase]             = useState<'form' | 'chat'>('form')
  const [founderName, setFounderName] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [companyUrl, setCompanyUrl]   = useState('')
  const [linkedinUrl, setLinkedinUrl] = useState('')

  const sessionIdRef = useRef<string>('')
  const chatBodyRef  = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // Captures form values at the moment the chat phase starts (avoids stale closure)
  const formDataRef  = useRef<{ founderName: string; companyName: string; companyUrl: string; linkedinUrl: string } | null>(null)

  // ── Pre-fill founder name from auth session ──────────────────────────────

  useEffect(() => {
    if (authSession?.user?.name) {
      setFounderName(prev => prev || authSession.user!.name!)
    }
  }, [authSession?.user?.name])

  // ── Init: session ID + body overflow + greeting (fires when chat phase starts) ──

  useEffect(() => {
    if (phase !== 'chat') return
    if (typeof window === 'undefined') return

    let sid = sessionStorage.getItem('mitra_founder_session') ?? ''
    if (!sid) {
      sid = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now()
      sessionStorage.setItem('mitra_founder_session', sid)
    }
    sessionIdRef.current = sid

    document.body.style.overflow = 'hidden'

    const fd = formDataRef.current

    setIsWaiting(true)
    fetch(`${API_URL}/founder/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id:   sid,
        message:      '',
        auth_email:   authEmail || undefined,
        founder_name: fd?.founderName || undefined,
        company_name: fd?.companyName || undefined,
        company_url:  fd?.companyUrl  || undefined,
        linkedin_url: fd?.linkedinUrl || undefined,
      }),
    })
      .then(r => r.json())
      .then((data: ChatResponse) => { applyResponse(data) })
      .catch(() => {
        const greeting = fd?.companyName
          ? `Hi ${fd.founderName || 'there'} — I'm Mitra. I can see you're from *${fd.companyName}*. What role are you most urgently hiring for right now?`
          : "Hi — I'm Mitra, a talent agent for funded startups. *What role are you most urgently hiring for right now?*"
        addMessage('in', greeting)
      })
      .finally(() => {
        setIsWaiting(false)
        setInitDone(true)
      })

    return () => { document.body.style.overflow = '' }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase])

  // ── Scroll to bottom on new content ──────────────────────────────────────

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight
    }
  }, [messages.length, isWaiting])

  // ── Animate new messages ──────────────────────────────────────────────────

  useEffect(() => {
    if (messages.length === 0) return
    const timer = setTimeout(() => {
      setVisibleIds(prev => {
        const next = new Set(prev)
        messages.forEach(m => next.add(m.id))
        return next
      })
    }, 30)
    return () => clearTimeout(timer)
  }, [messages.length])

  // ── Helpers ───────────────────────────────────────────────────────────────

  const addMessage = useCallback((role: 'in' | 'out', text: string) => {
    setMessages(prev => [...prev, { id: makeId(), role, text, time: getTime() }])
  }, [])

  const applyResponse = useCallback((data: ChatResponse) => {
    const id = makeId()
    setMessages(prev => [...prev, { id, role: 'in', text: data.reply, time: getTime() }])
    setSignals(data.signals)
    setStep(data.step)
    setProgress(data.progress)
    setComplete(data.complete)
    setQuickReplies(data.quick_replies ?? [])

    if (data.complete) {
      setPortalLoading(true)
      const sid = sessionIdRef.current
      const attempt = (tries: number) => {
        fetch(`${API_URL}/founder/portal-link?session_id=${encodeURIComponent(sid)}`)
          .then(r => r.json())
          .then((d: { portal_url?: string }) => {
            if (d.portal_url) {
              setPortalUrl(d.portal_url)
              setPortalLoading(false)
            } else if (tries > 0) {
              setTimeout(() => attempt(tries - 1), 1500)
            } else {
              setPortalLoading(false)
            }
          })
          .catch(() => {
            if (tries > 0) setTimeout(() => attempt(tries - 1), 1500)
            else setPortalLoading(false)
          })
      }
      setTimeout(() => attempt(5), 1500)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── JD upload handler ─────────────────────────────────────────────────────

  const handleJdUpload = useCallback(async (file: File) => {
    if (isWaiting || !initDone) return

    setQuickReplies([])
    setMessages(prev => [...prev, {
      id: makeId(), role: 'out', text: '', time: getTime(),
      attachment: { name: file.name, size: file.size },
    }])
    setIsWaiting(true)

    try {
      const form = new FormData()
      form.append('session_id', sessionIdRef.current)
      form.append('file', file)
      if (authEmail) form.append('auth_email', authEmail)

      const res = await fetch(`${API_URL}/founder/upload-jd`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
      }
      const data: ChatResponse = await res.json()
      applyResponse(data)
    } catch (e) {
      addMessage('in', `Sorry, I couldn't read that file. ${(e as Error).message || 'Please try again.'}`)
    } finally {
      setIsWaiting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [isWaiting, initDone, addMessage, applyResponse])

  // ── Send handler ──────────────────────────────────────────────────────────

  const handleSend = useCallback(async (text?: string) => {
    const msg = (text ?? inputValue).trim()
    if (!msg || isWaiting || !initDone) return

    setInputValue('')
    setQuickReplies([])
    addMessage('out', msg)
    setIsWaiting(true)

    try {
      const res = await fetch(`${API_URL}/founder/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current, message: msg, auth_email: authEmail || undefined }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: ChatResponse = await res.json()
      applyResponse(data)
    } catch {
      addMessage('in', 'Something went wrong on our end. Please try again in a moment.')
    } finally {
      setIsWaiting(false)
    }
  }, [inputValue, isWaiting, initDone, addMessage, applyResponse])

  // ── Form submit (pre-chat gate) ───────────────────────────────────────────

  const handleFormSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!companyName.trim() || !companyUrl.trim()) return
    formDataRef.current = {
      founderName: founderName.trim(),
      companyName: companyName.trim(),
      companyUrl:  companyUrl.trim(),
      linkedinUrl: linkedinUrl.trim(),
    }
    setPhase('chat')
  }

  // ── Suppress unused-variable lint (signals/step/progress still collected) ─
  void signals; void step; void progress

  // ── Render ────────────────────────────────────────────────────────────────

  // Pre-chat company form
  if (phase === 'form') {
    return (
      <main className={styles.formPage}>
        <form className={styles.formCard} onSubmit={handleFormSubmit} noValidate>

          {/* Logo — identical visual to the sign-in page */}
          <div className={styles.formLogoRow}>
            <div className={styles.formLogoBox}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
                <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className={styles.formLogoName}>Mitra<span>.</span></span>
          </div>

          {/* Role badge */}
          <div className={styles.formRoleBadge}>
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1.5" y="4.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M5 4.5V4a3 3 0 0 1 6 0v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              <circle cx="8" cy="9" r="1.5" fill="currentColor"/>
            </svg>
            Signing in as founder
          </div>

          <div className={styles.formHeader}>
            <h1 className={styles.formTitle}>Tell us about your company</h1>
            <p className={styles.formSub}>
              Mitra researches your company before the chat begins — so we skip the basics and get straight to what you&apos;re hiring for.
            </p>
          </div>

          <div className={styles.formFields}>

            <div className={styles.formField}>
              <label className={styles.formLabel} htmlFor="ob-founder-name">Your name</label>
              <input
                id="ob-founder-name"
                className={styles.formInput}
                type="text"
                placeholder="e.g. Harshal Patil"
                value={founderName}
                onChange={e => setFounderName(e.target.value)}
                autoComplete="name"
              />
            </div>

            <div className={styles.formField}>
              <label className={styles.formLabel} htmlFor="ob-company-name">
                Company name
                <span className={styles.formRequired}>*</span>
              </label>
              <input
                id="ob-company-name"
                className={styles.formInput}
                type="text"
                placeholder="e.g. Mitra Labs"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                required
                autoComplete="organization"
              />
            </div>

            <div className={styles.formField}>
              <label className={styles.formLabel} htmlFor="ob-company-url">
                Company website
                <span className={styles.formRequired}>*</span>
              </label>
              <input
                id="ob-company-url"
                className={styles.formInput}
                type="url"
                placeholder="e.g. https://mitra.work"
                value={companyUrl}
                onChange={e => setCompanyUrl(e.target.value)}
                required
                autoComplete="url"
              />
            </div>

            <div className={styles.formField}>
              <label className={styles.formLabel} htmlFor="ob-linkedin-url">
                LinkedIn company page
                <span className={styles.formOptional}>optional</span>
              </label>
              <input
                id="ob-linkedin-url"
                className={styles.formInput}
                type="url"
                placeholder="e.g. https://linkedin.com/company/mitra-labs"
                value={linkedinUrl}
                onChange={e => setLinkedinUrl(e.target.value)}
                autoComplete="off"
              />
            </div>

          </div>

          <button
            type="submit"
            className={styles.formSubmit}
            disabled={!companyName.trim() || !companyUrl.trim()}
          >
            Start your brief →
          </button>

          <p className={styles.formHint}>
            Takes 2 minutes. No credit card needed.
          </p>

        </form>
      </main>
    )
  }

  // Chat phase — Clera-style single-column layout
  return (
    <div className={styles.app}>

      {/* ── TOPBAR ──────────────────────────────────────────────────────────── */}
      <div className={styles.topbar}>
        <div className={styles.logo}>
          <div className={styles.logoBox}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
              <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className={styles.logoName}>Mitra<span>.</span></span>
        </div>
        <div className={styles.topbarRight}>
          <a href="/founder/dashboard" className={styles.dashBtn}>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.3" stroke="currentColor" strokeWidth="1.3"/>
              <rect x="9"   y="1.5" width="5.5" height="5.5" rx="1.3" stroke="currentColor" strokeWidth="1.3"/>
              <rect x="1.5" y="9"   width="5.5" height="5.5" rx="1.3" stroke="currentColor" strokeWidth="1.3"/>
              <rect x="9"   y="9"   width="5.5" height="5.5" rx="1.3" stroke="currentColor" strokeWidth="1.3"/>
            </svg>
            Dashboard
          </a>
        </div>
      </div>

      {/* ── CHAT ────────────────────────────────────────────────────────────── */}
      <div className={styles.chatPanel}>

        {/* Messages */}
        <div className={styles.chatBody} ref={chatBodyRef}>

          {messages.map(msg => (
            <div
              key={msg.id}
              className={[
                styles.msg,
                msg.role === 'in' ? styles.in : styles.out,
                visibleIds.has(msg.id) ? styles.visible : '',
              ].join(' ')}
            >
              {msg.role === 'in' && (
                <div className={styles.msgAvatar} aria-hidden="true">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                    <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="2" strokeLinejoin="round"/>
                    <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="2" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
              <div className={styles.msgContent}>
                {msg.attachment ? (
                  <div className={styles.fileCard}>
                    <div className={`${styles.fileCardIcon} ${msg.attachment.name.toLowerCase().endsWith('.pdf') ? styles.filePdf : styles.fileDoc}`}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                        <polyline points="10 9 9 9 8 9"/>
                      </svg>
                    </div>
                    <div className={styles.fileCardInfo}>
                      <div className={styles.fileCardName}>{msg.attachment.name}</div>
                      <div className={styles.fileCardMeta}>
                        {msg.attachment.name.toLowerCase().endsWith('.pdf') ? 'PDF' : 'Word'} · {(msg.attachment.size / 1024).toFixed(0)} KB
                      </div>
                    </div>
                  </div>
                ) : (
                  <div
                    className={styles.msgBubble}
                    dangerouslySetInnerHTML={{
                      __html: msg.text
                        .replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
                        .replace(/\n/g, '<br>'),
                    }}
                  />
                )}
                <div className={styles.msgTime}>{msg.time}</div>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isWaiting && (
            <div className={`${styles.msg} ${styles.in} ${styles.visible}`}>
              <div className={styles.msgAvatar} aria-hidden="true">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="2" strokeLinejoin="round"/>
                  <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="2" strokeLinejoin="round"/>
                </svg>
              </div>
              <div className={styles.typing}>
                <span /><span /><span />
              </div>
            </div>
          )}

          {/* Quick replies */}
          {quickReplies.length > 0 && !isWaiting && (
            <div className={styles.suggestions}>
              {quickReplies.map(r => (
                <button key={r} className={styles.suggestion} onClick={() => handleSend(r)}>
                  {r}
                </button>
              ))}
            </div>
          )}

          {/* Portal CTA — shown inline when onboarding completes */}
          {complete && (
            <div className={styles.portalCard}>
              <div className={styles.portalCardCheck}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <div className={styles.portalCardBody}>
                <div className={styles.portalCardTitle}>Onboarding complete</div>
                <div className={styles.portalCardSub}>
                  Your brief is ready. Mitra will start matching candidates within 48 hours.
                </div>
                {portalLoading && (
                  <div className={styles.portalCardBtn} style={{ opacity: 0.5, cursor: 'not-allowed', pointerEvents: 'none' }}>
                    Setting up your portal…
                  </div>
                )}
                {portalUrl && !portalLoading && (
                  <a href={portalUrl} target="_blank" rel="noopener noreferrer" className={styles.portalCardBtn}>
                    Open candidate portal →
                  </a>
                )}
              </div>
            </div>
          )}

        </div>

        {/* Input bar — floating pill */}
        <div className={styles.inputBar}>
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            style={{ display: 'none' }}
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) handleJdUpload(f)
            }}
          />
          <div className={styles.inputPill}>
            <input
              className={styles.chatInput}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="Type a message…"
              autoComplete="off"
              disabled={isWaiting && !initDone}
            />
            <button
              className={styles.attachBtn}
              onClick={() => fileInputRef.current?.click()}
              disabled={isWaiting || !initDone}
              title="Upload JD (PDF or Word)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48" />
              </svg>
            </button>
            <button
              className={styles.sendBtn}
              onClick={() => handleSend()}
              disabled={isWaiting || !inputValue.trim()}
            >
              <svg viewBox="0 0 24 24" fill="white">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
        </div>

      </div>

    </div>
  )
}
