import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

/** Decorative gradient bands — Mitra warm palette, not a literal copy of reference sites. */
export function HeroAccentBars({ audience }: { audience: V2Audience }) {
  return (
    <div
      className={s.heroAccent}
      data-audience={audience}
      aria-hidden="true"
    >
      <div className={s.heroAccentBars}>
        <span className={s.heroAccentBar} />
        <span className={s.heroAccentBar} />
        <span className={s.heroAccentBar} />
        <span className={s.heroAccentBar} />
        <span className={s.heroAccentBar} />
        <span className={s.heroAccentBar} />
      </div>
    </div>
  );
}
