# Keshara Trichology — Frontend

A complete, fully-interactive single-page frontend for the **Keshara Ayurvedic Trichology** hair health platform.

## Overview

`index.html` is a self-contained mobile-first SPA built with **Tailwind CSS** (CDN), **Google Fonts** (Inter + Playfair Display), and **Material Symbols**. No build step, no dependencies — open the file in any browser and it works.

## Pages (Tab Navigation)

| Tab | Screen | Key Features |
|-----|--------|-------------|
| 🏠 Overview | Customer Dashboard | Greeting card, scalp index score, 5-angle calibration photos, daily protocol tracker with checkable tasks, hydration stepper |
| 🔬 Hair Test | Scalp Triage Assessment | Step 3/6 diagnostic form, selectable concern cards, symptom multi-select pills, sleep/stress/hydration telemetry, 5-angle photo studio preview |
| 📅 Journey | Hair Progress Timeline | 3-milestone protocol arc, side-by-side dermoscopy with zoom slider & zone toggle, weekly compliance calendar, clinical observation journal |
| 🛒 Shop | Botanical Apothecary | Search + category filters, 4 prescribed products with add/remove cart, floating cart bar with live totals |
| 👤 Profile | Clinical Records | Patient identity card, diagnostic vault with PDF report, 5-angle photo thumbnails, trichologist notes, shipment tracker, toggle switches, privacy & consent |

## Design System

Based on the **Botanical Ivory** design language:
- **Primary**: `#00271d` Deep Forest
- **Secondary**: `#426654` Botanical Green  
- **Accent**: `#ffdea8` Champagne Gold
- **Surface**: `#faf9f4` Warm Ivory
- **Typography**: Playfair Display (headings) + Inter (body/labels)

## Running Locally

Just open `index.html` in a browser — no server needed.

```bash
# Or serve with any static file server, e.g.:
npx serve .
```

## Branch

This branch (`frontend`) contains **only** the static frontend prototype.  
Backend API code lives on the `main` branch.

---

*Keshara Trichology OS v3.8.4 · Botanical Ivory Design System*
