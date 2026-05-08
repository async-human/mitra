# Mitra — Marketing Site

The production landing page for **Mitra**, India's AI talent agent. Built with [Next.js 15 (App Router)](https://nextjs.org/), TypeScript, and Tailwind CSS v4.

This app is a faithful port of the original `landing_page.html` prototype (one folder up), restructured into typed React Server Components, with proper SEO metadata, font/image optimization, accessibility annotations, and a real production build pipeline.

---

## Stack

| Concern         | Choice                                                  |
| --------------- | ------------------------------------------------------- |
| Framework       | Next.js 15 (App Router, React 19)                       |
| Language        | TypeScript (strict)                                     |
| Styling         | Tailwind CSS v4 + design tokens in `globals.css`        |
| Fonts           | `next/font/google` — Lora (serif) + Plus Jakarta Sans   |
| SEO             | `Metadata` API + JSON-LD `Organization` + `robots.ts` + `sitemap.ts` |
| Animations      | CSS keyframes + IntersectionObserver (`<Reveal>`)       |
| Linter          | ESLint 9 (flat config) via `eslint-config-next`         |

---

## Project structure

```
web/
├── src/
│   ├── app/
│   │   ├── globals.css       # Design tokens + base + section styles
│   │   ├── layout.tsx        # Root layout, fonts, SEO metadata
│   │   ├── page.tsx          # Composes the home page
│   │   ├── robots.ts         # /robots.txt
│   │   └── sitemap.ts        # /sitemap.xml
│   └── components/
│       ├── icons.tsx         # Reusable SVG icon set
│       ├── Logo.tsx
│       ├── Reveal.tsx        # IntersectionObserver scroll-reveal wrapper
│       ├── Nav.tsx
│       ├── Hero.tsx          # Client — audience toggle state
│       ├── HeroScene.tsx     # SVG illustration (server)
│       ├── Marquee.tsx
│       ├── Problem.tsx
│       ├── HowItWorks.tsx
│       ├── Conversation.tsx
│       ├── Stats.tsx
│       ├── Founders.tsx
│       ├── Stories.tsx
│       ├── Pricing.tsx
│       ├── FinalCTA.tsx
│       └── Footer.tsx
├── public/                   # Static assets (drop og-image.png here)
├── eslint.config.mjs
├── next.config.ts
├── postcss.config.mjs
├── tsconfig.json
└── package.json
```

Sections render as **server components** by default for the smallest possible client bundle. Only the parts that genuinely need interactivity are marked `"use client"`:

- `Nav.tsx` — listens to `scroll` for the elevated-shadow effect
- `Hero.tsx` — owns the candidate/founder audience toggle state
- `Reveal.tsx` — IntersectionObserver wrapper used across the page

---

## Getting started

### Prerequisites

- Node.js **20.x or 22.x**
- npm **10+** (or pnpm / yarn / bun — adjust commands accordingly)

### Install

```bash
npm install
```

### Run the dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Production build

```bash
npm run build   # compile to .next/
npm run start   # serve the built app on port 3000
```

### Lint

```bash
npm run lint
```

---

## Configuration

### Environment variables

Copy `.env.example` → `.env.local` and fill in real values:

```env
NEXT_PUBLIC_SITE_URL=https://mitra.work
NEXT_PUBLIC_WHATSAPP_NUMBER=919999999999
```

| Variable                       | Used for                                                   |
| ------------------------------ | ---------------------------------------------------------- |
| `NEXT_PUBLIC_SITE_URL`         | Canonical URLs, OpenGraph URL, sitemap entries, JSON-LD    |
| `NEXT_PUBLIC_WHATSAPP_NUMBER`  | All `Chat with Mitra` / `Start on WhatsApp` / `List a role` CTAs deep-link to `wa.me/<number>` with persona-specific pre-filled messages. **Digits only**, including country code, no `+`/spaces/dashes (e.g. `919999999999` for India). |

Pre-filled messages live in `src/lib/whatsapp.ts` under `WA_MESSAGES` — edit them there if you want different copy per audience.

### Open Graph image

Drop a `1200×630` PNG named `og-image.png` into `public/`. The metadata in `src/app/layout.tsx` already references `/og-image.png` for both OpenGraph and Twitter cards.

### Favicon

Replace `src/app/favicon.ico` with the real Mitra mark when ready. Next.js automatically wires this into the `<link rel="icon">`.

---

## Design tokens

All colors, shadows, and radii live as CSS custom properties at the top of `src/app/globals.css`, then are re-exported into Tailwind v4's `@theme` block so utilities like `bg-sand`, `text-ink`, `text-amber-2`, and `text-teal` work alongside the bespoke component CSS.

```css
:root {
  --sand: #F6F1EA;
  --ink: #1C1917;
  --amber: #C07A28;
  --teal: #1B5E5A;
  /* …etc */
}
```

To rebrand, edit those variables once — every section will follow.

---

## Accessibility

- Decorative SVG illustrations carry `role="img"` + `aria-label`, or `aria-hidden="true"` when purely ornamental.
- The audience toggle uses `role="tablist"` / `role="tab"` with `aria-selected`.
- Reduced-motion users get instant transitions via the `prefers-reduced-motion` media query.
- Heading hierarchy (`h1` → `h2` → component-level titles) is preserved from the original design.

---

## Deployment

The easiest target is **[Vercel](https://vercel.com/)** (made by the Next.js team):

```bash
npx vercel       # one-time link
npx vercel --prod
```

Anywhere else that runs Node 20+ also works:

```bash
npm run build
npm run start    # listens on $PORT or 3000
```

For Docker / self-hosting, enable Next's [`output: "standalone"`](https://nextjs.org/docs/pages/api-reference/next-config-js/output) in `next.config.ts` to get a self-contained `.next/standalone/server.js`.

---

## Roadmap

A few small follow-ups that would make sense:

- [ ] Add a real OG image (`public/og-image.png`)
- [ ] Replace the placeholder favicon with the Mitra mark
- [ ] Wire `Chat with Mitra` and `Start on WhatsApp` buttons to the actual `wa.me/...` link
- [ ] Add Plausible / PostHog / GA4 analytics in `layout.tsx`
- [ ] Add `/blog`, `/stories/[slug]`, `/founders` sub-pages when content is ready
- [ ] Add a contact / "list a role" form route at `/list-a-role` (server action posting to your CRM)

---

## License

Proprietary — © Mitra Labs Pvt. Ltd.
