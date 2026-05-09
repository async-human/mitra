import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Logo } from "./Logo";

type FooterLink = { label: string; href: string; external?: boolean };

const TALENT_LINKS: FooterLink[] = [
  { label: "Chat with Mitra", href: whatsAppHrefFor("candidate"), external: true },
  { label: "Salary benchmark", href: "/salary-benchmark" },
  { label: "Resume review", href: "/resume-review" },
  { label: "Refer and earn ₹10K", href: "/refer" },
];

const FOUNDER_LINKS: FooterLink[] = [
  { label: "List a role", href: whatsAppHrefFor("founder"), external: true },
  { label: "Pricing", href: "#pricing" },
  { label: "Book a call", href: whatsAppHrefFor("founder"), external: true },
];

const COMPANY_LINKS: FooterLink[] = [
  { label: "Our manifesto", href: "/manifesto" },
  { label: "Blog", href: "/blog" },
  { label: "We are hiring", href: "/careers" },
  { label: "Privacy", href: "/privacy" },
  { label: "Cookie policy", href: "/cookies" },
];

function LinkColumn({
  heading,
  links,
}: {
  heading: string;
  links: FooterLink[];
}) {
  return (
    <div>
      <div className="fc-hd">{heading}</div>
      <ul className="fc-lnks">
        {links.map((l) =>
          l.external ? (
            <li key={l.label}>
              <a href={l.href} target="_blank" rel="noopener noreferrer">
                {l.label}
              </a>
            </li>
          ) : (
            <li key={l.label}>
              <Link href={l.href}>{l.label}</Link>
            </li>
          ),
        )}
      </ul>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="foot-top">
        <div>
          <Logo />
          <p className="foot-desc">
            India&apos;s AI talent agent. We don&apos;t help you apply — we
            make the introduction ourselves.
          </p>
        </div>
        <LinkColumn heading="For talent" links={TALENT_LINKS} />
        <LinkColumn heading="For founders" links={FOUNDER_LINKS} />
        <LinkColumn heading="Company" links={COMPANY_LINKS} />
      </div>
      <div className="foot-btm">
        <span className="fc-copy">
          © {new Date().getFullYear()} Mitra Labs Pvt. Ltd. · India
        </span>
        <span className="fc-made">
          Built with <span>care</span> for India&apos;s builders
        </span>
      </div>
    </footer>
  );
}
