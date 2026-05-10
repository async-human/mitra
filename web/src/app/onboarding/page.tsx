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

const STEPS = ['role', 'brief', 'details', 'context', 'contact'] as const

const STEP_LABELS: Record<string, string> = {
  role: 'Role',
  brief: 'Brief',
  details: 'Details',
  context: 'Context',
  contact: 'Contact',
}

const SIGNAL_GROUPS: { name: string; keys: string[] }[] = [
  { name: 'Role',        keys: ['role_title', 'first_90_days'] },
  { name: 'Fit filters', keys: ['dealbreaker', 'culture_signal'] },
  { name: 'Practical',   keys: ['salary_range', 'location'] },
  { name: 'Company',     keys: ['company_name', 'why_join', 'stage'] },
  { name: 'Preferences', keys: ['intro_preference', 'contact_info'] },
]

// Keys covered by the predefined groups above — anything else is "extra"
const DEFINED_KEYS = new Set(SIGNAL_GROUPS.flatMap(g => g.keys))

const SIGNAL_LABELS: Record<string, string> = {
  role_title:       'Role title',
  first_90_days:    'First 90 days',
  dealbreaker:      'Dealbreaker',
  culture_signal:   'Culture signal',
  salary_range:     'Salary range',
  location:         'Location',
  company_name:     'Company',
  why_join:         'Why join',
  stage:            'Stage',
  intro_preference: 'Intro preference',
  contact_info:     'Contact info',
}

// Signal icon characters — using clean unicode symbols instead of OS-dependent emoji
const SIGNAL_ICONS: Record<string, string> = {
  role_title:       '✦',
  first_90_days:    '◎',
  dealbreaker:      '◈',
  culture_signal:   '⬡',
  salary_range:     '₹',
  location:         '◉',
  company_name:     '▣',
  why_join:         '◆',
  stage:            '▲',
  intro_preference: '◐',
  contact_info:     '@',
}

const ICON_COLORS = ['green', 'amber', 'teal', 'sand'] as const

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatExtraKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

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

  const [messages, setMessages]               = useState<Message[]>([])
  const [visibleIds, setVisibleIds]           = useState<Set<string>>(new Set())
  const [signals, setSignals]                 = useState<Signals>({})
  const [visibleSigKeys, setVisibleSigKeys]   = useState<Set<string>>(new Set())
  const [step, setStep]                       = useState<string>('role')
  const [progress, setProgress]               = useState(5)
  const [complete, setComplete]               = useState(false)
  const [quickReplies, setQuickReplies]       = useState<string[]>([])
  const [isWaiting, setIsWaiting]             = useState(false)
  const [inputValue, setInputValue]           = useState('')
  const [initDone, setInitDone]               = useState(false)
  const [portalUrl, setPortalUrl]             = useState<string>('')
  const [portalLoading, setPortalLoading]     = useState(false)

  const sessionIdRef  = useRef<string>('')
  const chatBodyRef   = useRef<HTMLDivElement>(null)
  const fileInputRef  = useRef<HTMLInputElement>(null)

  // ── Init: session ID + body overflow + greeting ──────────────────────────

  useEffect(() => {
    if (typeof window === 'undefined') return

    // Generate or restore session ID
    let sid = sessionStorage.getItem('mitra_founder_session') ?? ''
    if (!sid) {
      sid = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now()
      sessionStorage.setItem('mitra_founder_session', sid)
    }
    sessionIdRef.current = sid

    // Lock body scroll for the full-viewport layout
    document.body.style.overflow = 'hidden'

    // Fetch opening greeting
    setIsWaiting(true)
    fetch(`${API_URL}/founder/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, message: '', auth_email: authEmail || undefined }),
    })
      .then(r => r.json())
      .then((data: ChatResponse) => {
        applyResponse(data)
      })
      .catch(() => {
        addMessage('in', "Hi — I'm Mitra, a talent agent for funded startups in Bengaluru. *What role are you most urgently hiring for right now?*")
      })
      .finally(() => {
        setIsWaiting(false)
        setInitDone(true)
      })

    return () => { document.body.style.overflow = '' }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

  // ── Animate new signal rows ───────────────────────────────────────────────

  const sigKeyStr = Object.keys(signals).sort().join(',')
  useEffect(() => {
    if (!sigKeyStr) return
    const timer = setTimeout(() => {
      setVisibleSigKeys(prev => {
        const next = new Set(prev)
        sigKeyStr.split(',').filter(Boolean).forEach(k => next.add(k))
        return next
      })
    }, 120)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sigKeyStr])

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

    // When onboarding completes, fetch the portal URL (job may take a moment to persist)
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
      // Give the background task 1.5s to persist the job, then retry up to 5 times
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

  // ── Derived state ─────────────────────────────────────────────────────────

  const currentStepIdx = STEPS.indexOf(step as typeof STEPS[number])

  const getStepStatus = (s: string): 'done' | 'active' | 'todo' => {
    const idx = STEPS.indexOf(s as typeof STEPS[number])
    if (complete) return 'done'
    if (idx < currentStepIdx) return 'done'
    if (idx === currentStepIdx) return 'active'
    return 'todo'
  }

  const companyTitle = signals['company_name'] ?? 'New founder'
  const companySub   = signals['stage']
    ? `${signals['stage']} · Startup`
    : 'Conversation in progress…'

  const visibleGroups = SIGNAL_GROUPS.filter(g => g.keys.some(k => signals[k]))

  const extraKeys = Object.keys(signals).filter(k => !DEFINED_KEYS.has(k) && signals[k])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className={styles.app}>

      {/* ── TOPBAR ──────────────────────────────────────────────────────── */}
      <div className={styles.topbar}>
        <div className={styles.logo}>
          <div className={styles.logoBox}>
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="9" r="4" fill="white" />
              <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <span className={styles.logoName}>Mitra<span>.</span></span>
        </div>
        <div className={styles.topbarSep} />
        <span className={styles.topbarLabel}>Founder Onboarding</span>
        <div className={styles.topbarRight}>
          <a href="/founder/setup?list=1" className={styles.portalLink}>
            <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M10 3H13a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h3M8 1v8M5.5 6.5 8 9l2.5-2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            My portal
          </a>
          <div className={styles.statusPill}>
            <div className={styles.statusDot} />
            Agent live
          </div>
        </div>
      </div>

      {/* ── LEFT: WHATSAPP CHAT ──────────────────────────────────────────── */}
      <div className={styles.waPanel}>

        {/* Chat header */}
        <div className={styles.waHeader}>
          <div className={styles.waAv}>
            M
            <div className={styles.waAvDot} />
          </div>
          <div>
            <div className={styles.waHeaderName}>Mitra</div>
            <div className={styles.waHeaderStatus}>AI Talent Agent · Online</div>
          </div>
          <div className={styles.waHeaderIcons}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /><circle cx="5" cy="12" r="1" />
            </svg>
          </div>
        </div>

        {/* Messages */}
        <div className={styles.waBody} ref={chatBodyRef}>
          <div className={styles.waDate}>Today · {getTime()}</div>

          {messages.map(msg => (
            <div
              key={msg.id}
              className={[
                styles.msg,
                msg.role === 'in' ? styles.in : styles.out,
                visibleIds.has(msg.id) ? styles.visible : '',
              ].join(' ')}
            >
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
          ))}

          {isWaiting && (
            <div className={`${styles.typing} ${styles.show}`}>
              <span /><span /><span />
            </div>
          )}

          {/* Inline suggestion options */}
          {quickReplies.length > 0 && !isWaiting && (
            <div className={styles.suggestions}>
              {quickReplies.map(r => (
                <button
                  key={r}
                  className={styles.suggestion}
                  onClick={() => handleSend(r)}
                >
                  <span>{r}</span>
                  <svg className={styles.suggestionArrow} viewBox="0 0 16 16" fill="none">
                    <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Input bar */}
        <div className={styles.waInputBar}>
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

          {/* Attach button */}
          <button
            className={styles.waAttach}
            onClick={() => fileInputRef.current?.click()}
            disabled={isWaiting || !initDone}
            title="Upload JD (PDF or Word)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          <input
            className={styles.waInput}
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
            className={styles.waSend}
            onClick={() => handleSend()}
            disabled={isWaiting || !inputValue.trim()}
          >
            <svg viewBox="0 0 24 24" fill="white">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* ── RIGHT: PROFILE PANEL ─────────────────────────────────────────── */}
      <div className={styles.profilePanel}>

        {/* Header */}
        <div className={styles.profileHeader}>
          <div className={styles.phEyebrow}>Company brief</div>
          <div className={styles.phTitle}>{companyTitle}</div>
          <div className={styles.phSub}>{companySub}</div>
        </div>

        {/* Progress */}
        <div className={styles.progressWrap}>
          <div className={styles.progressLabel}>
            <span>Onboarding progress</span>
            <span>{progress}%</span>
          </div>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${progress}%` }} />
          </div>
        </div>

        {/* Steps */}
        <div className={styles.stepsRow}>
          {STEPS.map(s => (
            <div
              key={s}
              className={`${styles.stepPill} ${styles[getStepStatus(s)]}`}
            >
              {STEP_LABELS[s]}
            </div>
          ))}
        </div>

        {/* Signals */}
        <div className={styles.signalsScroll}>
          {visibleGroups.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.esIcon}>
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
                  <rect x="3" y="3" width="16" height="16" rx="4" stroke="#C07828" strokeWidth="1.5"/>
                  <path d="M7 8h8M7 11h5M7 14h6" stroke="#C07828" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <div className={styles.esTitle}>Brief building…</div>
              <div className={styles.esSub}>
                Your company profile fills in automatically as you chat with Mitra.
              </div>
              <div className={styles.esActivity}>
                <span /><span /><span />
              </div>
            </div>
          ) : (
            <>
              {visibleGroups.map((group, groupIdx) => (
                <div key={group.name} className={styles.signalGroup}>
                  <div className={`${styles.sgLabel} ${groupIdx === 0 ? styles.sgLabelFirst : ''}`}>
                    {group.name}
                  </div>
                  {group.keys.filter(k => signals[k]).map((k, i) => (
                    <div
                      key={k}
                      className={`${styles.signalRow} ${visibleSigKeys.has(k) ? styles.visible : ''}`}
                    >
                      <div className={`${styles.sigIcon} ${styles[ICON_COLORS[i % ICON_COLORS.length]]}`}>
                        {SIGNAL_ICONS[k] ?? '·'}
                      </div>
                      <div>
                        <div className={styles.sigKey}>{SIGNAL_LABELS[k] ?? k}</div>
                        <div className={styles.sigVal}>{String(signals[k])}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}

              {extraKeys.length > 0 && (
                <div className={styles.signalGroup}>
                  <div className={styles.sgLabel}>Additional</div>
                  {extraKeys.map((k, i) => (
                    <div
                      key={k}
                      className={`${styles.signalRow} ${visibleSigKeys.has(k) ? styles.visible : ''}`}
                    >
                      <div className={`${styles.sigIcon} ${styles[ICON_COLORS[i % ICON_COLORS.length]]}`}>
                        📌
                      </div>
                      <div>
                        <div className={styles.sigKey}>{formatExtraKey(k)}</div>
                        <div className={styles.sigVal}>{String(signals[k])}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className={styles.profileFooter}>
          <div className={`${styles.readyBanner} ${complete ? styles.show : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Ready to match — first intro within 48h
          </div>

          {complete && (
            <div className={styles.completeCard}>
              <div className={styles.ccTitle}>Onboarding complete</div>
              <div className={styles.ccSub}>
                Mitra has everything needed to start matching candidates.
                Your portal is ready — bookmark it to review every intro we send.
              </div>
              {portalLoading && (
                <div className={styles.ccBtn} style={{ opacity: 0.5, cursor: 'not-allowed', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.4)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.6s linear infinite', display: 'inline-block' }} />
                  Setting up your portal…
                </div>
              )}
              {portalUrl && !portalLoading && (
                <a
                  href={portalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.ccBtn}
                  style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  Open your candidate portal →
                </a>
              )}
            </div>
          )}
        </div>
      </div>

    </div>
  )
}
