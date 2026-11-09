# PDP+ integration sample (layout-inspired)

## Purpose

Official PopIntel language asks that Track 1 tools be **“integrated into PDP+ and country workflows”**
(https://pdp.unfpa.org/popInthackathon/). This folder is an **unofficial** single-page demo that:

1. Mimics the public [Population Data Portal](https://pdp.unfpa.org/#/) shell (header, home, indicator viewer, visualizations).
2. Nests **Climate Pulse** the way real PDP places climate tools — as a **Visualizations / country-workflow module**, not a top-level nav product.
3. Links Owner-only ArcGIS Dashboards & Experience and points at package method docs.

## How Climate Pulse is inserted (matches real PDP pattern)

| Entry | Behavior |
|---|---|
| Top nav | **Only** Indicator viewer · Metadata · Visualizations (no Climate Pulse tab) |
| Home → Demographic Intelligence | Opens `#/climate-pulse` (emerging-narratives-style slot) |
| Home → More resources card | Same module |
| Visualizations grid | **Climate Pulse (PopIntel sample)** card among climate-style tools |
| Indicator viewer (Kenya) | Floating CTA “Open Climate Pulse operational view” |
| Other countries | Softer “Open Climate Pulse (extended demo)” CTA |
| On `#/climate-pulse` | Breadcrumb `Home / Visualizations / Climate Pulse`; Visualizations nav stays active |

## Scope / disclaimer

- **UNOFFICIAL DEMO** — not hosted by UNFPA; not production PDP; no official branding rights claimed.
- Text wordmark only (“Population Data Portal (layout sample)”); no UNFPA logo image files.
- Does not write into real PDP+.
- Does not activate Country pilot.

## Open locally

```text
pdp-plus-sample/index.html
```

Works via `file://` or any static host (GitHub Pages, nginx, etc.). Hash routes:

| Hash | View |
|---|---|
| `#/` | Home (hero, KPIs, resources) |
| `#/viewer` | Indicator viewer shell |
| `#/visualizations` | Visualizations grid (Climate Pulse card) |
| `#/climate-pulse` | Climate Pulse module (in-shell only; not in top nav) |
| `#/metadata` | Stub |

## Mapping to the official clause

| Official phrase | This sample |
|---|---|
| integrated into PDP+ | PDP-like chrome + Climate Pulse nested under Visualizations / country workflow |
| country workflows | Viewer countries KEN (primary) + NGA/MEX/IND CTAs |
| Esri dashboard deployed | Owner-only URLs in Climate Pulse view |
| Code open-sourced | Parent package MIT + scripts/docs |

## Assets

Local PNG previews under `assets/` illustrate Kenya maps when ArcGIS iframes are blocked.
