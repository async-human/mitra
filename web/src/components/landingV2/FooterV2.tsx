import Link from "next/link";
import s from "./landing-v2.module.css";

export function FooterV2() {
  return (
    <footer className={s.footer}>
      <div className={s.footerContent}>
        <div className={s.footerTop}>
          <ul className={s.footerLinks}>
            <li><a href="#how-it-works">How it works</a></li>
            <li><a href="#for-companies">For companies</a></li>
            <li><a href="#faq">FAQ</a></li>
            <li><Link href="/dashboard">Sign in</Link></li>
          </ul>
          <p className={s.footerCopy}>© 2025 Mitra Labs Pvt. Ltd.</p>
        </div>
      </div>

      <span className={s.footerBigText} aria-hidden="true">Mitra.</span>
    </footer>
  );
}
