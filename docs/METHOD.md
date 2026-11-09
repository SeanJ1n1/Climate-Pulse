# Method — Climate-Demographic Risk Score (prototype)

Prototype H×E×S weights. Component scores are scaled to approximately 0–100 before blending. Displacement precision/recall is not in this package (no gold displacement label).

## Composite

```text
climate_demographic_risk_score =
    0.40 * hazard_score
  + 0.35 * exposure_score
  + 0.25 * signal_score
```

## Hazard (Climate Risk Layer)

- Primary driver: drought-side **SPI-3** from CHIRPS (ADM1 zonal precip → 3-month sum → gamma/normal SPI).
- Hazard mapping (Kenya builder): stress = clip(−SPI-3, 0, 3); hazard = 100 × stress / 3 (full score at SPI-3 ≤ −3).

## Exposure (Population Exposure Engine)

- WorldPop 2020 1km Aggregated UNadj zonal population where available.
- Vulnerable proxy: children 0–14 + women 15–49 + older 65+.
- **Kenya (scientific path):** spatial age-sex where WorldPop age-sex rasters were processed.
- **NGA / MEX / IND (current builders):** national age-sex **shares** × zonal totals (`estimated_age_sex=true`). That is not a full WorldPop age-sex overlay.

## Signal (DIOS Early Signal Layer — media proxy)

When a DIOS article inventory is present:

```text
signal_score = 0.70 * signal_dios + 0.30 * signal_modes
```

- `signal_dios`: county/ADM1 media surge vs baseline (article counts). Media-count input, not a supervised label.
- `signal_modes`: national climate-mode anomaly (e.g. ONI/DMI-derived modes score).

When DIOS is absent: modes-only (`dios_available=false`). Topic inventories are not filled in (fertility-only stays fertility-only).

## Scope

| Item | In this package |
|---|---|
| Prototype H×E×S blend for the operational layers | Yes |
| Calibrated displacement probability | No |
| Measured 2–4 week displacement warning (precision/recall) | No — no gold displacement label |
| Official UNFPA PDP+ production layer | No |
| Email ~60% precision threshold | Not on the public track page (checked 2026-11-09); not used as a gate |

## References in this package

- Scripts: `scripts/build_climate_pulse_layers.py`, `scripts/build_climate_pulse_country.py`
- Alignment: `docs/OFFICIAL_ALIGNMENT.md`
