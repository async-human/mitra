/**
 * Quota and access-control helpers — mirrors backend/mitra_api/quota.py.
 * Keep these two files in sync when the whitelist changes.
 */

export const USAGE_WHITELIST = new Set([
  "sharshal499@gmail.com",
  "shindeharshal338@gmail.com",
  "kkrharsh16@gmail.com",
]);

export const PERSONAL_EMAIL_DOMAINS = new Set([
  "gmail.com", "googlemail.com",
  "yahoo.com", "yahoo.in", "yahoo.co.in", "yahoo.co.uk",
  "hotmail.com", "hotmail.in", "hotmail.co.uk",
  "outlook.com", "outlook.in",
  "live.com", "live.in",
  "aol.com",
  "protonmail.com", "proton.me",
  "icloud.com", "me.com", "mac.com",
  "ymail.com",
  "rediffmail.com",
  "zohomail.com",
  "mail.com",
  "inbox.com",
  "gmx.com", "gmx.net",
]);

export function isWhitelisted(email: string): boolean {
  return USAGE_WHITELIST.has(email.trim().toLowerCase());
}

export function isPersonalEmail(email: string): boolean {
  if (!email || !email.includes("@")) return false;
  const domain = email.trim().toLowerCase().split("@")[1];
  return PERSONAL_EMAIL_DOMAINS.has(domain);
}
