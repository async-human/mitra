import { LandingV1 } from "@/components/LandingV1";
import { LandingV2 } from "@/components/landingV2/LandingV2";
import { LandingV3 } from "@/components/landingV2/LandingV3";

// Toggle between landing page versions.
// V3 = streamlined: shorter copy, dark two-panel problem section, no Philosophy/Roadmap sections
// V2 = original full-length design (safe revert)
// V1 = legacy design
const USE_V3 = true;
const USE_V2 = false;

export default function HomePage() {
  if (USE_V3) return <LandingV3 />;
  if (USE_V2) return <LandingV2 />;
  return <LandingV1 />;
}
