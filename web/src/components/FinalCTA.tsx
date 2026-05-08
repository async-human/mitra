import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Reveal } from "./Reveal";
import { BriefcaseIcon, WhatsAppIcon } from "./icons";

export function FinalCTA() {
  return (
    <section className="final-sec">
      <Reveal className="final-inner">
        <div className="final-kicker">Your next chapter starts here</div>
        <h2 className="final-h2">
          One conversation.
          <br />
          <em>One introduction.</em>
          <br />
          Everything changes.
        </h2>
        <p className="final-sub">
          Whether you&apos;re looking for your next role or your next great
          hire — Mitra works for you. Not a platform. A partner.
        </p>
        <div className="final-btns">
          <a
            href={whatsAppHrefFor("candidate")}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-fp"
          >
            <WhatsAppIcon size={16} />
            I&apos;m looking for a role
          </a>
          <a
            href={whatsAppHrefFor("founder")}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-fs"
          >
            <BriefcaseIcon size={16} />
            I&apos;m a founder hiring
          </a>
        </div>
        <p className="final-bridge">
          <a
            href={whatsAppHrefFor("general")}
            target="_blank"
            rel="noopener noreferrer"
            className="final-bridge-link"
          >
            Not sure yet? Ask us anything on WhatsApp →
          </a>
        </p>
        <p className="final-note">
          Serving talent and startups across India · Free for candidates,
          always
        </p>
      </Reveal>
    </section>
  );
}
