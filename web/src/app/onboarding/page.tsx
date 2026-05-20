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

type JdPreview = {
  // Header
  role_title:  string | null
  company:     string | null
  // Tag row
  location:    string | null
  work_type:   string | null
  salary:      string | null
  experience:  string | null
  industry:    string | null
  stage:       string | null
  skills_tags: string[]
  // Body sections
  about_role:               string | null
  responsibilities:         string[]
  required_skills:          string[]
  preferred_qualifications: string[]
  // Company
  company_description: string | null
  company_size:        string | null
  company_website:     string | null
  company_linkedin:    string | null
  // Gate
  missing_brief:   string[]
  missing_contact: string[]
}

type ChatResponse = {
  reply: string
  signals: Signals
  step: string
  progress: number
  complete: boolean
  quick_replies: string[]
  preview?: JdPreview | null
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
  const [phase, setPhase]             = useState<'form' | 'upload' | 'processing' | 'preview' | 'chat'>('form')
  const [founderName, setFounderName] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [companyUrl, setCompanyUrl]   = useState('')
  const [linkedinUrl, setLinkedinUrl] = useState('')

  // Upload phase state
  const [uploadDragOver, setUploadDragOver] = useState(false)
  const [uploadError, setUploadError]       = useState('')
  const [uploadFileName, setUploadFileName] = useState('')

  // Processing phase state (animated steps + pending API response)
  const [processingStep, setProcessingStep]     = useState(0)   // 0-3 active step index
  const [processingDone, setProcessingDone]     = useState(false)
  const pendingResponseRef = useRef<ChatResponse | null>(null)   // API result while animation plays

  // Preview phase state
  const [previewData, setPreviewData] = useState<JdPreview | null>(null)

  const sessionIdRef      = useRef<string>('')
  const chatBodyRef       = useRef<HTMLDivElement>(null)
  const fileInputRef      = useRef<HTMLInputElement>(null)
  const uploadFileInputRef = useRef<HTMLInputElement>(null)
  const skipChatInitRef   = useRef(false)
  // Captures form values at the moment the chat phase starts (avoids stale closure)
  const formDataRef  = useRef<{ founderName: string; companyName: string; companyUrl: string; linkedinUrl: string } | null>(null)

  // ── Pre-fill founder name from auth session ──────────────────────────────

  useEffect(() => {
    if (authSession?.user?.name) {
      setFounderName(prev => prev || authSession.user!.name!)
    }
  }, [authSession?.user?.name])

  // ── Transition processing → preview once animation done + API returned ───

  useEffect(() => {
    if (!processingDone) return
    const data = pendingResponseRef.current
    if (!data) return   // API hasn't returned yet — it will call setPhase itself
    setSignals(data.signals)
    setStep(data.step)
    setProgress(data.progress)
    setComplete(data.complete)
    setPreviewData(data.preview ?? null)
    setPhase('preview')
  }, [processingDone])

  // ── Show upload UI when ?upload=1 ────────────────────────────────────────

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('upload') !== '1') return
    let sid = sessionStorage.getItem('mitra_founder_session') ?? ''
    if (!sid) {
      sid = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now()
      sessionStorage.setItem('mitra_founder_session', sid)
    }
    sessionIdRef.current = sid
    setPhase('upload')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Upload phase: kick off processing animation + API call in parallel ───

  const handleUploadPhaseFile = useCallback(async (file: File) => {
    setUploadError('')
    setUploadFileName(file.name)
    setProcessingStep(0)
    setProcessingDone(false)
    pendingResponseRef.current = null
    setPhase('processing')

    // Step animation — advances every 900ms, completes after step 3 (≥3.6s total)
    let stepVal = 0
    const stepTimer = setInterval(() => {
      stepVal++
      if (stepVal >= 4) {
        clearInterval(stepTimer)
        setProcessingStep(4)          // all steps done
        setProcessingDone(true)
      } else {
        setProcessingStep(stepVal)
      }
    }, 900)

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
        clearInterval(stepTimer)
        const err = await res.json().catch(() => ({}))
        throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`)
      }
      const data: ChatResponse = await res.json()
      pendingResponseRef.current = data

      // If animation already finished, go straight to preview; else it will
      // pick up pendingResponseRef when processingDone becomes true (see effect below)
      if (stepVal >= 4) {
        setSignals(data.signals)
        setStep(data.step)
        setProgress(data.progress)
        setComplete(data.complete)
        setPreviewData(data.preview ?? null)
        setPhase('preview')
      }
    } catch (e) {
      clearInterval(stepTimer)
      setUploadError((e as Error).message || 'Upload failed. Please try again.')
      setUploadFileName('')
      setPhase('upload')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authEmail])

  // ── Preview confirmed → go to chat to collect missing fields ────────────

  const handleConfirmPreview = useCallback(() => {
    const data = pendingResponseRef.current
    if (!data) return
    const fileId  = makeId()
    const replyId = makeId()
    setMessages([
      { id: fileId,  role: 'out', text: '', time: getTime(), attachment: { name: uploadFileName, size: 0 } },
      { id: replyId, role: 'in',  text: data.reply, time: getTime() },
    ])
    setQuickReplies(data.quick_replies ?? [])
    setInitDone(true)
    formDataRef.current = { founderName: '', companyName: '', companyUrl: '', linkedinUrl: '' }
    skipChatInitRef.current = true
    setPhase('chat')
  }, [uploadFileName])

  // ── Init: session ID + body overflow + greeting (fires when chat phase starts) ──

  useEffect(() => {
    if (phase !== 'chat') return
    if (typeof window === 'undefined') return

    // Came from upload flow — messages already set, skip API init
    if (skipChatInitRef.current) {
      document.body.style.overflow = 'hidden'
      return () => { document.body.style.overflow = '' }
    }

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

  // ── Upload phase ─────────────────────────────────────────────────────────

  if (phase === 'upload') {
    return (
      <main className={styles.formPage}>
        <div className={styles.formCard}>

          <div className={styles.formLogoRow}>
            <div className={styles.formLogoBox}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
                <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className={styles.formLogoName}>Mitra<span>.</span></span>
          </div>

          <div className={styles.formHeader}>
            <h1 className={styles.formTitle}>Upload your job description</h1>
            <p className={styles.formSub}>
              Drop a PDF or Word file and Mitra extracts everything automatically — role, salary, must-haves, culture.
            </p>
          </div>

          {/* Hidden file input */}
          <input
            ref={uploadFileInputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            style={{ display: 'none' }}
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) handleUploadPhaseFile(f)
            }}
          />

          {/* Drop zone */}
          <div
            className={[
              styles.uploadZone,
              uploadDragOver ? styles.uploadZoneDrag : '',
            ].join(' ')}
            onClick={() => uploadFileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setUploadDragOver(true) }}
            onDragLeave={() => setUploadDragOver(false)}
            onDrop={e => {
              e.preventDefault()
              setUploadDragOver(false)
              const f = e.dataTransfer.files?.[0]
              if (f) handleUploadPhaseFile(f)
            }}
          >
            <div className={styles.uploadZoneIcon} aria-hidden="true">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="12" y1="11" x2="12" y2="17"/>
                <polyline points="9 14 12 11 15 14"/>
              </svg>
            </div>
            <p className={styles.uploadZoneTitle}>
              {uploadDragOver ? 'Drop to upload' : 'Drop your JD here'}
            </p>
            <p className={styles.uploadZoneSub}>or <span className={styles.uploadZoneBrowse}>click to browse</span></p>
          </div>

          {uploadError && (
            <div className={styles.uploadError}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {uploadError}
            </div>
          )}

          <p className={styles.uploadFormats}>PDF · DOCX · DOC &nbsp;·&nbsp; Max 10 MB</p>

          <div className={styles.uploadDivider}><span>or</span></div>

          <a href="/onboarding" className={styles.uploadAltLink}>
            Start with AI brief instead →
          </a>

        </div>
      </main>
    )
  }

  // ── Processing phase ──────────────────────────────────────────────────────

  const processingSteps = [
    'Reading your document',
    'Extracting role details',
    'Researching the company',
    'Building your brief',
  ]

  if (phase === 'processing') {
    return (
      <main className={styles.formPage}>
        <div className={styles.processingCard}>

          <div className={styles.formLogoRow}>
            <div className={styles.formLogoBox}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 19V9l7-3 7 3v10l-7 3-7-3Z" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
                <path d="M12 6v14M5 9l7 3 7-3" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className={styles.formLogoName}>Mitra<span>.</span></span>
          </div>

          <div className={styles.processingFile}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            {uploadFileName}
          </div>

          <h2 className={styles.processingTitle}>Processing your JD</h2>
          <p className={styles.processingSub}>Takes just a few seconds…</p>

          <div className={styles.processingSteps}>
            {processingSteps.map((label, i) => {
              const done   = processingStep > i
              const active = processingStep === i
              return (
                <div
                  key={i}
                  className={[
                    styles.processingStep,
                    done   ? styles.processingStepDone   : '',
                    active ? styles.processingStepActive : '',
                  ].join(' ')}
                >
                  <div className={styles.processingStepIcon}>
                    {done ? (
                      <svg width="10" height="10" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <polyline points="2 8 6 12 14 4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    ) : active ? (
                      <div className={styles.processingPulse} aria-hidden="true" />
                    ) : (
                      <div className={styles.processingDot} aria-hidden="true" />
                    )}
                  </div>
                  <span className={styles.processingStepLabel}>{label}</span>
                </div>
              )
            })}
          </div>

        </div>
      </main>
    )
  }

  // ── Preview phase ─────────────────────────────────────────────────────────

  if (phase === 'preview') {
    const p = previewData
    const missingAll = [...(p?.missing_brief ?? []), ...(p?.missing_contact ?? [])]

    // Company initials for avatar
    const initials = (() => {
      const s = p?.company || p?.role_title || '?'
      const words = s.trim().split(/\s+/)
      return words.length >= 2
        ? (words[0][0] + words[1][0]).toUpperCase()
        : s.slice(0, 2).toUpperCase()
    })()

    const tagItems = [
      p?.location  && { icon: 'pin',      text: p.location },
      p?.work_type && { icon: null,        text: p.work_type },
      p?.salary    && { icon: null,        text: p.salary },
      p?.experience && { icon: null,       text: p.experience + ' exp' },
      p?.industry  && { icon: null,        text: p.industry },
    ].filter(Boolean) as { icon: string | null; text: string }[]

    return (
      <main className={styles.previewPage}>
        <div className={styles.previewWrap}>

          {/* ── Role header card ──────────────────────────────────────── */}
          <div className={styles.pvRoleCard}>
            <div className={styles.pvAvatar}>{initials}</div>
            <div className={styles.pvRoleInfo}>
              <h1 className={styles.pvRoleTitle}>{p?.role_title ?? 'Your role'}</h1>
              <div className={styles.pvCompany}>{p?.company}</div>
            </div>
          </div>

          {/* ── Tag row ───────────────────────────────────────────────── */}
          {(tagItems.length > 0 || (p?.skills_tags?.length ?? 0) > 0) && (
            <div className={styles.pvTagRow}>
              {tagItems.map((t, i) => (
                <span key={i} className={styles.pvMetaTag}>
                  {t.icon === 'pin' && (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                    </svg>
                  )}
                  {t.text}
                </span>
              ))}
              {p?.skills_tags?.map(tag => (
                <span key={tag} className={styles.pvSkillTag}>{tag}</span>
              ))}
            </div>
          )}

          {/* ── About the Role ────────────────────────────────────────── */}
          {p?.about_role && (
            <div className={styles.pvSection}>
              <h2 className={styles.pvSectionTitle}>About the Role</h2>
              <p className={styles.pvSectionText}>{p.about_role}</p>
            </div>
          )}

          {/* ── Key Responsibilities ──────────────────────────────────── */}
          {(p?.responsibilities?.length ?? 0) > 0 && (
            <div className={styles.pvSection}>
              <h2 className={styles.pvSectionTitle}>Key Responsibilities</h2>
              <ul className={styles.pvBulletList}>
                {p!.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* ── Required Skills ───────────────────────────────────────── */}
          {(p?.required_skills?.length ?? 0) > 0 && (
            <div className={styles.pvSection}>
              <h2 className={styles.pvSectionTitle}>Required Skills &amp; Experience</h2>
              <ul className={styles.pvBulletList}>
                {p!.required_skills.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* ── Preferred Qualifications ──────────────────────────────── */}
          {(p?.preferred_qualifications?.length ?? 0) > 0 && (
            <div className={styles.pvSection}>
              <h2 className={styles.pvSectionTitle}>Preferred Qualifications</h2>
              <ul className={`${styles.pvBulletList} ${styles.pvBulletMuted}`}>
                {p!.preferred_qualifications.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* ── About Company ─────────────────────────────────────────── */}
          {(p?.company_description || p?.company_size) && (
            <div className={styles.pvSection}>
              <h2 className={styles.pvSectionTitle}>About {p?.company}</h2>
              {p?.company_description && (
                <p className={styles.pvSectionText}>{p.company_description}</p>
              )}
              {p?.company_size && (
                <div className={styles.pvCompanySize}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                  {p.company_size}
                </div>
              )}
            </div>
          )}

          {/* ── Company Links ─────────────────────────────────────────── */}
          {(p?.company_website || p?.company_linkedin) && (
            <div className={styles.pvSection}>
              <h2 className={styles.pvSectionTitle}>Company Links</h2>
              <div className={styles.pvLinkRow}>
                {p?.company_website && (
                  <a href={p.company_website} target="_blank" rel="noopener noreferrer" className={styles.pvLinkBtn}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                    </svg>
                    Website
                  </a>
                )}
                {p?.company_linkedin && (
                  <a href={p.company_linkedin} target="_blank" rel="noopener noreferrer" className={styles.pvLinkBtn}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>
                      <rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>
                    </svg>
                    LinkedIn
                  </a>
                )}
              </div>
            </div>
          )}

          {/* ── Missing fields ────────────────────────────────────────── */}
          {missingAll.length > 0 && (
            <div className={styles.pvMissing}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <div>
                <div className={styles.pvMissingTitle}>
                  {missingAll.length === 1 ? '1 detail still needed' : `${missingAll.length} details still needed`}
                </div>
                <ul className={styles.pvMissingList}>
                  {missingAll.map(m => <li key={m}>{m}</li>)}
                </ul>
              </div>
            </div>
          )}

          {/* ── CTAs ─────────────────────────────────────────────────── */}
          <div className={styles.pvActions}>
            <button className={styles.pvPostBtn} onClick={handleConfirmPreview}>
              {missingAll.length > 0 ? 'Looks right — fill in the rest →' : 'Post this role →'}
            </button>
            <button className={styles.pvEditBtn} onClick={handleConfirmPreview}>
              Edit details via chat
            </button>
          </div>

        </div>
      </main>
    )
  }

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
