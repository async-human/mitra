import type { Metadata } from "next";
import { MetricsDashboard } from "./MetricsDashboard";

export const metadata: Metadata = {
  title: "Admin · Mitra",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return <MetricsDashboard />;
}
