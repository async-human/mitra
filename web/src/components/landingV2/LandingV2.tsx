import { NavV2 } from "./NavV2";
import { HeroV2 } from "./HeroV2";
import { HowItWorksV2 } from "./HowItWorksV2";
import { ProofV2 } from "./ProofV2";
import { ForCompaniesV2 } from "./ForCompaniesV2";
import { FAQV2 } from "./FAQV2";
import { FooterV2 } from "./FooterV2";
import s from "./landing-v2.module.css";

export function LandingV2() {
  return (
    <div className={s.root}>
      <NavV2 />
      <main>
        <HeroV2 />
        <HowItWorksV2 />
        <ProofV2 />
        <ForCompaniesV2 />
        <FAQV2 />
      </main>
      <FooterV2 />
    </div>
  );
}
