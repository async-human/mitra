import type { Metadata, Viewport } from "next";
import { Lora, Plus_Jakarta_Sans } from "next/font/google";
import { Providers } from "@/components/Providers";
import "./globals.css";

const lora = Lora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-lora",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-jakarta",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://mitra.work";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Mitra — India's AI Talent Agent",
    template: "%s · Mitra",
  },
  description:
    "Mitra is your personal AI talent agent. A 2-minute conversation on WhatsApp matches you to India's best-funded startups and introduces you directly to the founder. No cold applications. No ghosting. Ever.",
  keywords: [
    "AI talent agent",
    "India hiring",
    "startup jobs India",
    "WhatsApp jobs",
    "tech recruitment India",
    "India startup hiring",
    "AI recruiter",
    "Mitra",
  ],
  authors: [{ name: "Mitra Labs" }],
  creator: "Mitra Labs",
  publisher: "Mitra Labs",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: siteUrl,
    siteName: "Mitra",
    title: "Mitra — India's AI Talent Agent",
    description:
      "A 2-minute WhatsApp conversation, then warm introductions to India's best-funded startups. Free for candidates. 8% success fee for founders.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Mitra — India's AI Talent Agent",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Mitra — India's AI Talent Agent",
    description:
      "Stop sending CVs into the void. Get introduced. Free for candidates, always.",
    images: ["/og-image.png"],
    creator: "@mitra",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  category: "technology",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F6F1EA" },
    { media: "(prefers-color-scheme: dark)", color: "#1C1917" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${lora.variable} ${jakarta.variable}`} suppressHydrationWarning>
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
