# Method — Climate-Demographic Risk Score (prototype)

> **Claim boundary:** These are **prototype demonstration weights**, not calibrated probabilities, not causal effects, and not a validated 2–4 week **displacement** warning.

## Composite

```text
climate_demographic_risk_score =
    0.40 * hazard_score
  + 0.35 * exposure_score
  + 0.25 * signal_score
```

All component scores are scaled to approximately 0–100 before blending.

## Hazard (Climate Risk Layer)

- Primary driver: drought-side **SPI-3** from CHIRPS (ADM1 zonal precip → 3-month sum → gamma/normal SPI).
- Hazard mapping (Kenya builder): stress = clip(−SPI-3, 0, 3); hazard = 100 × stress / 3 (full score at SPI-3 ≤ −3).

## Exposure (Population Exposure Engine)

- WorldPop 2020 1km Aggregated UNadj zonal population where available.
- Vulnerable proxy: children 0–14 + women 15–49 + older 65+.
- **Kenya (scientific path):** spatial age-sex where WorldPop age-sex rasters were processed.
- **NGA / MEX / IND (current builders):** national age-sex **shares** × zonal totals (`estimated_age_sex=true`) — **not** a full WorldPop age-sex overlay.

## Signal (DIOS Early Signal Layer — media proxy)

When a DIOS article inventory is present:

```text
signal_score = 0.70 * signal_dios + 0.30 * signal_modes
```

- `signal_dios`: county/ADM1 media surge vs baseline (article counts) — **signal input, never supervised Y**.
- `signal_modes`: national climate-mode anomaly (e.g. ONI/DMI-derived modes score).

When DIOS is absent: modes-only (`dios_available=false`). Topic inventories are never invented (fertility-only stays fertility-only).

## What this is not

| Claim | Status |
|---|---|
| Association / fusion score for ops discussion | Yes (prototype) |
| Validated displacement probability | No |
| Measurable 2–4 week displacement warning P/R | No (no gold Y established) |
| Official UNFPA PDP+ production layer | No |
| Email ~60% precision threshold | Not found on public web (2026-11-09); not used as a hard gate here |

## References in this package

- Scripts: `scripts/build_climate_pulse_layers.py`, `scripts/build_climate_pulse_country.py`
- Alignment: `docs/OFFICIAL_ALIGNMENT.md`
