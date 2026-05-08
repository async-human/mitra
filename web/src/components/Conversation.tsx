import { Reveal } from "./Reveal";
import { SendIcon } from "./icons";

const MATCHES = [
  {
    role: "Staff Engineer · Setu (Series B)",
    score: "96% fit",
    tags: ["₹42–52L", "Remote", "Fintech"],
  },
  {
    role: "Senior Backend · Hyperface (Series A)",
    score: "88% fit",
    tags: ["₹38–46L", "Hybrid · BLR", "Payments"],
  },
];

const QUOTES = [
  {
    id: "q1",
    quote: "Mitra asked me why I was really thinking of moving — not what my skills were. That was the moment I knew this was different.",
    attr: "Senior engineer · fintech placement",
  },
  {
    id: "q2",
    quote: "On every other platform I was a row in a spreadsheet. Here it felt like someone actually read what I'd built.",
    attr: "Senior engineer · fintech",
  },
  {
    id: "q3",
    quote: "The intro to the founder wasn't a forward of my CV — it was context I would have taken twenty minutes to explain.",
    attr: "Backend engineer · Series B",
  },
];

export function Conversation() {
  return (
    <section className="convo">
      <Reveal className="convo-header">
        <div className="eyebrow">The Mitra experience</div>
        <h2 className="sec-title convo-sec-title">
          A conversation,<br />not a <em>form.</em>
        </h2>
        <p className="convo-lead">
          Every platform makes you fill in fields. Mitra has a real conversation on WhatsApp, where you already are. A conversation surfaces{" "}
          <strong className="convo-strong">intent</strong>, and intent is what determines whether an introduction becomes an offer.
        </p>
      </Reveal>

      <div className="convo-inner">
        <Reveal delay={1}>
          <div
            className="chat-wrap"
            role="img"
            aria-label="Sample WhatsApp conversation between Mitra and a candidate"
          >
            <div className="chat-top">
              <div className="chat-av">
                M<div className="chat-online" />
              </div>
              <div>
                <div className="chat-av-name">Mitra</div>
                <div className="chat-av-status">AI Talent Agent · Online now</div>
              </div>
            </div>
            <div className="chat-body">
              <div className="chat-date">Today · 10:14 AM</div>
              <div className="cm" style={{ animation: "up .4s .4s both", opacity: 0 }}>
                <div className="cm-av m">M</div>
                <div className="cm-bub in">
                  Before we look at roles —{" "}
                  <strong>why are you thinking of moving right now?</strong>
                </div>
              </div>
              <div className="cm out" style={{ animation: "up .4s 1.0s both", opacity: 0 }}>
                <div className="cm-av u">Y</div>
                <div className="cm-bub out-b">
                  3 years at Infosys maintaining legacy code. I want to actually build something that matters.
                </div>
              </div>
              <div className="cm" style={{ animation: "up .4s 1.7s both", opacity: 0 }}>
                <div className="cm-av m">M</div>
                <div className="cm-bub in">
                  <strong>What&apos;s the last thing you built that you were genuinely proud of?</strong>
                </div>
              </div>
              <div className="cm out" style={{ animation: "up .4s 2.4s both", opacity: 0 }}>
                <div className="cm-av u">Y</div>
                <div className="cm-bub out-b">
                  A real-time fraud detection pipeline. Nobody asked me to. Cut false positives by 40%.
                </div>
              </div>
              <div className="cm" style={{ animation: "up .4s 3.1s both", opacity: 0 }}>
                <div className="cm-av m">M</div>
                <div className="cm-bub in">
                  That tells me exactly the environment where you&apos;ll thrive.{" "}
                  <strong>2 strong matches:</strong>
                  <div className="match-chips">
                    {MATCHES.map((m) => (
                      <div className="mc" key={m.role}>
                        <div className="mc-top">
                          <span className="mc-role">{m.role}</span>
                          <span className="mc-score">{m.score}</span>
                        </div>
                        <div className="mc-meta">
                          {m.tags.map((t) => (
                            <span className="mc-tag" key={t}>{t}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="chat-inbar">
              <div className="chat-infield">Intro me to Setu please</div>
              <button type="button" className="chat-send-btn" aria-label="Send message">
                <SendIcon size={15} />
              </button>
            </div>
          </div>
        </Reveal>

        <div className="convo-quotes-col">
          {QUOTES.map((q, i) => (
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
