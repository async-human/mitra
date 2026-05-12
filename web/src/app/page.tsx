import { LandingV1 } from "@/components/LandingV1";
import { LandingV2 } from "@/components/landingV2/LandingV2";

// Toggle this to switch between the two landing pages.
// true  → new minimal design (V2)
// false → original full-length design (V1)
const USE_V2 = true;

export default function HomePage() {
  return USE_V2 ? <LandingV2 /> : <LandingV1 />;
}
