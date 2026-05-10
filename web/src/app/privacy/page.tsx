import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy — Mitra",
  description: "How Mitra collects, uses, and protects your personal data.",
  robots: { index: true, follow: true },
};

export default function PrivacyPolicyPage() {
  return (
    <div className="legal-page">
      <div className="legal-inner">
        <Link href="/" className="legal-back">← Back to Mitra</Link>

        <h1 className="legal-h1">Privacy Policy</h1>
        <p className="legal-meta">Last updated: May 2026</p>

        <section className="legal-sec">
          <h2>Who we are</h2>
          <p>
            Mitra is an AI-powered talent agent for India's startup ecosystem. We help candidates find
            the right startup roles and help founders hire the right people — primarily over WhatsApp.
            References to "Mitra", "we", "us", or "our" in this policy refer to the Mitra platform and
            its operators.
          </p>
          <p>
            For questions about this policy, contact us at{" "}
            <a href="mailto:hello@mitra.work">hello@mitra.work</a>.
          </p>
        </section>

        <section className="legal-sec">
          <h2>What data we collect</h2>

          <h3>When you use Mitra via WhatsApp</h3>
          <ul>
            <li>Your WhatsApp phone number (used as your session identifier)</li>
            <li>The content of messages you send to Mitra</li>
            <li>Career signals you share: role, company, skills, salary expectations, location preferences</li>
            <li>Any documents you send (e.g. a CV/resume) — parsed for structured career data</li>
          </ul>

          <h3>When you use the Mitra web app</h3>
          <ul>
            <li>Your email address (if you sign in)</li>
            <li>Your name and profile information</li>
            <li>Your cookie preferences (stored locally in your browser)</li>
          </ul>

          <h3>When you are a founder/employer</h3>
          <ul>
            <li>Company name, role, and contact details you provide</li>
            <li>Job listings you submit through the platform</li>
          </ul>
        </section>

        <section className="legal-sec">
          <h2>How we use your data</h2>
          <table className="legal-table">
            <thead>
              <tr><th>Purpose</th><th>Legal basis</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Matching you with relevant job opportunities</td>
                <td>Contract / legitimate interest</td>
              </tr>
              <tr>
                <td>Sending introductions between candidates and founders</td>
                <td>Consent (you explicitly request each intro)</td>
              </tr>
              <tr>
                <td>Personalising career advice and salary benchmarks</td>
                <td>Legitimate interest</td>
              </tr>
              <tr>
                <td>Improving the Mitra service</td>
                <td>Legitimate interest</td>
              </tr>
              <tr>
                <td>Communicating service updates</td>
                <td>Legitimate interest</td>
              </tr>
            </tbody>
          </table>
          <p>
            We do <strong>not</strong> sell your personal data to third parties. We do not use your data
            for advertising.
          </p>
        </section>

        <section className="legal-sec">
          <h2>Where your data is stored</h2>
          <p>
            Your data is stored in the following systems, all of which operate under appropriate data
            processing agreements:
          </p>
          <ul>
            <li><strong>Supabase (PostgreSQL)</strong> — durable candidate and job data, hosted on AWS (ap-south-1 region)</li>
            <li><strong>Redis</strong> — short-term conversation session data (30-day TTL)</li>
            <li><strong>OpenAI</strong> — message content is sent to OpenAI's API for AI responses; subject to OpenAI's data processing terms</li>
          </ul>
        </section>

        <section className="legal-sec">
          <h2>How long we keep your data</h2>
          <ul>
            <li><strong>Conversation history</strong>: stored in Redis with a 30-day rolling TTL</li>
            <li><strong>Career signals</strong>: kept until you request deletion</li>
            <li><strong>Intro records</strong>: kept for up to 12 months for dispute resolution</li>
          </ul>
        </section>

        <section className="legal-sec">
          <h2>Your rights</h2>
          <p>You can ask us at any time to:</p>
          <ul>
            <li>Access the personal data we hold about you</li>
            <li>Correct inaccurate data</li>
            <li>Delete your data entirely (right to erasure)</li>
            <li>Export your data in a portable format</li>
          </ul>
          <p>
            To exercise any of these rights, message us on WhatsApp or email{" "}
            <a href="mailto:hello@mitra.work">hello@mitra.work</a>. We will respond within 30 days.
          </p>
        </section>

        <section className="legal-sec">
          <h2>Cookies</h2>
          <p>
            We use a small number of cookies on the Mitra website. See our{" "}
            <Link href="/cookies">Cookie Policy</Link> for details.
          </p>
        </section>

        <section className="legal-sec">
          <h2>Third-party services</h2>
          <p>Mitra uses the following third-party services to operate:</p>
          <ul>
            <li><strong>WhatsApp (Meta)</strong> — message delivery channel</li>
            <li><strong>OpenAI</strong> — AI language model powering conversations</li>
            <li><strong>Twilio</strong> — fallback WhatsApp message delivery</li>
            <li><strong>Resend</strong> — transactional email delivery</li>
            <li><strong>Railway</strong> — application hosting</li>
            <li><strong>Supabase</strong> — database hosting</li>
          </ul>
          <p>
            Each of these providers has its own privacy policy and data processing terms.
          </p>
        </section>

        <section className="legal-sec">
          <h2>Changes to this policy</h2>
          <p>
            We may update this policy as the product evolves. Material changes will be communicated via
            WhatsApp or email. The "Last updated" date at the top of this page reflects the most recent
            revision.
          </p>
        </section>

        <section className="legal-sec">
          <h2>Contact</h2>
          <p>
            Questions or requests about your data:{" "}
            <a href="mailto:hello@mitra.work">hello@mitra.work</a>
          </p>
        </section>

        <Link href="/cookies" className="legal-link">Cookie Policy →</Link>
      </div>
    </div>
  );
}
