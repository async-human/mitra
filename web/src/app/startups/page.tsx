import type { Metadata } from "next";
import { StartupsClient, type CompanyFeedItem } from "./StartupsClient";
import s from "./startups.module.css";

export const metadata: Metadata = {
  title: "Funded Startups Hiring Now",
  description:
    "Browse India's best-funded startups that are actively hiring — Series A through late stage. Fintech, B2B SaaS, Consumer, and more.",
};

export const revalidate = 3600; // rebuild every hour

async function getCompanies(): Promise<CompanyFeedItem[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
  try {
    const res = await fetch(`${apiUrl}/public/companies`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
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
