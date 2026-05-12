"use client";

import { useState, useRef, useEffect } from "react";
import { signOutAction } from "./actions";

interface UserMenuProps {
  name: string | null | undefined;
  email: string | null | undefined;
  image: string | null | undefined;
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="11" height="11" viewBox="0 0 11 11" fill="none"
      aria-hidden="true"
      style={{ transition: "transform 0.2s ease", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
    >
      <path d="M1.5 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function UserMenu({ name, email, image }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  return (
    <div className="dash-user-menu" ref={ref}>
      <button
        type="button"
        className="dash-user-menu-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="true"
      >
        {image ? (
          <img src={image} alt={name ?? ""} className="dash-topbar-av" referrerPolicy="no-referrer" />
        ) : (
          <span className="dash-topbar-av dash-topbar-av--fallback">{name?.[0] ?? "U"}</span>
        )}
        <span className="dash-topbar-name">{name}</span>
        <ChevronIcon open={open} />
      </button>

      {open && (
        <div className="dash-user-menu-dropdown" role="menu">
          {email && <p className="dash-user-menu-email">{email}</p>}
          <form action={signOutAction}>
            <button type="submit" className="dash-user-menu-item" role="menuitem">
              Sign out
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
