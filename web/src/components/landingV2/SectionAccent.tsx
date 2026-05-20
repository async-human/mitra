import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

export type SectionAccentVariant = "foot" | "bridge" | "crown" | "rim";

type Props = {
  audience: V2Audience;
  variant: SectionAccentVariant;
  /** Mirror the dip curve (alternate bridges down the page). */
  flip?: boolean;
  className?: string;
};

function Bands({ count, tier }: { count: number; tier: "full" | "soft" | "whisper" }) {
  return (
    <div className={`${s.accentBands} ${s[`accentBands_${tier}`]}`}>
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className={s.accentBar} />
      ))}
    </div>
  );
}

/** Curved transition between band stacks — fill matches the section below. */
function AccentDip({
  audience,
  flip,
  fillClass,
}: {
  audience: V2Audience;
  flip?: boolean;
  fillClass: string;
}) {
  const path = flip
    ? "M0,0 C360,28 1080,28 1440,0 L1440,32 L0,32 Z"
    : "M0,32 C360,4 1080,4 1440,32 L1440,0 L0,0 Z";

  return (
    <svg
      className={`${s.accentDip} ${s[fillClass]}`}
      viewBox="0 0 1440 32"
      preserveAspectRatio="none"
      aria-hidden="true"
      data-audience={audience}
    >
      <path d={path} />
    </svg>
  );
}

/**
 * Mitra terracotta accent system — full-bleed bands, dips, and light rims.
 * Variants are composed to feel native to each section transition.
 */
export function SectionAccent({ audience, variant, flip, className }: Props) {
  const rootClass = [
    s.accent,
    s[`accent_${variant}`],
    flip ? s.accent_flip : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  if (variant === "foot") {
    return (
      <div className={rootClass} data-audience={audience} aria-hidden="true">
        <Bands count={6} tier="full" />
      </div>
    );
  }

  if (variant === "rim") {
    return (
      <div className={rootClass} data-audience={audience} aria-hidden="true">
        <Bands count={3} tier="whisper" />
      </div>
    );
  }

  if (variant === "crown") {
    return (
      <div className={rootClass} data-audience={audience} aria-hidden="true">
        <svg
          className={`${s.accentDip} ${s.accentDip_toDark} ${s.accentDip_crown}`}
          viewBox="0 0 1440 32"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d="M0,32 L0,10 Q720,0 1440,10 L1440,32 Z" />
        </svg>
        <Bands count={4} tier="soft" />
      </div>
    );
  }

  /* bridge: bands → dip → whisper bands */
  return (
    <div className={rootClass} data-audience={audience} aria-hidden="true">
      <Bands count={4} tier="full" />
      <AccentDip audience={audience} flip={flip} fillClass="accentDip_toTint" />
      <Bands count={2} tier="whisper" />
    </div>
  );
}
