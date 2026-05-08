"use client";

import type { ReactNode } from "react";
import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

function ArjunVis({ label }: { label: string }) {
  return (
    <svg viewBox="0 0 460 160" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }} role="img" aria-label={label}>
      <rect width="460" height="160" fill="#1B3A3A" />
      <text x="230" y="120" textAnchor="middle" fontFamily="Georgia,serif" fontSize="200" fontWeight="700" fill="rgba(27,94,90,0.15)" letterSpacing="-5">A</text>
      <line x1="40" y1="90" x2="420" y2="90" stroke="rgba(255,255,255,0.08)" strokeWidth="2" />
      <circle cx="80" cy="90" r="8" fill="rgba(27,94,90,0.4)" stroke="rgba(27,94,90,0.7)" strokeWidth="1.5" />
      <circle cx="200" cy="90" r="8" fill="rgba(192,122,40,0.4)" stroke="rgba(192,122,40,0.7)" strokeWidth="1.5" />
      <circle cx="320" cy="90" r="8" fill="rgba(26,122,74,0.4)" stroke="rgba(26,122,74,0.7)" strokeWidth="1.5" />
      <circle cx="400" cy="90" r="12" fill="rgba(26,122,74,0.3)" stroke="rgba(26,122,74,0.6)" strokeWidth="2" />
      <path d="M392 90 L398 96 L412 80" stroke="#4ADE80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <text x="80" y="114" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.35)" fontFamily="sans-serif">Chat</text>
      <text x="200" y="114" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.35)" fontFamily="sans-serif">Matched</text>
      <text x="320" y="114" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.35)" fontFamily="sans-serif">Intro sent</text>
      <text x="400" y="114" textAnchor="middle" fontSize="9" fill="rgba(74,222,128,0.7)" fontFamily="sans-serif">Hired!</text>
      <text x="240" y="50" textAnchor="middle" fontSize="13" fill="rgba(192,122,40,0.6)" fontFamily="Georgia,serif" fontStyle="italic">11 days · Setu · Series B</text>
    </svg>
  );
}

function RohitVis({ label }: { label: string }) {
  return (
    <svg viewBox="0 0 460 160" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }} role="img" aria-label={label}>
      <rect width="460" height="160" fill="#1C1917" />
      <rect x="40" y="30" width="160" height="70" rx="8" fill="rgba(220,60,60,0.08)" stroke="rgba(220,60,60,0.2)" strokeWidth="1" />
      <text x="120" y="56" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.35)" fontFamily="sans-serif">Initial offer</text>
      <text x="120" y="76" textAnchor="middle" fontSize="22" fill="rgba(220,80,80,0.7)" fontFamily="Georgia,serif" fontWeight="700">₹36L</text>
      <rect x="260" y="30" width="160" height="70" rx="8" fill="rgba(26,122,74,0.1)" stroke="rgba(26,122,74,0.3)" strokeWidth="1" />
      <text x="340" y="56" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.35)" fontFamily="sans-serif">After negotiation</text>
      <text x="340" y="76" textAnchor="middle" fontSize="22" fill="rgba(74,222,128,0.8)" fontFamily="Georgia,serif" fontWeight="700">₹42L</text>
      <path d="M205 65 L255 65" stroke="rgba(192,122,40,0.6)" strokeWidth="2" strokeLinecap="round" />
      <path d="M248 58 L258 65 L248 72" stroke="rgba(192,122,40,0.6)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <text x="230" y="62" textAnchor="middle" fontSize="9" fill="rgba(192,122,40,0.7)" fontFamily="sans-serif" fontWeight="600">+₹6L</text>
      <text x="230" y="130" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.2)" fontFamily="sans-serif">Mitra wrote the counter-offer message</text>
    </svg>
  );
}

function NehVis({ label }: { label: string }) {
  return (
    <svg viewBox="0 0 460 160" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }} role="img" aria-label={label}>
      <rect width="460" height="160" fill="#1A1220" />
      <text x="230" y="120" textAnchor="middle" fontFamily="Georgia,serif" fontSize="200" fontWeight="700" fill="rgba(107,79,187,0.08)" letterSpacing="-5">N</text>
      <rect x="30" y="40" width="180" height="80" rx="10" fill="rgba(220,60,60,0.08)" stroke="rgba(220,60,60,0.18)" strokeWidth="1" />
      <text x="120" y="68" textAnchor="middle" fontSize="11" fill="rgba(255,255,255,0.3)" fontFamily="sans-serif">4 months · 60 apps</text>
      <text x="120" y="90" textAnchor="middle" fontSize="15" fill="rgba(220,80,80,0.6)" fontFamily="Georgia,serif" fontStyle="italic">Zero callbacks</text>
      <path d="M215 80 L245 80" stroke="rgba(192,122,40,0.5)" strokeWidth="1.5" strokeDasharray="4,3" />
      <path d="M240 74 L248 80 L240 86" stroke="rgba(192,122,40,0.5)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <rect x="250" y="40" width="180" height="80" rx="10" fill="rgba(26,122,74,0.1)" stroke="rgba(26,122,74,0.25)" strokeWidth="1" />
      <text x="340" y="65" textAnchor="middle" fontSize="11" fill="rgba(255,255,255,0.3)" fontFamily="sans-serif">Mitra · 4 days</text>
      <text x="340" y="86" textAnchor="middle" fontSize="15" fill="rgba(74,222,128,0.75)" fontFamily="Georgia,serif" fontStyle="italic">Founder call booked</text>
      <text x="230" y="145" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.2)" fontFamily="sans-serif">Now Senior PM at CRED · Series E</text>
    </svg>
  );
}

function PriyaVis({ label }: { label: string }) {
  return (
    <svg viewBox="0 0 460 160" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }} role="img" aria-label={label}>
      <rect width="460" height="160" fill="#2A1F14" />
      <text x="230" y="120" textAnchor="middle" fontFamily="Georgia,serif" fontSize="200" fontWeight="700" fill="rgba(192,122,40,0.1)" letterSpacing="-5">P</text>
      <rect x="20" y="40" width="110" height="60" rx="8" fill="rgba(27,94,90,0.2)" stroke="rgba(27,94,90,0.3)" strokeWidth="1" />
      <rect x="28" y="50" width="60" height="5" rx="2" fill="rgba(255,255,255,0.35)" />
      <rect x="28" y="60" width="45" height="4" rx="2" fill="rgba(255,255,255,0.15)" />
      <rect x="28" y="72" width="80" height="16" rx="4" fill="rgba(27,94,90,0.2)" />
      <rect x="32" y="76" width="40" height="4" rx="2" fill="rgba(255,255,255,0.25)" />
      <path d="M135 70 L155 70" stroke="rgba(192,122,40,0.4)" strokeWidth="1.5" strokeDasharray="4,3" strokeLinecap="round" />
      <path d="M150 65 L158 70 L150 75" stroke="rgba(192,122,40,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <circle cx="220" cy="70" r="36" fill="rgba(192,122,40,0.06)" stroke="rgba(192,122,40,0.15)" strokeWidth="1" />
      <circle cx="220" cy="58" r="14" fill="#8B6B4A" opacity="0.7" />
      <ellipse cx="220" cy="83" rx="20" ry="14" fill="#2A1F14" opacity="0.7" />
      <path d="M275 70 L295 70" stroke="rgba(192,122,40,0.4)" strokeWidth="1.5" strokeDasharray="4,3" strokeLinecap="round" />
      <path d="M290 65 L298 70 L290 75" stroke="rgba(192,122,40,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <rect x="310" y="40" width="120" height="60" rx="8" fill="rgba(192,122,40,0.12)" stroke="rgba(192,122,40,0.25)" strokeWidth="1" />
      <rect x="318" y="50" width="70" height="5" rx="2" fill="rgba(255,255,255,0.4)" />
      <rect x="318" y="60" width="55" height="4" rx="2" fill="rgba(255,255,255,0.2)" />
      <rect x="358" y="74" width="60" height="16" rx="4" fill="rgba(192,122,40,0.3)" />
      <rect x="362" y="78" width="36" height="4" rx="2" fill="rgba(192,122,40,0.8)" />
      <text x="220" y="130" textAnchor="middle" fontSize="10" fill="rgba(192,122,40,0.5)" fontFamily="sans-serif">3–5 curated introductions per week</text>
    </svg>
  );
}

function VikVis({ label }: { label: string }) {
  return (
    <svg viewBox="0 0 460 160" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }} role="img" aria-label={label}>
      <rect width="460" height="160" fill="#0F1F1A" />
      <rect x="30" y="35" width="400" height="30" rx="6" fill="rgba(220,60,60,0.07)" stroke="rgba(220,60,60,0.15)" strokeWidth="1" />
      <text x="40" y="55" fontSize="10" fill="rgba(255,255,255,0.25)" fontFamily="sans-serif">Naukri inbox: 187 applicants</text>
      <rect x="30" y="75" width="180" height="30" rx="6" fill="rgba(220,60,60,0.05)" stroke="rgba(220,60,60,0.12)" strokeWidth="1" />
      <text x="40" y="95" fontSize="10" fill="rgba(255,255,255,0.2)" fontFamily="sans-serif">Agency: 8 CVs, no context</text>
      <rect x="250" y="75" width="180" height="30" rx="6" fill="rgba(26,122,74,0.12)" stroke="rgba(26,122,74,0.3)" strokeWidth="1" />
      <text x="260" y="89" fontSize="10" fill="rgba(74,222,128,0.7)" fontFamily="sans-serif">Mitra: 4 pre-qualified intros</text>
      <text x="260" y="102" fontSize="9" fill="rgba(255,255,255,0.3)" fontFamily="sans-serif">with full context notes</text>
      <text x="230" y="140" textAnchor="middle" fontSize="10" fill="rgba(192,122,40,0.45)" fontFamily="Georgia,serif" fontStyle="italic">2 hires in 6 weeks · Hyperface · Series A</text>
    </svg>
  );
}

function AnkVis({ label }: { label: string }) {
  return (
    <svg viewBox="0 0 460 160" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }} role="img" aria-label={label}>
      <rect width="460" height="160" fill="#141820" />
      <rect x="50" y="30" width="360" height="100" rx="12" fill="rgba(27,94,90,0.08)" stroke="rgba(27,94,90,0.2)" strokeWidth="1" />
      <text x="100" y="60" fontSize="11" fill="rgba(255,255,255,0.3)" fontFamily="sans-serif">Before Mitra:</text>
      <text x="100" y="80" fontSize="13" fill="rgba(220,80,80,0.6)" fontFamily="Georgia,serif" fontStyle="italic">3 months, 1 interview</text>
      <text x="280" y="60" fontSize="11" fill="rgba(255,255,255,0.3)" fontFamily="sans-serif">With Mitra:</text>
      <text x="280" y="80" fontSize="13" fill="rgba(74,222,128,0.75)" fontFamily="Georgia,serif" fontStyle="italic">3 offers in 18 days</text>
      <line x1="240" y1="45" x2="240" y2="115" stroke="rgba(192,122,40,0.2)" strokeWidth="1" strokeDasharray="4,3" />
      <text x="230" y="140" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.18)" fontFamily="sans-serif">Staff Data Engineer · now at Razorpay</text>
    </svg>
  );
}

type Story = { text: string; name: string; role: string; city: string; initial: string; avatarBg: string; vis: ReactNode; feat?: boolean; delay?: 1 | 2 | 3 | 4 };

const CANDIDATE_STORIES: Story[] = [
  {
    text: "I had applied to 60 companies over 4 months. Ghosted by most. Mitra had me talking to a Series B founder within 72 hours of our first WhatsApp conversation. The introduction they sent was better than anything I could have written about myself. Offer accepted in 11 days.",
    name: "Arjun Krishnamurthy", role: "Staff Engineer · now at Setu", city: "Bengaluru",
    initial: "A", avatarBg: "linear-gradient(135deg,#1B5E5A,#237870)",
    vis: <ArjunVis label="Timeline: WhatsApp chat, matched, introduction sent, hired at Setu in 11 days." />,
    feat: true, delay: 1,
  },
  {
    text: "Mitra told me my offer was ₹8L below market and wrote the counter-offer message for me. I walked away with ₹6L more than the original number. The negotiation coaching alone was worth the entire experience.",
    name: "Rohit Agarwal", role: "Product Lead · now at Finbox", city: "Hyderabad",
    initial: "R", avatarBg: "linear-gradient(135deg,#6B4FBB,#8B6FDB)",
    vis: <RohitVis label="Salary comparison: lower initial offer versus higher offer after negotiation support from Mitra." />,
    delay: 2,
  },
  {
    text: "4 months of cold applications and one response. Then I tried Mitra. A founder called me the same week. 18 days later I had 3 competing offers and Mitra helped me pick the right one — not just the highest salary.",
    name: "Neha Sharma", role: "Senior PM · now at CRED", city: "Mumbai",
    initial: "N", avatarBg: "linear-gradient(135deg,#8B2252,#B03070)",
    vis: <NehVis label="Before Mitra: 4 months, zero callbacks. After Mitra: founder call booked in 4 days." />,
    delay: 3,
  },
];

const FOUNDER_STORIES: Story[] = [
  {
    text: "As a founder I was drowning in Naukri CVs. Mitra sends me 3–4 candidates a week who are genuinely relevant. Two of my best hires this year came through them. The context notes on every candidate are invaluable.",
    name: "Priya Subramaniam", role: "Co-founder, Hyperface", city: "Founder",
    initial: "P", avatarBg: "linear-gradient(135deg,#C07A28,#A06020)",
    vis: <PriyaVis label="Founder view: screened candidates on the left, Mitra in the center, curated introductions for Hyperface on the right." />,
    feat: true, delay: 1,
  },
  {
    text: "I wasted 3 months with a recruiter agency — they charged 18% and sent CVs we could have found ourselves. Mitra had us in conversations with 4 pre-qualified candidates in the first week. Hired in 6 weeks, paid 8%.",
    name: "Vikram Nair", role: "CTO, Finbox", city: "Founder",
    initial: "V", avatarBg: "linear-gradient(135deg,#1B5E5A,#237870)",
    vis: <VikVis label="Comparison: recruiter agency vs Mitra. Mitra delivered 4 pre-qualified intros vs agency 8 CVs with no context." />,
    delay: 2,
  },
  {
    text: "What I love most is the context. Every intro comes with salary expectation, why they want to join us specifically, and what they won't compromise on. We go straight to the real conversation instead of spending 30 minutes on 'tell me about yourself'.",
    name: "Ankit Mehta", role: "Founder, Setu", city: "Founder",
    initial: "A", avatarBg: "linear-gradient(135deg,#2A4A8A,#3A6ACA)",
    vis: <AnkVis label="Staff Data Engineer hired via Mitra at Razorpay — 3 offers in 18 days." />,
    delay: 3,
  },
];

export function Stories() {
  const { audience } = useAudience();
  const stories = audience === "candidate" ? CANDIDATE_STORIES : FOUNDER_STORIES;
  const heading = audience === "candidate"
    ? <><>People whose careers changed<br />through one <em>introduction.</em></></>
    : <><>Founders who stopped drowning in CVs<br />and started <em>hiring on instinct.</em></></>;

  return (
    <section className="stories-sec" id="stories">
      <Reveal>
        <div className="eyebrow">Real stories</div>
        <h2 className="sec-title">{heading}</h2>
      </Reveal>
      <div className="stories-grid">
        {stories.map((s) => (
          <Reveal key={s.name} className={`story-card${s.feat ? " feat" : ""}`} delay={s.delay}>
            <div className="story-vis">{s.vis}</div>
            <div className="story-body">
              <div className="story-stars" aria-label="5 out of 5 stars">★★★★★</div>
              <div className="story-text">&ldquo;{s.text}&rdquo;</div>
              <div className="story-person">
                <div className="sp-av2" style={{ background: s.avatarBg }} aria-hidden="true">{s.initial}</div>
                <div>
                  <div className="sp-nm">{s.name}</div>
                  <div className="sp-rl">{s.role}</div>
                </div>
                <div className="sp-co">{s.city}</div>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal delay={4}>
        <p className="stories-disclaimer">
          Stories and visuals are illustrative; timelines and outcomes vary by role, company, and market.
        </p>
      </Reveal>
    </section>
  );
}
