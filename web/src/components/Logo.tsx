import Link from "next/link";
import { MitraMark } from "./icons";

export function Logo({ href = "#" }: { href?: string }) {
  return (
    <Link href={href} className="nav-logo" aria-label="Mitra — home">
      <span className="logo-mark">
        <MitraMark size={18} />
      </span>
      <span className="logo-type">
        Mitra<span>.</span>
      </span>
    </Link>
  );
}
