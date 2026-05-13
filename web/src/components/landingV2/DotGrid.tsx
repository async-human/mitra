"use client";

import { useEffect, useRef } from "react";
import type { V2Audience } from "./LandingV2";

const GAP = 30;        // px between dots
const R_BASE = 1.2;    // base dot radius
const GLOW = 120;      // cursor influence radius
const ACCENT = "200,66,26";

export function DotGrid({ audience }: { audience: V2Audience }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dark = audience === "company";
    const base = dark ? "242,237,231" : "14,11,9";

    let raf: number;
    let mx = -9999, my = -9999;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(canvas.offsetWidth * dpr);
      canvas.height = Math.round(canvas.offsetHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (t: number) => {
      const W = canvas.offsetWidth;
      const H = canvas.offsetHeight;
      ctx.clearRect(0, 0, W, H);

      const cols = Math.ceil(W / GAP) + 1;
      const rows = Math.ceil(H / GAP) + 1;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = c * GAP;
          const y = r * GAP;
          const dx = x - mx;
          const dy = y - my;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // Ambient wave — offset per row+col so it ripples diagonally
          const wave = 0.5 + 0.5 * Math.sin(t * 0.0009 + r * 0.55 + c * 0.38);

          let alpha: number;
          let radius = R_BASE;
          let color = base;

          if (dist < GLOW) {
            // Smoothstep so the glow falloff feels soft
            const s = 1 - dist / GLOW;
            const ease = s * s * (3 - 2 * s);
            alpha = dark ? 0.08 + ease * 0.55 : 0.06 + ease * 0.44;
            radius = R_BASE + ease * 3.2;
            color = ease > 0.12 ? ACCENT : base;
          } else {
            alpha = dark
              ? 0.04 + wave * 0.08
              : 0.03 + wave * 0.05;
          }

          ctx.beginPath();
          ctx.arc(x, y, radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${color},${alpha.toFixed(3)})`;
          ctx.fill();
        }
      }

      raf = requestAnimationFrame(draw);
    };

    resize();

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mx = e.clientX - rect.left;
      my = e.clientY - rect.top;
    };
    const onLeave = () => { mx = -9999; my = -9999; };

    window.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
      ro.disconnect();
    };
  }, [audience]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    />
  );
}
