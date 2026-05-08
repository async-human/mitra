import Link from "next/link";

export function PrivacyPulse() {
  return (
    <aside
      className="privacy-pulse"
      aria-label="Data and privacy"
    >
      <p className="privacy-pulse-inner">
        <strong className="privacy-pulse-lead">Privacy</strong>{' '}
        We take conversations seriously: intake stays in Mitra&apos;s hiring systems,
        summarized for intros only when you agree.
        <Link href="#faq-whatsapp-data" className="privacy-pulse-link">
          How we handle WhatsApp data →
        </Link>
      </p>
    </aside>
  );
}
