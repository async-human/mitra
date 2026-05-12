import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Logo } from "@/components/Logo";
import type { Metadata } from "next";
import { UserMenu } from "./UserMenu";
import { DashboardClient } from "./DashboardClient";

export const metadata: Metadata = {
  title: "Dashboard · Mitra",
};

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) redirect("/sign-in");

  const user = session.user;

  return (
    <div className="dash-root">

      <header className="dash-topbar">
        <Logo />
        <div className="dash-topbar-right">
          <Link href="/" className="dash-topbar-back">← Back to site</Link>
          <UserMenu name={user.name} email={user.email} image={user.image} />
        </div>
      </header>

      <main className="dash-main">
        <DashboardClient
          userEmail={user.email ?? ""}
          firstName={user.name?.split(" ")[0] ?? "there"}
          greeting={getGreeting()}
          waHref={whatsAppHrefFor("candidate")}
        />
      </main>

      <footer className="dash-footer">
        <p>Mitra keeps your data private. <Link href="/cookies" className="dash-footer-link">Privacy policy</Link></p>
      </footer>

    </div>
  );
}
