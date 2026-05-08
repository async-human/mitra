/**
 * Builds `wa.me` deep-links for the Mitra WhatsApp number.
 *
 * Configure the number via `NEXT_PUBLIC_WHATSAPP_NUMBER` in `.env.local`
 * (digits only, country code included, no `+` or spaces). Production must set
 * a real number — the dev fallback digits only satisfy `next build` when unset.
 */

const PLACEHOLDER_NUMBER = "919999999999";

export function getWhatsAppNumber(): string {
  const raw = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER ?? PLACEHOLDER_NUMBER;
  // Strip everything except digits — `wa.me` only accepts digits.
  return raw.replace(/\D/g, "") || PLACEHOLDER_NUMBER;
}

export function whatsAppUrl(message?: string): string {
  const number = getWhatsAppNumber();
  if (!message) return `https://wa.me/${number}`;
  return `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
}

/**
 * Persona-specific opening messages. These are pre-filled in the WhatsApp
 * compose box when a visitor taps a CTA — so Mitra knows which intent
 * pipeline to route them into without asking again.
 */
export const WA_MESSAGES = {
  candidate:
    "Hi Mitra! I just visited your site — I'm looking for my next role and want to chat.",
  founder:
    "Hi Mitra! I'm a founder and want to list a role. (Site: mitra.work)",
  general: "Hi Mitra! I just visited mitra.work and want to learn more.",
} as const;

export type WaPersona = keyof typeof WA_MESSAGES;

export function whatsAppHrefFor(persona: WaPersona = "general"): string {
  return whatsAppUrl(WA_MESSAGES[persona]);
}
