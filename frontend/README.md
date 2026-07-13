# KShield — React Dashboard

The frontend for KShield — a real-time security telemetry dashboard built with React 19, Vite 8, Tailwind CSS v4, and Lucide React.

---

## Stack

| Tool | Version | Role |
|---|---|---|
| React | 19 | UI framework |
| Vite | 8 | Build tool + dev server |
| Tailwind CSS | v4 | Styling (Vite plugin, no config file) |
| Lucide React | 1.x | Icon library |
| TypeScript | 6 | Type safety |

---

## Getting Started

```bash
npm install
npm run dev
```

Open **http://localhost:5173**

```bash
npm run build     # production build → dist/
npm run lint      # oxlint
```

---

## Features

- **Security Dashboard** — live scan list, anomaly list, metric cards
- **Slide-over drawer** — full anomaly detail with syntax-coloured unified diff
- **Rules & Settings** — rule toggles, backend URL config, ignore patterns
- **Light / dark theme** — toggled from sidebar, persisted to `localStorage`
- **Fully responsive** — mobile hamburger sidebar, adaptive panel heights, full-width drawer on small screens

---

## Project Structure

```
src/
├── App.tsx                  # Root layout, theme management, mobile header
├── main.tsx                 # React entry point
├── index.css                # Tailwind v4 import + dark mode variant + scrollbar
├── components/
│   ├── Dashboard.tsx        # Main dashboard with scan list, anomaly list, drawer
│   ├── Settings.tsx         # Rule toggles, backend config, ignore patterns
│   └── Sidebar.tsx          # Navigation, theme toggle, status indicator
└── types/
    └── scan.ts              # TypeScript interfaces for API responses
```

---

## Tailwind v4 Notes

This project uses Tailwind CSS v4 with the Vite plugin — there is **no** `tailwind.config.js`.

```ts
// vite.config.ts
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({ plugins: [tailwindcss(), react()] })
```

```css
/* src/index.css */
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```

Dark mode is class-based. The `dark` class is toggled on `document.documentElement` from `App.tsx`.

When importing types from `.ts` files that only export `interface` declarations, use `import type`:
```ts
import type { ScanResult, Anomaly } from '../types/scan';
```
This is required because Rolldown (Vite 8's bundler) strips type-only exports at build time.

---

## Theme

The theme state lives in `App.tsx` and is written to `localStorage` under the key `kshield-theme`. Default is `dark`.

The sidebar sun/moon button calls `toggleTheme()` which adds or removes the `dark` class on `<html>`.
