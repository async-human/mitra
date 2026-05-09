import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description: "How Mitra uses cookies and how you can control them.",
  robots: { index: false, follow: false },
};

export default function CookiePolicyPage() {
  return (
    <div className="legal-page">
      <div className="legal-inner">
        <Link href="/" className="legal-back">← Back to Mitra</Link>

        <h1 className="legal-h1">Cookie Policy</h1>
        <p className="legal-meta">Last updated: May 2026</p>

        <section className="legal-sec">
          <h2>What are cookies?</h2>
          <p>
            Cookies are small text files stored on your device when you visit a website. They help the site remember your preferences and understand how you use it.
          </p>
        </section>

        <section className="legal-sec">
          <h2>What we use</h2>
          <p>Mitra uses two categories of cookies:</p>

          <h3>Essential cookies</h3>
          <p>These are required for the site to function. They cannot be turned off.</p>
          <table className="legal-table">
            <thead>
              <tr><th>Name</th><th>Purpose</th><th>Duration</th></tr>
            </thead>
            <tbody>
              <tr><td><code>mitra-theme</code></td><td>Remembers your light/dark mode preference</td><td>1 year</td></tr>
              <tr><td><code>mitra-cookie-consent</code></td><td>Stores your cookie consent choice</td><td>1 year</td></tr>
            </tbody>
          </table>

          <h3>Analytics cookies (optional)</h3>
          <p>
            If you accept all cookies, we may use analytics tools (e.g. Plausible or a self-hosted equivalent) to understand aggregate usage — pages visited, session duration. We do <strong>not</strong> use Google Analytics, Meta Pixel, or any advertising tracking. No personal data is sold.
          </p>
          <table className="legal-table">
            <thead>
              <tr><th>Name</th><th>Purpose</th><th>Duration</th></tr>
            </thead>
            <tbody>
              <tr><td><code>_plausible</code></td><td>Anonymous page view analytics</td><td>Session</td></tr>
            </tbody>
          </table>
        </section>

        <section className="legal-sec">
          <h2>Your choices</h2>
          <p>
            When you first visit, you can choose &ldquo;Essential only&rdquo; or &ldquo;Accept all&rdquo;. You can change your preference at any time by clearing your browser's local storage for <code>mitra.work</code>, or by contacting us below.
          </p>
          <p>
            You can also manage cookies directly in your browser settings — all major browsers let you block or delete cookies.
          </p>
        </section>

        <section className="legal-sec">
          <h2>Contact</h2>
          <p>
            Questions about how we use cookies? Write to us at{" "}
            <a href="mailto:hello@mitra.work">hello@mitra.work</a>.
          </p>
        </section>

        <Link href="/privacy" className="legal-link">Privacy Policy →</Link>
      </div>
    </div>
  );
}
