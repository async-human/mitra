import type { Metadata } from "next";
import { StartupsClient, type CompanyFeedItem } from "./StartupsClient";
import s from "./startups.module.css";

export const metadata: Metadata = {
  title: "Funded Startups Hiring Now",
  description:
    "Browse India's best-funded startups that are actively hiring — Series A through late stage. Fintech, B2B SaaS, Consumer, and more.",
};

// Always fetch fresh — avoids caching an empty first response for an hour after deploy
export const dynamic = "force-dynamic";

function apiBase(): string {
  return (
    process.env.MITRA_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    ""
  ).replace(/\/$/, "");
}

async function getCompanies(): Promise<CompanyFeedItem[]> {
  const apiUrl = apiBase();
  if (!apiUrl) {
    console.error("startups: MITRA_API_BASE_URL / NEXT_PUBLIC_API_URL not set");
    return [];
  }
  try {
    const res = await fetch(`${apiUrl}/public/companies`, { cache: "no-store" });
    if (!res.ok) {
      console.error("startups: API returned", res.status, res.statusText);
      return [];
    }
    return res.json();
  } catch (err) {
    console.error("startups: fetch failed", err);
    return [];
  }
}

export default async function StartupsPage() {
  const companies = await getCompanies();

  return (
    <div className={s.page}>
      <StartupsClient companies={companies} />
    </div>
  );
}
