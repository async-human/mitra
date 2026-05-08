"use client";

import { Reveal } from "./Reveal";
import { useAudience } from "./AudienceContext";

type Story = {
  stat: string;
  statLabel: string;
  accentColor: string;
  text: string;
  name: string;
  role: string;
  city: string;
  initial: string;
  avatarBg: string;
  delay?: 1 | 2 | 3 | 4;
};

const CANDIDATE_STORIES: Story[] = [
  {
    stat: "11 days",
    statLabel: "from WhatsApp chat to offer accepted",
    accentColor: "#1B5E5A",
    text: "I had applied to 60 companies over 4 months. Ghosted by most. Mitra had me talking to a Series B founder within 72 hours. The introduction they sent was better than anything I could have written about myself. Offer accepted in 11 days.",
    name: "Arjun Krishnamurthy",
    role: "Staff Engineer · now at Setu",
    city: "Bengaluru",
    initial: "A",
    avatarBg: "linear-gradient(135deg,#1B5E5A,#237870)",
    delay: 1,
  },
  {
    stat: "+₹6L",
    statLabel: "above initial offer, negotiated",
    accentColor: "#6B4FBB",
    text: "Mitra told me my offer was ₹8L below market and wrote the counter-offer message for me. The negotiation coaching alone was worth the entire experience.",
    name: "Rohit Agarwal",
    role: "Product Lead · now at Finbox",
    city: "Hyderabad",
    initial: "R",
    avatarBg: "linear-gradient(135deg,#6B4FBB,#8B6FDB)",
    delay: 2,
  },
  {
    stat: "3 offers",
    statLabel: "in 18 days, founder intros only",
    accentColor: "#8B2252",
    text: "4 months of cold applications and one response. Then I tried Mitra. A founder called me the same week. Mitra helped me pick the right offer — not just the highest salary.",
    name: "Neha Sharma",
    role: "Senior PM · now at CRED",
    city: "Mumbai",
    initial: "N",
    avatarBg: "linear-gradient(135deg,#8B2252,#B03070)",
    delay: 3,
  },
];

const FOUNDER_STORIES: Story[] = [
  {
    stat: "2 best hires",
    statLabel: "this year — both through Mitra",
    accentColor: "#C07A28",
    text: "I was drowning in Naukri CVs. Mitra sends me 3–4 candidates a week who are genuinely relevant. The context notes on every candidate are invaluable — I know why they want to join before we even speak.",
    name: "Priya Subramaniam",
    role: "Co-founder, Hyperface",
    city: "Founder",
    initial: "P",
    avatarBg: "linear-gradient(135deg,#C07A28,#A06020)",
    delay: 1,
  },
  {
    stat: "8%",
    statLabel: "vs 18% agency — hired in 6 weeks",
    accentColor: "#1B5E5A",
    text: "We wasted 3 months with a recruiter agency — charged 18%, sent CVs we could have found ourselves. Mitra had us in conversations with 4 pre-qualified candidates in the first week.",
    name: "Vikram Nair",
    role: "CTO, Finbox",
    city: "Founder",
    initial: "V",
    avatarBg: "linear-gradient(135deg,#1B5E5A,#237870)",
    delay: 2,
  },
  {
    stat: "4 days",
    statLabel: "to first qualified introduction",
    accentColor: "#2A4A8A",
    text: "Every intro comes with salary expectation, why they want to join us specifically, and what they won't compromise on. We go straight to the real conversation — no 'tell me about yourself'.",
    name: "Ankit Mehta",
    role: "Founder, Setu",
    city: "Founder",
    initial: "A",
    avatarBg: "linear-gradient(135deg,#2A4A8A,#3A6ACA)",
    delay: 3,
  },
];

function StoryCard({ s, featured = false }: { s: Story; featured?: boolean }) {
  return (
    <Reveal className={`story-card${featured ? " story-card--feat" : ""}`} delay={s.delay}>
      <div className="story-stat-block" style={{ background: s.accentColor }}>
        <div className="story-stat-num">{s.stat}</div>
        <div className="story-stat-lbl">{s.statLabel}</div>
      </div>
      <div className="story-body">
        <div className="story-stars" aria-label="5 out of 5 stars">★★★★★</div>
        <p className="story-text">&ldquo;{s.text}&rdquo;</p>
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
  );
}

export function Stories() {
  const { audience } = useAudience();
  const stories = audience === "candidate" ? CANDIDATE_STORIES : FOUNDER_STORIES;
  const heading = audience === "candidate"
    ? <>People whose careers changed<br />through one <em>introduction.</em></>
    : <>Founders who stopped drowning in CVs<br />and started <em>hiring on instinct.</em></>;

  return (
    <section className="stories-sec" id="stories">
      <Reveal className="stories-header">
        <div className="eyebrow sec-intro-eyebrow">Real stories</div>
        <h2 className="sec-title sec-title--center">{heading}</h2>
      </Reveal>
      <div className="stories-bento">
        <StoryCard s={stories[0]!} featured />
        <div className="stories-bento-col">
          <StoryCard s={stories[1]!} />
          <StoryCard s={stories[2]!} />
        </div>
      </div>
      <Reveal delay={4}>
        <p className="stories-disclaimer">
          Stories are illustrative; timelines and outcomes vary by role, company, and market.
        </p>
      </Reveal>
    </section>
  );
}
