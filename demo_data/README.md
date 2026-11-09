# Demo data

`synthetic_adm1_risk_stub.csv` — **synthetic** 5-row ADM1 stub for smoke tests and UI wiring.

It is **not** real geography, not validated risk, and must not be used for decisions.

## Public inputs to rebuild real layers (not bundled)

| Source | Role | Typical URL / note |
|---|---|---|
| CHIRPS / IRI | Precipitation → SPI-3 hazard | IRI Data Library CHIRPS v2p0 |
| WorldPop | Population totals (+ age-sex where available) | worldpop.org 2020 1km Aggregated UNadj |
| geoBoundaries | ADM1 / ADM2 polygons | geoBoundaries.org |
| DIOS article inventories | Early **media** signal (not displacement Y) | UNFPA DIOS exports when licensed |

Large rasters, NetCDF, and restricted DIOS dumps are **excluded** from this repository.
