"use client";

import { useAudience } from "./AudienceContext";

const PLACEMENTS = [
  { name: "Setu", stage: "Series B", color: "#5E6AD2" },
  { name: "Razorpay", stage: "Series D", color: "#5E6AD2" },
  { name: "CRED", stage: "Late-stage", color: "#5E6AD2" },
  { name: "Hyperface", stage: "Series A", color: "#5E6AD2" },
  { name: "Finbox", stage: "Series B", color: "#5E6AD2" },
  { name: "Jupiter", stage: "Series C", color: "#5E6AD2" },
  { name: "Jar", stage: "Series B", color: "#5E6AD2" },
  { name: "Groww", stage: "Series D", color: "#5E6AD2" },
  { name: "Zepto", stage: "Series E", color: "#5E6AD2" },
  { name: "Slice", stage: "Series B", color: "#5E6AD2" },
];

const HIRING = [
  { name: "Setu", role: "3 engineers", color: "#5E6AD2" },
  { name: "Hyperface", role: "PM + Eng", color: "#5E6AD2" },
  { name: "Finbox", role: "ML + Risk", color: "#5E6AD2" },
  { name: "Razorpay", role: "2 PMs", color: "#5E6AD2" },
  { name: "Jupiter", role: "Backend", color: "#5E6AD2" },
  { name: "CRED", role: "Data Eng", color: "#5E6AD2" },
  { name: "Jar", role: "Growth PM", color: "#5E6AD2" },
  { name: "Zepto", role: "Staff Eng", color: "#5E6AD2" },
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
