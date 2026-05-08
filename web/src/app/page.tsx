import { Comparison } from "@/components/Comparison";
import { Conversation } from "@/components/Conversation";
import { FAQ } from "@/components/FAQ";
import { FAQ_ITEMS } from "@/lib/faqData";
import { FinalCTA } from "@/components/FinalCTA";
import { FitAudience } from "@/components/FitAudience";
import { Footer } from "@/components/Footer";
import { Founders } from "@/components/Founders";
import { Hero } from "@/components/Hero";
import { HowItWorks } from "@/components/HowItWorks";
import { Nav } from "@/components/Nav";
import { Pricing } from "@/components/Pricing";
import { PrivacyPulse } from "@/components/PrivacyPulse";
import { Problem } from "@/components/Problem";
import { Stats } from "@/components/Stats";
import { Stories } from "@/components/Stories";
import { StickyMobileCta } from "@/components/StickyMobileCta";
import { TrustStrip } from "@/components/TrustStrip";

const ORGANIZATION_JSONLD = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Mitra",
  legalName: "Mitra Labs Pvt. Ltd.",
  url: "https://mitra.work",
  logo: "https://mitra.work/og-image.png",
  description:
    "India's AI talent agent. A 2-minute WhatsApp conversation matches candidates to funded startups via warm introductions to founders.",
  address: {
    "@type": "PostalAddress",
    addressCountry: "IN",
  },
  areaServed: "IN",
  sameAs: [],
};

const FAQ_JSONLD = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ_ITEMS.map((item) => ({
    "@type": "Question",
    name: item.q,
    acceptedAnswer: {
      "@type": "Answer",
      text: item.a,
    },
  })),
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(ORGANIZATION_JSONLD),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(FAQ_JSONLD) }}
      />
      <Nav />
      <main className="site-main">
        <Hero />
        <TrustStrip />
        <PrivacyPulse />
        <FitAudience />
        <Problem />
        <Founders />
        <HowItWorks />
        <Conversation />
        <Stats />
        <Stories />
        <Comparison />
        <Pricing />
        <FAQ />
        <FinalCTA />
      </main>
      <StickyMobileCta />
      <Footer />
    </>
  );
}
