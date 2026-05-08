"use client";

import { Reveal } from "./Reveal";
import { SendIcon } from "./icons";
import { useAudience } from "./AudienceContext";

/* ── CANDIDATE CONTENT ── */
const CANDIDATE_MATCHES = [
  { role: "Staff Engineer · Setu (Series B)", score: "96% fit", tags: ["₹42–52L", "Remote", "Fintech"] },
  { role: "Senior Backend · Hyperface (Series A)", score: "88% fit", tags: ["₹38–46L", "Hybrid · BLR", "Payments"] },
];

const CANDIDATE_QUOTES = [
  { id: "q1", quote: "Mitra asked me why I was really thinking of moving — not what my skills were. That was the moment I knew this was different.", attr: "Senior engineer · fintech placement" },
  { id: "q2", quote: "On every other platform I was a row in a spreadsheet. Here it felt like someone actually read what I'd built.", attr: "Senior engineer · fintech" },
  { id: "q3", quote: "The intro to the founder wasn't a forward of my CV — it was context I would have taken twenty minutes to explain.", attr: "Backend engineer · Series B" },
];

/* ── FOUNDER CONTENT ── */
const FOUNDER_INTROS = [
  { name: "Arjun K.", title: "Staff Engineer · 6 yrs", tags: ["₹48L", "30-day notice", "Infra / Golang"], score: "Strong match" },
  { name: "Neha S.", title: "Senior PM · 5 yrs", tags: ["₹54L", "Immediate", "Growth / B2C"], score: "Startup-only" },
];

const FOUNDER_QUOTES = [
  { id: "fq1", quote: "Every intro came with a paragraph on why they wanted to join us specifically. We skipped the first 30 minutes of every interview.", attr: "Founder, Hyperface · Series A" },
  { id: "fq2", quote: "I wasted 3 months with an agency. Mitra had us in conversations with 4 pre-qualified candidates in the first week.", attr: "CTO, Finbox · Series B" },
  { id: "fq3", quote: "The context notes tell me what the candidate won't compromise on. That alone saves us from bad hires.", attr: "Founder, Setu · Series B" },
];

function CandidateChat() {
  return (
    <div className="chat-wrap" role="img" aria-label="Sample WhatsApp conversation between Mitra and a candidate">
      <div className="chat-top">
        <div className="chat-av">M<div className="chat-online" /></div>
        <div>
          <div className="chat-av-name">Mitra</div>
          <div className="chat-av-status">AI Talent Agent · Online now</div>
        </div>
      </div>
      <div className="chat-body">
        <div className="chat-date">Today · 10:14 AM</div>
        <div className="cm" style={{ animation: "up .4s .4s both", opacity: 0 }}>
          <div className="cm-av m">M</div>
          <div className="cm-bub in">Before we look at roles — <strong>why are you thinking of moving right now?</strong></div>
        </div>
        <div className="cm out" style={{ animation: "up .4s 1.0s both", opacity: 0 }}>
          <div className="cm-av u">Y</div>
          <div className="cm-bub out-b">3 years at Infosys maintaining legacy code. I want to actually build something that matters.</div>
        </div>
        <div className="cm" style={{ animation: "up .4s 1.7s both", opacity: 0 }}>
          <div className="cm-av m">M</div>
          <div className="cm-bub in"><strong>What&apos;s the last thing you built that you were genuinely proud of?</strong></div>
        </div>
        <div className="cm out" style={{ animation: "up .4s 2.4s both", opacity: 0 }}>
          <div className="cm-av u">Y</div>
          <div className="cm-bub out-b">A real-time fraud detection pipeline. Nobody asked me to. Cut false positives by 40%.</div>
        </div>
        <div className="cm" style={{ animation: "up .4s 3.1s both", opacity: 0 }}>
          <div className="cm-av m">M</div>
          <div className="cm-bub in">
            That tells me exactly the environment where you&apos;ll thrive. <strong>2 strong matches:</strong>
            <div className="match-chips">
              {CANDIDATE_MATCHES.map((m) => (
                <div className="mc" key={m.role}>
                  <div className="mc-top"><span className="mc-role">{m.role}</span><span className="mc-score">{m.score}</span></div>
                  <div className="mc-meta">{m.tags.map((t) => <span className="mc-tag" key={t}>{t}</span>)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="chat-inbar">
        <div className="chat-infield">Intro me to Setu please</div>
        <button type="button" className="chat-send-btn" aria-label="Send message"><SendIcon size={15} /></button>
      </div>
    </div>
  );
}

function FounderChat() {
  return (
    <div className="chat-wrap" role="img" aria-label="Sample WhatsApp conversation between Mitra and a founder">
      <div className="chat-top">
        <div className="chat-av">M<div className="chat-online" /></div>
        <div>
          <div className="chat-av-name">Mitra</div>
          <div className="chat-av-status">AI Talent Partner · Online now</div>
        </div>
      </div>
      <div className="chat-body">
        <div className="chat-date">Today · 9:32 AM</div>
        <div className="cm out" style={{ animation: "up .4s .4s both", opacity: 0 }}>
          <div className="cm-av u">P</div>
          <div className="cm-bub out-b">We need a Staff Engineer, infra focus. Growing fast, no corp nonsense.</div>
        </div>
        <div className="cm" style={{ animation: "up .4s 1.0s both", opacity: 0 }}>
          <div className="cm-av m">M</div>
          <div className="cm-bub in"><strong>What&apos;s the one thing that would make this hire a failure 6 months in?</strong></div>
        </div>
        <div className="cm out" style={{ animation: "up .4s 1.7s both", opacity: 0 }}>
          <div className="cm-av u">P</div>
          <div className="cm-bub out-b">Someone who needs to be told what to do. We need an owner, not an executor.</div>
        </div>
        <div className="cm" style={{ animation: "up .4s 2.4s both", opacity: 0 }}>
          <div className="cm-av m">M</div>
          <div className="cm-bub in">Got it. <strong>First intros by Thursday.</strong> Here&apos;s who I&apos;m qualifying now:
            <div className="match-chips">
              {FOUNDER_INTROS.map((c) => (
                <div className="mc" key={c.name}>
                  <div className="mc-top"><span className="mc-role">{c.name} · {c.title}</span><span className="mc-score">{c.score}</span></div>
                  <div className="mc-meta">{c.tags.map((t) => <span className="mc-tag" key={t}>{t}</span>)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="chat-inbar">
        <div className="chat-infield">Send me Arjun&apos;s full context</div>
        <button type="button" className="chat-send-btn" aria-label="Send message"><SendIcon size={15} /></button>
      </div>
    </div>
  );
}

export function Conversation() {
  const { audience } = useAudience();

  const copy = audience === "candidate" ? {
    heading: <>A conversation,<br />not a <em>form.</em></>,
    lead: <>Every platform makes you fill in fields. Mitra has a real conversation on WhatsApp, where you already are. A conversation surfaces <strong className="convo-strong">intent</strong>, and intent is what determines whether an introduction becomes an offer.</>,
    quotes: CANDIDATE_QUOTES,
    chat: <CandidateChat />,
  } : {
    heading: <>We ask what job boards<br />never <em>think to ask.</em></>,
    lead: <>Every agency sends you a pile of CVs. Mitra asks the founder what a failed hire looks like in 6 months — then screens for that. The result is <strong className="convo-strong">context</strong>, and context is what turns an introduction into a hire.</>,
    quotes: FOUNDER_QUOTES,
    chat: <FounderChat />,
  };

  return (
    <section className="convo">
      <Reveal className="convo-header">
        <div className="eyebrow">The Mitra experience</div>
        <h2 className="sec-title convo-sec-title">{copy.heading}</h2>
        <p className="convo-lead">{copy.lead}</p>
      </Reveal>

      <div className="convo-inner">
        <Reveal delay={1}>{copy.chat}</Reveal>

        <div className="convo-quotes-col">
          {copy.quotes.map((q, i) => (
            <Reveal key={q.id} delay={([2, 3, 4] as const)[i]} className="convo-qcard">
              <p className="convo-qcard-text">&ldquo;{q.quote}&rdquo;</p>
              <p className="convo-qcard-attr">{q.attr}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
