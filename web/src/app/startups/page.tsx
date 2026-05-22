import type { Metadata } from "next";
import { StartupsClient } from "./StartupsClient";
import s from "./startups.module.css";

export const metadata: Metadata = {
  title: "Funded Startups Hiring Now",
  description:
    "Browse India's best-funded startups that are actively hiring — Series A through late stage. Fintech, B2B SaaS, Consumer, and more.",
};

export default function StartupsPage() {
  return (
    <div className={s.page}>
      <StartupsClient />
    </div>
  );
}
