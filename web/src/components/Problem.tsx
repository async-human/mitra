import { Reveal } from "./Reveal";
import { ProblemRotors } from "./ProblemRotors";

export function Problem() {
  return (
    <section className="problem">
      <div className="prob-eyebrow">The problem we solve</div>
      <Reveal as="h2" className="prob-h2">
        The hiring system in India
        <br />
        is broken for <em>everyone.</em>
      </Reveal>
      <Reveal as="p" className="prob-sub" delay={1}>
        Whether you&apos;re looking for your next role or trying to fill one —
        the usual tools optimise for volume or fees, not fit. Below are real
        shapes of that failure — they rotate so you see how often the same
        story shows up.
      </Reveal>

      <Reveal delay={2}>
        <ProblemRotors />
      </Reveal>
    </section>
  );
}
