import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const CTA = {
  candidate: { label: "Get started", href: "/sign-in?role=candidate", external: false },
  company:   { label: "List a role", href: whatsAppHrefFor("founder"),  external: true  },
};

interface NavV2Props {
  audience: V2Audience;
  onAudienceChange: (a: V2Audience) => void;
}

export function NavV2({ audience, onAudienceChange }: NavV2Props) {
  const isCompany = audience === "company";

  return (
    <nav className={s.nav}>
      <div className={s.navInner}>
        <Link href="/" className={s.navLogo}>
          <div className={s.navLogoMark}>M</div>
          Mitra.
        </Link>

        {/* Segmented pill — both options always visible */}
        <div className={s.navToggle} role="tablist" aria-label="View for">
          <button
            role="tab"
            type="button"
            aria-selected={!isCompany}
            className={`${s.navToggleBtn} ${!isCompany ? s.navToggleBtnActive : ""}`}
            onClick={() => onAudienceChange("candidate")}
          >
            Candidates
          </button>
          <button
            role="tab"
            type="button"
            aria-selected={isCompany}
            className={`${s.navToggleBtn} ${isCompany ? s.navToggleBtnActive : ""}`}
            onClick={() => onAudienceChange("company")}
          >
            Companies
          </button>
        </div>

        <div className={s.navRight}>
          <ul className={s.navLinks}>
            <li><a href="#how-it-works">How it works</a></li>
            <li><a href="#faq">FAQ</a></li>
          </ul>
          <Link href="/sign-in" className={s.navSignIn}>Sign in</Link>
          {CTA[audience].external ? (
            <a href={CTA[audience].href} target="_blank" rel="noopener noreferrer" className={s.navCtaBtn}>
              {CTA[audience].label}
            </a>
          ) : (
            <Link href={CTA[audience].href} className={s.navCtaBtn}>
              {CTA[audience].label}
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
