# Climate Pulse — PopIntel Track 1 (open-source package)

> **中文摘要：** 本仓库是 Climate Pulse（PopIntel Track 1）的开源代码与样例页面。风险分是原型 H×E×S 加权。ArcGIS 条目为 Owner-only（私人 AGOL 账号，需登录）；样例页不是生产环境 PDP+。

## Official track

- Hackathon / Track 1: https://pdp.unfpa.org/popInthackathon/
- Official PDP: https://pdp.unfpa.org/

**Four-month deliverable (official wording):** Climate-Demographic Risk Score at Admin-2, Esri dashboard deployed, Country pilot active, Code open-sourced — tools integrated into PDP+ and country workflows.

## What this package contains

| Path | Purpose |
|---|---|
| `scripts/build_climate_pulse_layers.py` | Kenya Climate Pulse layer builder (H×E×S) |
| `scripts/build_climate_pulse_country.py` | NGA / MEX / IND builders (same weights) |
| `docs/OFFICIAL_ALIGNMENT.md` | Official components vs status (web-verified) |
| `docs/METHOD.md` | Prototype H×E×S weights |
| `docs/ARCGIS_ITEMS.md` | Owner-only ArcGIS URLs |
| `pdp-plus-sample/` | Sample portal page wiring those URLs |
| `demo_data/` | Synthetic stub CSV for smoke tests |
| `examples/` | Small sample score tables |

## Risk score

The Climate-Demographic Risk Score is a prototype weighted blend of hazard, exposure, and a media/climate-mode signal (0.40 / 0.35 / 0.25). Component definitions are in `docs/METHOD.md`.

## ArcGIS items

Deployed dashboards and the Kenya Experience are Owner-only ArcGIS items on a private AGOL account. Opening the links requires that login. URLs: `docs/ARCGIS_ITEMS.md`.

## How to reproduce Kenya layers (high level)

1. Install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Place inputs under a data root that the scripts can find (`data/`, `track1_data/`, or sibling checkout):
   - CHIRPS ADM1 monthly parquet (or IRI NetCDF for other countries)
   - WorldPop 2020 1km UNadj GeoTIFF
   - geoBoundaries KEN ADM1 / ADM2 GeoJSON
   - Optional: DIOS article inventory CSV; climate modes parquet
3. Run: `python scripts/build_climate_pulse_layers.py`
4. Outputs land under `outputs/climate_pulse_dashboard/` when that layout exists.

Public sources (download yourself; not bundled): CHIRPS/IRI, WorldPop, geoBoundaries. DIOS dumps may be restricted — not included.

## What is NOT included

- Secrets, AGOL tokens, vault refs, passwords
- Multi-GB rasters / NetCDF
- Raw restricted DIOS article dumps
- PDP+ production hosting or country-pilot records

## Sample PDP+ page

Open locally:

```text
pdp-plus-sample/index.html
```

Static file (`file://`, GitHub Pages, or any static host). Unofficial demo, not production PDP+.

## License

MIT — Copyright (c) 2026 Climate Pulse PopIntel Track 1 contributors. See `LICENSE`.
