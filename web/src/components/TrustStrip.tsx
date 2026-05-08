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
  { name: "Zepto", stage: "Series E", color: "#C07A28" },
  { name: "Slice", stage: "Series B", color: "#6B4FBB" },
];

const HIRING = [
  { name: "Setu", role: "3 engineers", color: "#1B5E5A" },
  { name: "Hyperface", role: "PM + Eng", color: "#1A6B5A" },
  { name: "Finbox", role: "ML + Risk", color: "#B06020" },
  { name: "Razorpay", role: "2 PMs", color: "#C07A28" },
  { name: "Jupiter", role: "Backend", color: "#2255CC" },
  { name: "CRED", role: "Data Eng", color: "#6B4FBB" },
  { name: "Jar", role: "Growth PM", color: "#C03060" },
  { name: "Zepto", role: "Staff Eng", color: "#C07A28" },
];

function Chip({ name, detail, color }: { name: string; detail: string; color: string }) {
  return (
    <div className="ts-chip">
      <span className="ts-chip-dot" style={{ background: color }} />
      <span className="ts-chip-name">{name}</span>
      <span className="ts-chip-stage">{detail}</span>
    </div>
  );
}

export function TrustStrip() {
  const { audience } = useAudience();
  const items = audience === "candidate" ? PLACEMENTS : HIRING;
  const label = audience === "candidate" ? "Recent placements at" : "Currently hiring via Mitra";

  return (
    <section className="ts" aria-label={label}>
      <div className="ts-label">{label}</div>
      <div className="ts-marquee-wrap">
        <div className="ts-marquee-track">
          {/* Duplicated for seamless loop */}
          {[...items, ...items].map((item, i) => (
            <Chip
              key={i}
              name={item.name}
              detail={"stage" in item ? item.stage : item.role}
              color={item.color}
            />
          ))}
        </div>
      </div>
      <div className="ts-note">
        {audience === "candidate"
          ? "+ dozens more VC-backed startups across India"
          : "Seed through Series C · India-headquartered product startups only"}
      </div>
    </section>
  );
}
