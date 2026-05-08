import type { ReactNode } from "react";
import { Reveal } from "./Reveal";

function ArjunVis({ label }: { label: string }) {
  return (
    <svg
      viewBox="0 0 460 160"
      xmlns="http://www.w3.org/2000/svg"
      style={{ width: "100%", height: "100%" }}
      role="img"
      aria-label={label}
    >
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

function PriyaVis({ label }: { label: string }) {
  return (
    <svg
      viewBox="0 0 460 160"
      xmlns="http://www.w3.org/2000/svg"
      style={{ width: "100%", height: "100%" }}
      role="img"
      aria-label={label}
    >
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

function RohitVis({ label }: { label: string }) {
  return (
    <svg
      viewBox="0 0 460 160"
      xmlns="http://www.w3.org/2000/svg"
      style={{ width: "100%", height: "100%" }}
      role="img"
      aria-label={label}
    >
      <rect width="460" height="160" fill="#1C1917" />
      <text x="230" y="120" textAnchor="middle" fontFamily="Georgia,serif" fontSize="200" fontWeight="700" fill="rgba(255,255,255,0.03)" letterSpacing="-5">R</text>
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

type Story = {
  text: string;
  name: string;
  role: string;
  city: string;
  initial: string;
  avatarBg: string;
  vis: ReactNode;
  feat?: boolean;
  delay?: 1 | 2 | 3 | 4;
};

const STORIES: Story[] = [
  {
    text: "I had applied to 60 companies over 4 months. Ghosted by most. Mitra had me talking to a Series B founder within 72 hours of our first WhatsApp conversation. The introduction they sent was better than anything I could have written about myself. Offer accepted in 11 days.",
    name: "Arjun Krishnamurthy",
    role: "Staff Engineer · now at Setu",
    city: "India",
    initial: "A",
    avatarBg: "linear-gradient(135deg,#1B5E5A,#237870)",
    vis: (
      <ArjunVis label="Timeline: WhatsApp chat, matched, introduction sent, hired at Setu in about eleven days." />
    ),
    feat: true,
    delay: 1,
  },
  {
    text: "As a founder I was drowning in Naukri CVs. Mitra sends me 3–4 candidates a week who are genuinely relevant. Two of my best hires this year came through them. The context notes on every candidate are invaluable.",
    name: "Priya Subramaniam",
    role: "Co-founder, Hyperface",
    city: "Founder",
    initial: "P",
    avatarBg: "linear-gradient(135deg,#C07A28,#A06020)",
    vis: (
      <PriyaVis label="Founder view: screened candidates on the left, Mitra persona in the center, curated introductions for Hyperface on the right." />
    ),
    delay: 2,
  },
  {
    text: "Mitra told me my offer was ₹8L below market and wrote the counter-offer message for me. I walked away with ₹6L more than the original number. The negotiation coaching alone was worth the entire experience.",
    name: "Rohit Agarwal",
    role: "Product Lead · now at Finbox",
    city: "Hyderabad",
    initial: "R",
    avatarBg: "linear-gradient(135deg,#6B4FBB,#8B6FDB)",
    vis: (
      <RohitVis label="Salary comparison: lower initial offer versus higher offer after negotiation support from Mitra." />
    ),
    delay: 3,
  },
];

export function Stories() {
  return (
    <section className="stories-sec" id="stories">
      <Reveal>
        <div className="eyebrow">Real stories</div>
        <h2 className="sec-title">
          People whose careers changed
          <br />
          through one <em>introduction.</em>
        </h2>
      </Reveal>
      <div className="stories-grid">
        {STORIES.map((s) => (
          <Reveal
            key={s.name}
            className={`story-card${s.feat ? " feat" : ""}`}
            delay={s.delay}
          >
            <div className="story-vis">{s.vis}</div>
            <div className="story-body">
              <div className="story-stars" aria-label="5 out of 5 stars">★★★★★</div>
              <div className="story-text">&ldquo;{s.text}&rdquo;</div>
              <div className="story-person">
                <div
                  className="sp-av2"
                  style={{ background: s.avatarBg }}
                  aria-hidden="true"
                >
                  {s.initial}
                </div>
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
          Stories and visuals are illustrative; timelines and outcomes vary by
          role, company, and market. Numeric claims elsewhere on the page are not
          audited financials — they reflect how we operate today.
        </p>
      </Reveal>
    </section>
  );
}
