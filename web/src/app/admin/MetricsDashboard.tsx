"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
const KEY_STORAGE = "mitra_admin_key";

// ── Types ─────────────────────────────────────────────────────────────────────

interface MetricsSnapshot {
  total_candidates: number;
  total_jobs: number;
  active_jobs: number;
  total_intros: number;
}

interface FunnelStage {
  status: string;
  label: string;
  count: number;
  pct: number;
}

interface WeeklyPoint {
  week_start: string;
  intros: number;
  interviews: number;
  hires: number;
}

interface TopJob {
  job_id: number;
  title: string;
  company: string;
  stage: string | null;
  intros: number;
  hires: number;
  rate: number;
}

interface MetricsData {
  snapshot: MetricsSnapshot;
  funnel: FunnelStage[];
  by_status: Record<string, number>;
  weekly_trend: WeeklyPoint[];
  top_jobs: TopJob[];
  response_rate: number;
  ghosted_rate: number;
  avg_days_to_interview: number | null;
  avg_days_to_hire: number | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n.toLocaleString("en-IN");
}

function shortWeek(iso: string) {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-IN", { month: "short", day: "numeric", timeZone: "UTC" });
}

function pctColor(pct: number) {
  if (pct >= 20) return "#34D399";
  if (pct >= 10) return "#FBBF24";
  return "#60A5FA";
}

// ── Key Gate ─────────────────────────────────────────────────────────────────

function KeyGate({ onKey }: { onKey: (k: string) => void }) {
  const [val, setVal] = useState("");
  const [err, setErr] = useState("");
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => { ref.current?.focus(); }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!val.trim()) { setErr("Enter your admin key."); return; }
    onKey(val.trim());
  };

  return (
    <div className="adm-gate">
      <div className="adm-gate-card">
        <div className="adm-logo">Mitra<span className="adm-logo-dot">.</span></div>
        <p className="adm-gate-sub">Admin access required</p>
        <form onSubmit={submit} className="adm-gate-form">
          <input
            ref={ref}
            type="password"
            value={val}
            onChange={e => { setVal(e.target.value); setErr(""); }}
            placeholder="Enter admin key"
            className={`adm-gate-input${err ? " adm-gate-input--err" : ""}`}
            autoComplete="current-password"
          />
          {err && <p className="adm-gate-err">{err}</p>}
          <button type="submit" className="adm-gate-btn">Continue</button>
        </form>
      </div>
    </div>
  );
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, accent, large,
}: {
  label: string; value: string | number; sub?: string; accent?: string; large?: boolean;
}) {
  return (
    <div className={`adm-kpi${large ? " adm-kpi--large" : ""}`}
      style={accent ? { "--adm-kpi-accent": accent } as React.CSSProperties : undefined}>
      <span className="adm-kpi-val">{value}</span>
      <span className="adm-kpi-label">{label}</span>
      {sub && <span className="adm-kpi-sub">{sub}</span>}
    </div>
  );
}

// ── Funnel ────────────────────────────────────────────────────────────────────

const FUNNEL_COLORS: Record<string, string> = {
  sent:         "#60A5FA",
  acknowledged: "#A78BFA",
  interview:    "#FBBF24",
  offer:        "#FB923C",
  hired:        "#34D399",
};

function FunnelBar({ stage, maxCount }: { stage: FunnelStage; maxCount: number }) {
  const width = maxCount > 0 ? Math.max(4, (stage.count / maxCount) * 100) : 4;
  const color = FUNNEL_COLORS[stage.status] ?? "#60A5FA";
  return (
    <div className="adm-funnel-row">
      <span className="adm-funnel-label">{stage.label}</span>
      <div className="adm-funnel-track">
        <div
          className="adm-funnel-bar"
          style={{ width: `${width}%`, background: color }}
        />
      </div>
      <span className="adm-funnel-count">{fmt(stage.count)}</span>
      <span className="adm-funnel-pct" style={{ color: stage.pct >= 10 ? color : "#6B7280" }}>
        {stage.pct > 0 ? `${stage.pct}%` : "—"}
      </span>
    </div>
  );
}

// ── Weekly Chart ──────────────────────────────────────────────────────────────

function WeeklyChart({ data }: { data: WeeklyPoint[] }) {
  const maxIntros = Math.max(...data.map(d => d.intros), 1);
  const H = 140;
  const barW = 28;
  const gap  = 12;
  const totalW = data.length * (barW + gap) - gap;

  return (
    <div className="adm-chart-wrap">
      <svg
        width="100%"
        viewBox={`0 0 ${totalW + 16} ${H + 28}`}
        preserveAspectRatio="xMidYMid meet"
        aria-label="Weekly intro trend"
      >
        {data.map((pt, i) => {
          const x        = i * (barW + gap);
          const introH   = (pt.intros / maxIntros) * H;
          const hireH    = (pt.hires  / maxIntros) * H;
          const intrY    = H - introH;
          const hireY    = H - hireH;
          const labelY   = H + 18;

          return (
            <g key={pt.week_start}>
              {/* Intro bar (background) */}
              <rect
                x={x} y={intrY}
                width={barW} height={introH}
                rx={4} fill="#1E3A2F" className="adm-chart-bar"
              />
              {/* Hire overlay */}
              {pt.hires > 0 && (
                <rect
                  x={x} y={hireY}
                  width={barW} height={hireH}
                  rx={4} fill="#34D399"
                />
              )}
              {/* Interview dot */}
              {pt.interviews > 0 && (
                <rect
                  x={x} y={H - (pt.interviews / maxIntros) * H}
                  width={barW} height={3}
                  fill="#FBBF24" opacity={0.8}
                />
              )}
              {/* Week label */}
              <text
                x={x + barW / 2} y={labelY}
                textAnchor="middle"
                fill="#4B5563"
                fontSize="10"
                fontFamily="system-ui, sans-serif"
              >
                {shortWeek(pt.week_start)}
              </text>
              {/* Count on bar */}
              {pt.intros > 0 && (
                <text
                  x={x + barW / 2} y={intrY - 5}
                  textAnchor="middle"
                  fill="#9CA3AF"
                  fontSize="9"
                  fontFamily="system-ui, sans-serif"
                >
                  {pt.intros}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="adm-chart-legend">
        <span className="adm-legend-dot" style={{ background: "#1E3A2F", border: "1px solid #34D399" }} />
        <span className="adm-legend-label">Intros</span>
        <span className="adm-legend-dot" style={{ background: "#34D399" }} />
        <span className="adm-legend-label">Hires</span>
        <span className="adm-legend-dot" style={{ background: "#FBBF24", height: 3, borderRadius: 2 }} />
        <span className="adm-legend-label">Interviews</span>
      </div>
    </div>
  );
}

// ── Stat Pill ─────────────────────────────────────────────────────────────────

function StatPill({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="adm-stat-pill">
      <span className="adm-stat-pill-val" style={color ? { color } : undefined}>{value}</span>
      <span className="adm-stat-pill-label">{label}</span>
    </div>
  );
}

// ── Top Jobs ─────────────────────────────────────────────────────────────────

function TopJobsTable({ jobs }: { jobs: TopJob[] }) {
  if (!jobs.length) {
    return <p className="adm-empty">No roles with intros yet.</p>;
  }
  return (
    <div className="adm-table-wrap">
      <table className="adm-table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Stage</th>
            <th className="adm-th-num">Intros</th>
            <th className="adm-th-num">Hires</th>
            <th className="adm-th-num">Rate</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.job_id} className="adm-tr">
              <td className="adm-td-role">
                <span className="adm-td-title">{j.title}</span>
                <span className="adm-td-company">{j.company}</span>
              </td>
              <td>
                {j.stage
                  ? <span className="adm-stage-pill">{j.stage}</span>
                  : <span className="adm-td-na">—</span>
                }
              </td>
              <td className="adm-td-num">{j.intros}</td>
              <td className="adm-td-num" style={{ color: j.hires > 0 ? "#34D399" : "#6B7280" }}>
                {j.hires}
              </td>
              <td className="adm-td-num">
                <span
                  className="adm-rate-badge"
                  style={{ color: pctColor(j.rate), borderColor: pctColor(j.rate) + "33" }}
                >
                  {j.rate}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Status Breakdown ──────────────────────────────────────────────────────────

function StatusGrid({ by_status }: { by_status: Record<string, number> }) {
  const statuses = [
    { key: "sent",         label: "Awaiting",   color: "#60A5FA" },
    { key: "acknowledged", label: "Interested", color: "#A78BFA" },
    { key: "interview",    label: "Interview",  color: "#FBBF24" },
    { key: "offer",        label: "Offer",      color: "#FB923C" },
    { key: "hired",        label: "Hired",      color: "#34D399" },
    { key: "declined",     label: "Declined",   color: "#6B7280" },
    { key: "ghosted",      label: "Ghosted",    color: "#374151" },
  ];
  return (
    <div className="adm-status-grid">
      {statuses.map(s => (
        <div key={s.key} className="adm-status-cell">
          <span className="adm-status-num" style={{ color: s.color }}>
            {by_status[s.key] ?? 0}
          </span>
          <span className="adm-status-label">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Loading Skeleton ──────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="adm-root">
      <header className="adm-topbar">
        <div className="adm-logo">Mitra<span className="adm-logo-dot">.</span></div>
        <span className="adm-topbar-pill">Admin</span>
      </header>
      <main className="adm-main">
        <div className="adm-kpi-row">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="adm-kpi adm-sk" style={{ height: 96 }} />
          ))}
        </div>
        <div className="adm-grid-2">
          <div className="adm-card adm-sk" style={{ height: 240 }} />
          <div className="adm-card adm-sk" style={{ height: 240 }} />
        </div>
        <div className="adm-card adm-sk" style={{ height: 180 }} />
        <div className="adm-card adm-sk" style={{ height: 220 }} />
      </main>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export function MetricsDashboard() {
  const [key,     setKey]     = useState<string | null>(null);
  const [data,    setData]    = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [ts,      setTs]      = useState("");

  // Restore key from storage
  useEffect(() => {
    const stored = sessionStorage.getItem(KEY_STORAGE);
    if (stored) setKey(stored);
  }, []);

  const fetchMetrics = useCallback(async (adminKey: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/admin/metrics`, {
        headers: { "X-Admin-Key": adminKey },
      });
      if (res.status === 403) {
        sessionStorage.removeItem(KEY_STORAGE);
        setKey(null);
        setError("Invalid admin key.");
        setLoading(false);
        return;
      }
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const json: MetricsData = await res.json();
      setData(json);
      setTs(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleKey = (k: string) => {
    sessionStorage.setItem(KEY_STORAGE, k);
    setKey(k);
    fetchMetrics(k);
  };

  useEffect(() => {
    if (key) fetchMetrics(key);
  }, [key, fetchMetrics]);

  if (!key) return <KeyGate onKey={handleKey} />;
  if (loading && !data) return <Skeleton />;

  if (error && !data) {
    return (
      <div className="adm-gate">
        <div className="adm-gate-card">
          <div className="adm-logo">Mitra<span className="adm-logo-dot">.</span></div>
          <p className="adm-gate-err" style={{ marginTop: 16 }}>{error}</p>
          <button className="adm-gate-btn" style={{ marginTop: 12 }} onClick={() => setKey(null)}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { snapshot, funnel, by_status, weekly_trend, top_jobs,
          response_rate, ghosted_rate,
          avg_days_to_interview, avg_days_to_hire } = data;

  const convRate = funnel.find(f => f.status === "hired")?.pct ?? 0;
  const maxFunnelCount = funnel[0]?.count ?? 1;

  return (
    <div className="adm-root">

      {/* Top bar */}
      <header className="adm-topbar">
        <div className="adm-logo">Mitra<span className="adm-logo-dot">.</span></div>
        <div className="adm-topbar-right">
          {ts && <span className="adm-topbar-ts">Updated {ts}</span>}
          <button
            className="adm-refresh-btn"
            onClick={() => key && fetchMetrics(key)}
            disabled={loading}
            title="Refresh"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"
              style={{ transform: loading ? "rotate(360deg)" : undefined,
                       transition: loading ? "transform 0.6s linear" : undefined }}>
              <path d="M12 7A5 5 0 1 1 2.5 4.5M2 2v3h3" stroke="currentColor"
                strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Refresh
          </button>
          <span className="adm-topbar-pill">Admin</span>
        </div>
      </header>

      <main className="adm-main">

        {/* KPI row */}
        <div className="adm-kpi-row">
          <KpiCard label="Total Intros"    value={fmt(snapshot.total_intros)}    sub={`${snapshot.total_candidates} candidates`} />
          <KpiCard label="Hired"           value={fmt(by_status.hired ?? 0)}     sub="all time" accent="#34D399" large />
          <KpiCard label="Conversion Rate" value={`${convRate}%`}                sub="intro → hire" accent={pctColor(convRate)} />
          <KpiCard label="Active Jobs"     value={fmt(snapshot.active_jobs)}     sub={`of ${snapshot.total_jobs} total`} />
        </div>

        {/* Funnel + Pipeline health */}
        <div className="adm-grid-2">

          <div className="adm-card">
            <h2 className="adm-card-title">Hiring Funnel</h2>
            <div className="adm-funnel">
              {funnel.map(stage => (
                <FunnelBar key={stage.status} stage={stage} maxCount={maxFunnelCount} />
              ))}
            </div>
          </div>

          <div className="adm-card">
            <h2 className="adm-card-title">Pipeline Health</h2>
            <div className="adm-stat-pills">
              <StatPill
                label="Response rate"
                value={`${response_rate}%`}
                color={response_rate >= 30 ? "#34D399" : response_rate >= 15 ? "#FBBF24" : "#EF4444"}
              />
              <StatPill
                label="Ghost rate"
                value={`${ghosted_rate}%`}
                color={ghosted_rate <= 10 ? "#34D399" : ghosted_rate <= 25 ? "#FBBF24" : "#EF4444"}
              />
              <StatPill
                label="Avg to interview"
                value={avg_days_to_interview != null ? `${avg_days_to_interview}d` : "—"}
              />
              <StatPill
                label="Avg to hire"
                value={avg_days_to_hire != null ? `${avg_days_to_hire}d` : "—"}
              />
            </div>

            <div className="adm-divider" />

            <h3 className="adm-card-subtitle">Status breakdown</h3>
            <StatusGrid by_status={by_status} />
          </div>

        </div>

        {/* Weekly trend */}
        <div className="adm-card">
          <h2 className="adm-card-title">Weekly Activity <span className="adm-card-title-muted">— last 8 weeks</span></h2>
          <WeeklyChart data={weekly_trend} />
        </div>

        {/* Top jobs */}
        <div className="adm-card">
          <h2 className="adm-card-title">Top Roles by Volume</h2>
          <TopJobsTable jobs={top_jobs} />
        </div>

        <p className="adm-footer-note">
          Mitra Admin · Data is live from your Postgres database
        </p>

      </main>
    </div>
  );
}
