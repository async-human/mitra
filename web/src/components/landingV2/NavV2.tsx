import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import s from "./landing-v2.module.css";

export function NavV2() {
  return (
    <nav className={s.nav}>
      <div className={s.navInner}>
        <Link href="/" className={s.navLogo}>
          <div className={s.navLogoMark}>M</div>
          Mitra.
        </Link>

        <ul className={s.navLinks}>
          <li><a href="#how-it-works">How it works</a></li>
          <li><a href="#faq">FAQ</a></li>
          <li><a href="#for-companies">For companies</a></li>
        </ul>

        <div className={s.navRight}>
          <Link href="/dashboard" className={s.navSignIn}>Sign in</Link>
          <a
            href={whatsAppHrefFor("candidate")}
            target="_blank"
            rel="noopener noreferrer"
            className={s.navCtaBtn}
          >
            Get started
          </a>
        </div>
      </div>
    </nav>
  );
}
