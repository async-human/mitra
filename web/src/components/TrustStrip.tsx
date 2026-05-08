"use client";

import { useAudience } from "./AudienceContext";

const PLACEMENTS = [
  { name: "Setu", stage: "Series B", color: "#1B5E5A" },
  { name: "Razorpay", stage: "Series D", color: "#C07A28" },
  { name: "CRED", stage: "Late-stage", color: "#6B4FBB" },
  { name: "Hyperface", stage: "Series A", color: "#1A6B5A" },
  { name: "Finbox", stage: "Series B", color: "#B06020" },
  { name: "Jupiter", stage: "Series C", color: "#2255CC" },
  { name: "Jar", stage: "Series B", color: "#C03060" },
  { name: "Groww", stage: "Series D", color: "#6BBB22" },
];

const HIRING = [
  { name: "Setu", role: "3 engineers", color: "#1B5E5A" },
  { name: "Hyperface", role: "PM + Eng", color: "#1A6B5A" },
  { name: "Finbox", role: "ML + Risk", color: "#B06020" },
  { name: "Razorpay", role: "2 PMs", color: "#C07A28" },
  { name: "Jupiter", role: "Backend", color: "#2255CC" },
  { name: "CRED", role: "Data Eng", color: "#6B4FBB" },
];

export function TrustStrip() {
  const { audience } = useAudience();

  if (audience === "candidate") {
    return (
      <section className="ts" aria-label="Recent placements">
        <div className="ts-label">Recent placements at</div>
        <div className="ts-chips">
          {PLACEMENTS.map((p) => (
            <div key={p.name} className="ts-chip">
              <span className="ts-chip-dot" style={{ background: p.color }} />
              <span className="ts-chip-name">{p.name}</span>
              <span className="ts-chip-stage">{p.stage}</span>
            </div>
          ))}
        </div>
        <div className="ts-note">+ dozens more VC-backed startups across India</div>
      </section>
    );
  }

  return (
    <section className="ts" aria-label="Hiring partners">
      <div className="ts-label">Currently hiring via Mitra</div>
      <div className="ts-chips">
        {HIRING.map((h) => (
          <div key={h.name} className="ts-chip">
            <span className="ts-chip-dot" style={{ background: h.color }} />
            <span className="ts-chip-name">{h.name}</span>
            <span className="ts-chip-stage">{h.role}</span>
          </div>
        ))}
      </div>
      <div className="ts-note">Seed through Series C · India-headquartered product startups only</div>
    </section>
  );
}
