# Climate Pulse — PopIntel Track 1 (open-source package)

> **中文摘要：** 本仓是 Xin Jin / Climate Pulse 为 UNFPA PopIntel Hackathon **Track 1** 准备的开源代码与样例 PDP+ 集成页。风险分为原型加权（关联，非因果、非概率）。ArcGIS 看板现为 **Owner-only**，需 Xin Jin 的 Africa GeoPortal 登录。本样例页 **不是** 官方 UNFPA Population Data Portal，也 **未** 写入真实 PDP+。

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
| `docs/METHOD.md` | Prototype weights and claim boundaries |
| `docs/ARCGIS_ITEMS.md` | Live Owner-only ArcGIS URLs |
| `pdp-plus-sample/` | **Unofficial** sample portal page wiring those URLs |
| `demo_data/` | Synthetic stub CSV for smoke tests |
| `examples/` | Small sample score tables (illustrative) |

## Association ≠ causation

Climate-Demographic Risk Score = prototype weighted blend of hazard, exposure, and media/climate-mode **signal**. It is an **association / fusion score**, not a validated probability of displacement, and **not** a proven 2–4 week displacement warning.

## Owner-only ArcGIS note

Deployed dashboards and the Kenya Experience live under Xin Jin’s Africa GeoPortal account with **Owner** sharing. Opening the links typically requires that AGOL login. See `docs/ARCGIS_ITEMS.md`.

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
- Claim of official UNFPA PDP+ hosting or Country pilot activation

## Sample PDP+ page

Open locally:

```text
pdp-plus-sample/index.html
```

(file:// or any static host / GitHub Pages). Banner states this is an **unofficial team demo**.

## License

MIT — Copyright (c) 2026 Xin Jin / Climate Pulse (PopIntel Track 1). See `LICENSE`.

## Citation

Xin Jin. Climate Pulse — PopIntel Track 1 open-source package (prototype). 2026. Official track: https://pdp.unfpa.org/popInthackathon/
