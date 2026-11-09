#!/usr/bin/env python3
"""Build UNFPA PopIntel Track 1 Climate Pulse product layers (Kenya).

Produces ArcGIS-uploadable GeoJSON + CSV for the official four-piece product:
  1) Climate Risk Layer (hazard from CHIRPS SPI-3)
  2) Population Exposure Engine (WorldPop age-sex)
  3) DIOS Early Signal Layer (article surge + climate modes as SIGNAL, not Y)
  4) Climate-Demographic Risk Score (weighted composite)

Snapshot month = latest month in outputs/kenya_county_scores.csv.
This is product packaging, not an ML evaluation.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from exactextract import exact_extract
from scipy import stats as scipy_stats

# Repo root: climate_pulse_oss_v1/ when packaged; or parent unfpa-dios checkout.
# Prefer local data layout under this package; fall back to sibling unfpa-dios.
_PKG = Path(__file__).resolve().parents[1]
_CANDIDATES = [_PKG, _PKG.parent, Path.cwd()]
ROOT = next((c for c in _CANDIDATES if (c / "data").exists() or (c / "track1_data").exists() or (c / "demo_data").exists()), _PKG)
OUT = ROOT / "outputs" / "climate_pulse_dashboard"
SCORES_CSV = ROOT / "outputs" / "kenya_county_scores.csv"
CHIRPS = ROOT / "data" / "features" / "chirps_adm1_monthly.parquet"
EXPOSURE = ROOT / "data" / "features" / "exposure_adm1_worldpop2020.parquet"
MODES = ROOT / "data" / "features" / "modes_monthly.parquet"
DIOS_INV = ROOT / "downloads" / "dios_articles_KEN_all_topics_inventory.csv"
ADM1_GEO = ROOT / "track1_data" / "geoBoundaries-KEN-ADM1.geojson"
ADM2_GEO = ROOT / "track1_data" / "geoBoundaries-KEN-ADM2.geojson"
WP_TIF = ROOT / "track1_data" / "worldpop" / "ken_ppp_2020_1km_Aggregated_UNadj.tif"

# Composite weights (documented in LAYER_DICTIONARY.md)
W_HAZARD = 0.40
W_EXPOSURE = 0.35
W_SIGNAL = 0.25

# Signal blend: county DIOS surge vs national climate-mode anomaly
W_SIGNAL_DIOS = 0.70
W_SIGNAL_MODES = 0.30


def log(msg: str) -> None:
    print(f"[ClimatePulse] {msg}", flush=True)


def norm_name(s: object) -> str:
    s = str(s).lower().strip()
    for a in ["'", "'", "`", "´"]:
        s = s.replace(a, "")
    s = s.replace("-", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def adm1_key_from_name(s: object) -> str:
    """Stable key matching existing feature tables (lowercase, keep hyphen/apostrophe style)."""
    return str(s).lower().strip()


def clip01(x: np.ndarray | float) -> np.ndarray | float:
    return np.clip(x, 0.0, 100.0)


def compute_spi3(chirps: pd.DataFrame, end_month: str) -> pd.DataFrame:
    """Compute SPI-3 per adm1_key ending at end_month (inclusive 3-month precip sum).

    SPI uses a gamma fit on the historical 3-month totals for the same calendar
    month triplet (standard SPI practice), fitted on all available history.
    """
    df = chirps.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["adm1_key", "date"])
    df["precip_3m"] = (
        df.groupby("adm1_key", sort=False)["precip_mm"]
        .transform(lambda s: s.rolling(3, min_periods=3).sum())
    )
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["cal_month"] = df["date"].dt.month

    end_dt = pd.Timestamp(f"{end_month}-01")
    target_cal = end_dt.month

    rows = []
    for key, g in df.groupby("adm1_key"):
        hist = g[(g["cal_month"] == target_cal) & g["precip_3m"].notna()].copy()
        cur = g[g["month"] == end_month]
        if cur.empty or cur["precip_3m"].isna().all():
            rows.append(
                {
                    "adm1_key": key,
                    "adm1_name": g["adm1_name"].iloc[0],
                    "precip_mm": np.nan,
                    "precip_3m": np.nan,
                    "spi_3": np.nan,
                }
            )
            continue
        cur_row = cur.iloc[-1]
        vals = hist["precip_3m"].astype(float).values
        vals = vals[np.isfinite(vals) & (vals >= 0)]
        x = float(cur_row["precip_3m"])
        if len(vals) < 20 or not np.isfinite(x):
            spi = np.nan
        else:
            # Zero-inflated gamma SPI (McKee-style approximation)
            n = len(vals)
            n_zero = int(np.sum(vals == 0))
            p_zero = n_zero / n
            if x == 0:
                # Mid-point of zero mass
                cdf = p_zero / 2.0
            else:
                pos = vals[vals > 0]
                if len(pos) < 10:
                    # Fallback: empirical rank
                    cdf = float(np.mean(vals <= x))
                else:
                    try:
                        shape, loc, scale = scipy_stats.gamma.fit(pos, floc=0)
                        cdf_pos = float(scipy_stats.gamma.cdf(x, shape, loc=loc, scale=scale))
                        cdf = p_zero + (1.0 - p_zero) * cdf_pos
                    except Exception:
                        cdf = float(np.mean(vals <= x))
            cdf = min(max(cdf, 1e-5), 1.0 - 1e-5)
            spi = float(scipy_stats.norm.ppf(cdf))
        rows.append(
            {
                "adm1_key": key,
                "adm1_name": cur_row["adm1_name"],
                "precip_mm": float(cur_row["precip_mm"]),
                "precip_3m": x,
                "spi_3": spi,
            }
        )
    return pd.DataFrame(rows)


def hazard_from_spi(spi_3: pd.Series) -> pd.Series:
    """Drought-side hazard 0-100: full score at SPI-3 <= -3."""
    stress = np.clip(-spi_3.astype(float), 0.0, 3.0)
    return clip01(100.0 * stress / 3.0)


def exposure_scores(exp: pd.DataFrame) -> pd.DataFrame:
    out = exp.copy()
    out["pop_vulnerable"] = (
        out["pop_children_0_14"].fillna(0)
        + out["pop_women_15_49"].fillna(0)
        + out["pop_older_65"].fillna(0)
    )
    vmax = float(out["pop_vulnerable"].max())
    # log scale so Nairobi does not dominate the entire map
    out["exposure_score"] = clip01(
        100.0 * np.log1p(out["pop_vulnerable"]) / np.log1p(vmax)
    )
    return out


def build_dios_signal(end_month: str, adm1_keys: pd.DataFrame) -> pd.DataFrame:
    """County DIOS article surge as early-signal input (NOT a prediction label).

    signal_dios uses 3-month article count ending at end_month vs prior 24-month
    mean of rolling 3-month counts. Saturated at 3x baseline -> 100.
    """
    inv = pd.read_csv(DIOS_INV)
    inv["dt"] = pd.to_datetime(inv["publication_date"], errors="coerce")
    inv = inv.dropna(subset=["dt"])
    inv["nk"] = inv["adm1_name"].map(norm_name)

    # Map DIOS names onto our adm1 table
    key_map = {norm_name(r.adm1_name): r.adm1_key for r in adm1_keys.itertuples()}
    inv["adm1_key"] = inv["nk"].map(key_map)
    inv = inv.dropna(subset=["adm1_key"])

    end_dt = pd.Timestamp(f"{end_month}-01") + pd.offsets.MonthEnd(0)
    start_3 = (pd.Timestamp(f"{end_month}-01") - pd.DateOffset(months=2)).replace(day=1)

    # Monthly counts per county
    inv["month"] = inv["dt"].dt.strftime("%Y-%m")
    monthly = (
        inv.groupby(["adm1_key", "month"], as_index=False)
        .size()
        .rename(columns={"size": "n_articles"})
    )

    # Build full month index for baseline
    all_months = pd.period_range("2021-01", end_month, freq="M").astype(str)
    keys = adm1_keys["adm1_key"].tolist()
    full = pd.MultiIndex.from_product([keys, all_months], names=["adm1_key", "month"]).to_frame(
        index=False
    )
    monthly = full.merge(monthly, on=["adm1_key", "month"], how="left").fillna({"n_articles": 0})
    monthly = monthly.sort_values(["adm1_key", "month"])
    monthly["n_3m"] = (
        monthly.groupby("adm1_key")["n_articles"]
        .transform(lambda s: s.rolling(3, min_periods=1).sum())
    )

    cur = monthly[monthly["month"] == end_month][["adm1_key", "n_articles", "n_3m"]].copy()
    cur = cur.rename(columns={"n_articles": "dios_n_month", "n_3m": "dios_n_3m"})

    # Baseline: mean of n_3m over prior 24 months (excluding current)
    base_months = set(
        pd.period_range(
            (pd.Timestamp(f"{end_month}-01") - pd.DateOffset(months=24)).strftime("%Y-%m"),
            (pd.Timestamp(f"{end_month}-01") - pd.DateOffset(months=1)).strftime("%Y-%m"),
            freq="M",
        ).astype(str)
    )
    base = (
        monthly[monthly["month"].isin(base_months)]
        .groupby("adm1_key")["n_3m"]
        .mean()
        .rename("dios_baseline_3m")
        .reset_index()
    )
    cur = cur.merge(base, on="adm1_key", how="left")
    cur["dios_baseline_3m"] = cur["dios_baseline_3m"].fillna(0.0)
    cur["dios_ratio"] = cur["dios_n_3m"] / np.maximum(cur["dios_baseline_3m"], 1.0)
    cur["signal_dios"] = clip01(100.0 * np.minimum(cur["dios_ratio"] / 3.0, 1.0))

    # Climate-change topic share in the 3-month window (context field)
    win = inv[(inv["dt"] >= start_3) & (inv["dt"] <= end_dt)].copy()
    if "export_topic" in win.columns:
        win["is_climate"] = win["export_topic"].fillna("").str.contains("climate", case=False) | win[
            "primary_topic"
        ].fillna("").str.contains("climate", case=False)
    else:
        win["is_climate"] = win["primary_topic"].fillna("").str.contains("climate", case=False)
    clim = win.groupby("adm1_key")["is_climate"].sum().rename("dios_n_climate_3m").reset_index()
    cur = cur.merge(clim, on="adm1_key", how="left")
    cur["dios_n_climate_3m"] = cur["dios_n_climate_3m"].fillna(0).astype(int)

    return cur


def modes_component(end_month: str) -> tuple[float, dict]:
    modes = pd.read_parquet(MODES)
    modes["month"] = pd.to_datetime(modes["date"]).dt.strftime("%Y-%m")
    row = modes[modes["month"] == end_month]
    if row.empty:
        return 0.0, {"oni": None, "dmi": None, "oni_seas": None}
    r = row.iloc[0]
    oni = float(r["oni"]) if pd.notna(r["oni"]) else 0.0
    dmi = float(r["dmi"]) if pd.notna(r["dmi"]) else np.nan
    # Magnitude of ENSO anomaly (East Africa drought teleconnection is seasonal;
    # we expose raw ONI/DMI as context and use |ONI| for a national modes score).
    score = float(clip01(100.0 * min(abs(oni) / 2.5, 1.0)))
    ctx = {
        "oni": oni,
        "dmi": None if not np.isfinite(dmi) else dmi,
        "oni_seas": None if pd.isna(r.get("oni_seas")) else str(r["oni_seas"]),
    }
    return score, ctx


def simplify_gdf(gdf: gpd.GeoDataFrame, tol: float = 0.001) -> gpd.GeoDataFrame:
    out = gdf.copy()
    out["geometry"] = out.geometry.simplify(tol, preserve_topology=True)
    return out


def write_geojson(gdf: gpd.GeoDataFrame, path: Path, max_mb: float = 18.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    size_mb = path.stat().st_size / 1e6
    if size_mb > max_mb:
        log(f"{path.name} is {size_mb:.1f}MB > {max_mb}; simplifying...")
        for tol in (0.002, 0.005, 0.01, 0.02):
            sg = simplify_gdf(gdf, tol)
            sg.to_file(path, driver="GeoJSON")
            size_mb = path.stat().st_size / 1e6
            log(f"  tol={tol} -> {size_mb:.2f}MB")
            if size_mb <= max_mb:
                break


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scores = pd.read_csv(SCORES_CSV)
    end_month = str(scores["month"].max())
    log(f"Snapshot month: {end_month}")

    # --- Geography ---
    g1 = gpd.read_file(ADM1_GEO).to_crs(epsg=4326)
    g1["adm1_name"] = g1["shapeName"].astype(str)
    g1["adm1_key"] = g1["adm1_name"].map(adm1_key_from_name)
    g1["nk"] = g1["adm1_name"].map(norm_name)

    g2 = gpd.read_file(ADM2_GEO).to_crs(epsg=4326)
    g2["adm2_name"] = g2["shapeName"].astype(str)
    g2["adm2_key"] = g2["adm2_name"].map(adm1_key_from_name)

    # --- Hazard (SPI-3 from CHIRPS, all 47) ---
    chirps = pd.read_parquet(CHIRPS)
    # Align chirps keys to geo keys via name
    chirps["nk"] = chirps["adm1_name"].map(norm_name)
    name_to_key = {r.nk: r.adm1_key for r in g1[["nk", "adm1_key"]].itertuples()}
    chirps["adm1_key"] = chirps["nk"].map(name_to_key)
    chirps = chirps.dropna(subset=["adm1_key"])
    haz = compute_spi3(chirps, end_month)
    haz["hazard_score"] = hazard_from_spi(haz["spi_3"])
    log(f"Hazard SPI-3 computed for {haz['spi_3'].notna().sum()} / {len(haz)} counties")

    # --- Exposure (WorldPop 2020 age-sex, ADM1) ---
    exp = pd.read_parquet(EXPOSURE)
    exp["nk"] = exp["adm1_name"].map(norm_name)
    exp["adm1_key"] = exp["nk"].map(name_to_key)
    exp = exposure_scores(exp)
    log(f"Exposure rows: {len(exp)}")

    # --- DIOS signal + modes ---
    dios = build_dios_signal(end_month, g1[["adm1_key", "adm1_name"]].drop_duplicates())
    modes_score, modes_ctx = modes_component(end_month)
    log(f"Modes national score={modes_score:.1f} ONI={modes_ctx['oni']} DMI={modes_ctx['dmi']}")

    # Optional legacy contributions from ASAL stress scores
    s_latest = scores[scores["month"] == end_month].copy()
    s_latest["nk"] = s_latest["adm1_name"].map(norm_name)
    s_latest["adm1_key"] = s_latest["nk"].map(name_to_key)
    legacy = s_latest[
        [
            "adm1_key",
            "stress_score_m8_calibrated",
            "rank_month",
            "contribution_hazard",
            "contribution_exposure",
            "contribution_modes",
            "contribution_state",
            "confidence",
            "estimated_affected_pop_u5_women",
        ]
    ].copy()
    legacy = legacy.rename(
        columns={
            "stress_score_m8_calibrated": "stress_score_legacy",
            "rank_month": "rank_legacy",
            "contribution_hazard": "contrib_hazard_legacy",
            "contribution_exposure": "contrib_exposure_legacy",
            "contribution_modes": "contrib_modes_legacy",
            "contribution_state": "contrib_state_legacy",
            "confidence": "confidence_legacy",
            "estimated_affected_pop_u5_women": "est_aff_u5_women_legacy",
        }
    )

    # --- Assemble ADM1 attributes ---
    attrs = g1[["adm1_key", "adm1_name", "nk"]].drop_duplicates().copy()
    attrs = attrs.merge(
        haz[["adm1_key", "precip_mm", "precip_3m", "spi_3", "hazard_score"]],
        on="adm1_key",
        how="left",
    )
    attrs = attrs.merge(
        exp[
            [
                "adm1_key",
                "pop_total",
                "pop_children_0_14",
                "pop_women_15_49",
                "pop_older_65",
                "pop_vulnerable",
                "exposure_score",
                "n_adm2",
            ]
        ],
        on="adm1_key",
        how="left",
    )
    attrs = attrs.merge(dios, on="adm1_key", how="left")
    for c in ["dios_n_month", "dios_n_3m", "dios_baseline_3m", "dios_ratio", "signal_dios", "dios_n_climate_3m"]:
        if c not in attrs.columns:
            attrs[c] = 0.0
        attrs[c] = attrs[c].fillna(0.0)
    attrs = attrs.merge(legacy, on="adm1_key", how="left")

    # Modes component: national |ONI| for all; blend with legacy modes contribution for ASAL
    attrs["modes_score_national"] = modes_score
    max_cm = float(attrs["contrib_modes_legacy"].max()) if attrs["contrib_modes_legacy"].notna().any() else 1.0
    max_cm = max(max_cm, 1e-6)
    local_modes = clip01(100.0 * attrs["contrib_modes_legacy"].fillna(0.0) / max_cm)
    has_legacy_modes = attrs["contrib_modes_legacy"].notna()
    attrs["signal_modes"] = np.where(
        has_legacy_modes,
        0.5 * modes_score + 0.5 * local_modes,
        modes_score,
    )
    attrs["signal_score"] = clip01(
        W_SIGNAL_DIOS * attrs["signal_dios"] + W_SIGNAL_MODES * attrs["signal_modes"]
    )

    attrs["climate_demographic_risk_score"] = clip01(
        W_HAZARD * attrs["hazard_score"].fillna(0)
        + W_EXPOSURE * attrs["exposure_score"].fillna(0)
        + W_SIGNAL * attrs["signal_score"].fillna(0)
    )
    attrs["risk_rank"] = attrs["climate_demographic_risk_score"].rank(
        ascending=False, method="min"
    ).astype(int)
    attrs["month"] = end_month
    attrs["oni"] = modes_ctx["oni"]
    attrs["dmi"] = modes_ctx["dmi"]
    attrs["oni_seas"] = modes_ctx["oni_seas"]
    attrs["layer_notes"] = (
        "Kenya Climate Pulse snapshot; DIOS used as signal not label; "
        "week-scale lead not measured; hazard=drought-side SPI-3"
    )
    attrs["coverage_note"] = np.where(
        attrs["stress_score_legacy"].notna(),
        "full_asal_legacy_plus_national",
        "national_hazard_exposure_signal",
    )
    # Confidence: higher when SPI present + DIOS baseline > 0 + exposure present
    conf = np.full(len(attrs), 0.5)
    conf = np.where(attrs["spi_3"].notna(), conf + 0.2, conf)
    conf = np.where(attrs["pop_total"].notna(), conf + 0.15, conf)
    conf = np.where(attrs["dios_baseline_3m"] > 0, conf + 0.15, conf)
    attrs["confidence"] = np.clip(conf, 0, 1)

    # Driver breakdown (absolute weighted contributions summing to risk score)
    attrs["driver_hazard"] = W_HAZARD * attrs["hazard_score"].fillna(0)
    attrs["driver_exposure"] = W_EXPOSURE * attrs["exposure_score"].fillna(0)
    attrs["driver_signal"] = W_SIGNAL * attrs["signal_score"].fillna(0)

    # Scale legacy stress 0-1-ish to 0-100 for map continuity
    if attrs["stress_score_legacy"].notna().any():
        attrs["stress_score_legacy_0_100"] = clip01(
            100.0 * attrs["stress_score_legacy"].fillna(0)
            / max(float(attrs["stress_score_legacy"].max()), 1e-6)
        )
    else:
        attrs["stress_score_legacy_0_100"] = np.nan

    # Round numerics for ArcGIS friendliness
    float_cols = [
        "precip_mm",
        "precip_3m",
        "spi_3",
        "hazard_score",
        "exposure_score",
        "signal_score",
        "signal_dios",
        "signal_modes",
        "modes_score_national",
        "climate_demographic_risk_score",
        "pop_total",
        "pop_children_0_14",
        "pop_women_15_49",
        "pop_older_65",
        "pop_vulnerable",
        "dios_n_month",
        "dios_n_3m",
        "dios_baseline_3m",
        "dios_ratio",
        "confidence",
        "driver_hazard",
        "driver_exposure",
        "driver_signal",
        "stress_score_legacy",
        "stress_score_legacy_0_100",
        "contrib_hazard_legacy",
        "contrib_exposure_legacy",
        "contrib_modes_legacy",
        "contrib_state_legacy",
        "confidence_legacy",
        "est_aff_u5_women_legacy",
        "oni",
        "dmi",
    ]
    for c in float_cols:
        if c in attrs.columns:
            attrs[c] = pd.to_numeric(attrs[c], errors="coerce").round(4)

    assert len(attrs) == 47, f"Expected 47 ADM1 rows, got {len(attrs)}"

    # --- GeoJSON ADM1 (single combined feature class) ---
    keep_cols = [
        "adm1_key",
        "adm1_name",
        "month",
        "climate_demographic_risk_score",
        "risk_rank",
        "hazard_score",
        "exposure_score",
        "signal_score",
        "signal_dios",
        "signal_modes",
        "spi_3",
        "precip_mm",
        "precip_3m",
        "pop_total",
        "pop_children_0_14",
        "pop_women_15_49",
        "pop_older_65",
        "pop_vulnerable",
        "dios_n_month",
        "dios_n_3m",
        "dios_baseline_3m",
        "dios_ratio",
        "dios_n_climate_3m",
        "oni",
        "dmi",
        "oni_seas",
        "modes_score_national",
        "driver_hazard",
        "driver_exposure",
        "driver_signal",
        "confidence",
        "stress_score_legacy",
        "stress_score_legacy_0_100",
        "rank_legacy",
        "contrib_hazard_legacy",
        "contrib_exposure_legacy",
        "contrib_modes_legacy",
        "est_aff_u5_women_legacy",
        "coverage_note",
        "layer_notes",
    ]
    g1_out = g1[["adm1_key", "geometry"]].merge(attrs[keep_cols], on="adm1_key", how="left")
    # Light simplify for upload headroom
    g1_out = simplify_gdf(g1_out, 0.0008)
    adm1_geo = OUT / "kenya_climate_demographic_risk_adm1.geojson"
    write_geojson(g1_out, adm1_geo)
    attrs[keep_cols].to_csv(OUT / "kenya_climate_demographic_risk_adm1.csv", index=False)
    log(f"ADM1 written: {len(g1_out)} features, {adm1_geo.stat().st_size/1e6:.2f}MB")

    # Also write component-oriented views (same geometry, subset fields) for optional hosting
    for name, cols in {
        "climate_risk_adm1.geojson": [
            "adm1_key",
            "adm1_name",
            "month",
            "hazard_score",
            "spi_3",
            "precip_mm",
            "precip_3m",
            "driver_hazard",
            "layer_notes",
        ],
        "population_exposure_adm1.geojson": [
            "adm1_key",
            "adm1_name",
            "month",
            "exposure_score",
            "pop_total",
            "pop_children_0_14",
            "pop_women_15_49",
            "pop_older_65",
            "pop_vulnerable",
            "driver_exposure",
            "layer_notes",
        ],
        "dios_signal_adm1.geojson": [
            "adm1_key",
            "adm1_name",
            "month",
            "signal_score",
            "signal_dios",
            "signal_modes",
            "dios_n_month",
            "dios_n_3m",
            "dios_baseline_3m",
            "dios_ratio",
            "dios_n_climate_3m",
            "oni",
            "dmi",
            "oni_seas",
            "driver_signal",
            "layer_notes",
        ],
    }.items():
        sub = g1_out[["geometry"] + [c for c in cols if c in g1_out.columns]]
        write_geojson(sub, OUT / name)

    # --- ADM2: parent join + WorldPop zonal + inherit scores ---
    log("Building ADM2 (spatial parent + WorldPop zonal)...")
    cent = g2.copy()
    cent["geometry"] = cent.representative_point()
    joined = gpd.sjoin(
        cent[["adm2_key", "adm2_name", "geometry"]],
        g1[["adm1_key", "adm1_name", "geometry"]],
        how="left",
        predicate="within",
    )
    # Drop index_right; if duplicates (boundaries), keep first
    joined = joined[~joined.index.duplicated(keep="first")]
    parent = joined[["adm2_key", "adm1_key", "adm1_name"]].copy()
    assert parent["adm1_key"].notna().all(), "ADM2 parent join incomplete"

    # Zonal sum WorldPop total
    note_exposure_approx = False
    try:
        zonal = exact_extract(str(WP_TIF), g2, ["sum"], output="pandas")
        g2_pop = g2[["adm2_key", "adm2_name"]].copy()
        g2_pop["pop_total"] = zonal["sum"].astype(float).values
        log(f"ADM2 WorldPop zonal OK; sum={g2_pop['pop_total'].sum():.0f}")
    except Exception as e:
        log(f"WorldPop zonal failed ({e}); falling back to area-share split")
        note_exposure_approx = True
        g2_tmp = g2.copy()
        g2_tmp["area"] = g2_tmp.geometry.to_crs(epsg=3857).area
        g2_tmp = g2_tmp.merge(parent, on="adm2_key", how="left")
        g2_tmp = g2_tmp.merge(
            attrs[["adm1_key", "pop_total"]].rename(columns={"pop_total": "adm1_pop_total"}),
            on="adm1_key",
            how="left",
        )
        g2_tmp["area_share"] = g2_tmp["area"] / g2_tmp.groupby("adm1_key")["area"].transform("sum")
        g2_tmp["pop_total"] = g2_tmp["adm1_pop_total"] * g2_tmp["area_share"]
        g2_pop = g2_tmp[["adm2_key", "adm2_name", "pop_total"]]

    adm2_attrs = parent.merge(g2_pop[["adm2_key", "adm2_name", "pop_total"]], on="adm2_key", how="left")
    # Age-sex: apply parent ADM1 shares to ADM2 total
    shares = attrs[
        [
            "adm1_key",
            "pop_total",
            "pop_children_0_14",
            "pop_women_15_49",
            "pop_older_65",
            "hazard_score",
            "signal_score",
            "signal_dios",
            "signal_modes",
            "spi_3",
            "climate_demographic_risk_score",
            "oni",
            "dmi",
            "oni_seas",
            "month",
            "confidence",
            "layer_notes",
        ]
    ].copy()
    shares = shares.rename(columns={"pop_total": "adm1_pop_total", "climate_demographic_risk_score": "risk_adm1"})
    for c, num in [
        ("share_children", "pop_children_0_14"),
        ("share_women", "pop_women_15_49"),
        ("share_older", "pop_older_65"),
    ]:
        shares[c] = shares[num] / shares["adm1_pop_total"].replace(0, np.nan)

    adm2_attrs = adm2_attrs.merge(shares, on="adm1_key", how="left")
    adm2_attrs["pop_children_0_14"] = adm2_attrs["pop_total"] * adm2_attrs["share_children"]
    adm2_attrs["pop_women_15_49"] = adm2_attrs["pop_total"] * adm2_attrs["share_women"]
    adm2_attrs["pop_older_65"] = adm2_attrs["pop_total"] * adm2_attrs["share_older"]
    adm2_attrs["pop_vulnerable"] = (
        adm2_attrs["pop_children_0_14"].fillna(0)
        + adm2_attrs["pop_women_15_49"].fillna(0)
        + adm2_attrs["pop_older_65"].fillna(0)
    )
    # ADM2 exposure score: log scale vs national ADM2 max vulnerable
    vmax2 = float(adm2_attrs["pop_vulnerable"].max())
    adm2_attrs["exposure_score"] = clip01(
        100.0 * np.log1p(adm2_attrs["pop_vulnerable"]) / np.log1p(max(vmax2, 1.0))
    )
    # Recompute composite at ADM2 with local exposure + inherited hazard/signal
    adm2_attrs["climate_demographic_risk_score"] = clip01(
        W_HAZARD * adm2_attrs["hazard_score"].fillna(0)
        + W_EXPOSURE * adm2_attrs["exposure_score"].fillna(0)
        + W_SIGNAL * adm2_attrs["signal_score"].fillna(0)
    )
    adm2_attrs["risk_rank"] = adm2_attrs["climate_demographic_risk_score"].rank(
        ascending=False, method="min"
    ).astype(int)
    adm2_attrs["driver_hazard"] = W_HAZARD * adm2_attrs["hazard_score"].fillna(0)
    adm2_attrs["driver_exposure"] = W_EXPOSURE * adm2_attrs["exposure_score"].fillna(0)
    adm2_attrs["driver_signal"] = W_SIGNAL * adm2_attrs["signal_score"].fillna(0)
    adm2_attrs["note_exposure_approx"] = bool(note_exposure_approx)
    adm2_attrs["note_hazard_inherited"] = True
    adm2_attrs["note_agesex_from_adm1_share"] = True
    adm2_attrs["layer_notes"] = (
        "ADM2 MVP: hazard/signal inherited from parent ADM1; "
        "pop_total from WorldPop 1km zonal; age-sex via ADM1 shares; "
        "week-scale lead not measured"
    )

    adm2_keep = [
        "adm2_key",
        "adm2_name",
        "adm1_key",
        "adm1_name",
        "month",
        "climate_demographic_risk_score",
        "risk_rank",
        "hazard_score",
        "exposure_score",
        "signal_score",
        "signal_dios",
        "signal_modes",
        "spi_3",
        "pop_total",
        "pop_children_0_14",
        "pop_women_15_49",
        "pop_older_65",
        "pop_vulnerable",
        "driver_hazard",
        "driver_exposure",
        "driver_signal",
        "oni",
        "dmi",
        "oni_seas",
        "confidence",
        "note_exposure_approx",
        "note_hazard_inherited",
        "note_agesex_from_adm1_share",
        "layer_notes",
    ]
    for c in [
        "pop_total",
        "pop_children_0_14",
        "pop_women_15_49",
        "pop_older_65",
        "pop_vulnerable",
        "hazard_score",
        "exposure_score",
        "signal_score",
        "climate_demographic_risk_score",
        "spi_3",
        "driver_hazard",
        "driver_exposure",
        "driver_signal",
        "confidence",
        "oni",
        "dmi",
    ]:
        if c in adm2_attrs.columns:
            adm2_attrs[c] = pd.to_numeric(adm2_attrs[c], errors="coerce").round(4)

    g2_out = g2[["adm2_key", "geometry"]].merge(adm2_attrs[adm2_keep], on="adm2_key", how="left")
    g2_out = simplify_gdf(g2_out, 0.001)
    adm2_geo = OUT / "kenya_climate_demographic_risk_adm2.geojson"
    write_geojson(g2_out, adm2_geo)
    adm2_attrs[adm2_keep].to_csv(OUT / "kenya_climate_demographic_risk_adm2.csv", index=False)
    log(f"ADM2 written: {len(g2_out)} features, {adm2_geo.stat().st_size/1e6:.2f}MB")

    # --- Documentation ---
    formula = {
        "hazard_score": "100 * clip(-spi_3, 0, 3) / 3; spi_3 = SPI of 3-month CHIRPS precip ending snapshot month (gamma+zeros, by calendar month)",
        "exposure_score_adm1": "100 * log1p(pop_children_0_14 + pop_women_15_49 + pop_older_65) / log1p(national_max_vulnerable)",
        "exposure_score_adm2": "same log formula on ADM2 vulnerable pop; pop_total=WorldPop 1km zonal sum; age-sex = ADM2_total * ADM1 age shares",
        "signal_dios": "100 * min((dios_articles_3m / max(baseline_3m_mean_prior_24m, 1)) / 3, 1)",
        "signal_modes": "national: 100 * min(|ONI|/2.5, 1); ASAL with legacy contrib_modes: 0.5*national + 0.5*scaled_local",
        "signal_score": f"{W_SIGNAL_DIOS}*signal_dios + {W_SIGNAL_MODES}*signal_modes",
        "climate_demographic_risk_score": f"{W_HAZARD}*hazard_score + {W_EXPOSURE}*exposure_score + {W_SIGNAL}*signal_score",
        "weights": {"hazard": W_HAZARD, "exposure": W_EXPOSURE, "signal": W_SIGNAL},
    }

    dictionary_md = f"""# Climate Pulse Layer Dictionary (Kenya)

中文说明：本目录是 UNFPA PopIntel Track 1 **Climate Pulse** 官方四件套的可发布图层打包，不是 ML 评估结果。DIOS 仅作**早期信号输入**，不作监督标签。周尺度提前量**未实测**。

## Snapshot

- **Country:** Kenya only
- **Month:** `{end_month}`
- **CRS:** EPSG:4326 (WGS84)
- **ADM1 features:** {len(g1_out)} (geoBoundaries)
- **ADM2 features:** {len(g2_out)} (geoBoundaries)
- **Primary hosted files:** `kenya_climate_demographic_risk_adm1.geojson`, `kenya_climate_demographic_risk_adm2.geojson`

## Official four pieces → fields

| Official piece | Primary fields |
|---|---|
| Climate Risk Layer (Hazard) | `hazard_score`, `spi_3`, `precip_mm`, `precip_3m`, `driver_hazard` |
| Population Exposure Engine | `exposure_score`, `pop_total`, `pop_children_0_14`, `pop_women_15_49`, `pop_older_65`, `pop_vulnerable` |
| DIOS Early Signal Layer | `signal_score`, `signal_dios`, `signal_modes`, `dios_*`, `oni`, `dmi`, `oni_seas` |
| Climate-Demographic Risk Score | `climate_demographic_risk_score`, `risk_rank`, `driver_*` |

## Formulas

- **hazard_score (0–100):** `{formula["hazard_score"]}`
- **exposure_score ADM1:** `{formula["exposure_score_adm1"]}`
- **exposure_score ADM2:** `{formula["exposure_score_adm2"]}`
- **signal_dios:** `{formula["signal_dios"]}`
- **signal_modes:** `{formula["signal_modes"]}`
- **signal_score:** `{formula["signal_score"]}`
- **climate_demographic_risk_score:** `{formula["climate_demographic_risk_score"]}`
- **Weights:** hazard={W_HAZARD}, exposure={W_EXPOSURE}, signal={W_SIGNAL}

## Field list (ADM1 combined)

| Field | Type | Meaning |
|---|---|---|
| adm1_key | str | Lowercase county key |
| adm1_name | str | County name (geoBoundaries) |
| month | str | Snapshot YYYY-MM |
| climate_demographic_risk_score | float 0–100 | Composite risk |
| risk_rank | int | 1 = highest risk |
| hazard_score | float 0–100 | Drought-side SPI-3 stress |
| exposure_score | float 0–100 | Vulnerable population pressure |
| signal_score | float 0–100 | DIOS surge + climate modes |
| spi_3 | float | 3-month Standardized Precipitation Index |
| pop_* | float | WorldPop 2020 UNadj age-sex aggregates |
| dios_n_month / dios_n_3m | float | DIOS article counts (signal) |
| dios_baseline_3m / dios_ratio | float | Baseline and surge ratio |
| oni / dmi / oni_seas | float/str | National climate modes context |
| driver_hazard/exposure/signal | float | Weighted components of composite |
| confidence | float 0–1 | Data completeness heuristic |
| stress_score_legacy* | float | Prior ASAL model score (23 counties) for continuity |
| coverage_note / layer_notes | str | Provenance notes |

## ADM2 caveats (MVP)

- `note_hazard_inherited=true`: hazard and signal inherited from parent ADM1 (CHIRPS/DIOS not yet zonally aggregated to ADM2).
- `note_agesex_from_adm1_share=true`: age-sex pops = ADM2 total × parent ADM1 age shares (WorldPop raster is total population).
- `note_exposure_approx={str(note_exposure_approx).lower()}`: if true, total pop was area-split instead of raster zonal.
- Composite at ADM2 **recomputes** using ADM2 `exposure_score` + inherited hazard/signal.

## What this is NOT

- Not a claim of 2–4 week displacement lead time (week-scale EO/DIOS alignment **not measured**).
- Not an ML leaderboard / NDMA phase predictor.
- DIOS article counts are **media early-signal proxies**, not ground-truth displacement.

## Sources

- CHIRPS v3 monthly ADM1 means (existing `chirps_adm1_monthly.parquet`)
- WorldPop 2020 1km UNadj + existing ADM1 age-sex parquet
- DIOS Kenya article inventory (`dios_articles_KEN_all_topics_inventory.csv`)
- ONI/DMI modes parquet
- geoBoundaries KEN ADM1/ADM2
- Legacy ASAL stress scores from `kenya_county_scores.csv` (optional continuity fields only)
"""

    (OUT / "LAYER_DICTIONARY.md").write_text(dictionary_md, encoding="utf-8")

    manifest = {
        "product": "UNFPA PopIntel Track 1 Climate Pulse — Kenya",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_month": end_month,
        "crs": "EPSG:4326",
        "weights": formula["weights"],
        "formulas": formula,
        "modes_context": modes_ctx,
        "modes_score_national": modes_score,
        "adm1_feature_count": int(len(g1_out)),
        "adm2_feature_count": int(len(g2_out)),
        "adm2_note_exposure_approx": bool(note_exposure_approx),
        "adm2_hazard_inherited": True,
        "week_lead_measured": False,
        "dios_used_as": "signal_input_not_label",
        "inputs": {
            "kenya_county_scores_csv": str(SCORES_CSV),
            "chirps": str(CHIRPS),
            "exposure": str(EXPOSURE),
            "modes": str(MODES),
            "dios_inventory": str(DIOS_INV),
            "adm1_geo": str(ADM1_GEO),
            "adm2_geo": str(ADM2_GEO),
            "worldpop_tif": str(WP_TIF),
        },
        "outputs": {
            p.name: {
                "path": str(p),
                "bytes": p.stat().st_size,
                "mb": round(p.stat().st_size / 1e6, 3),
            }
            for p in sorted(OUT.iterdir())
            if p.is_file()
        },
        "score_summary_adm1": {
            "risk_min": float(attrs["climate_demographic_risk_score"].min()),
            "risk_max": float(attrs["climate_demographic_risk_score"].max()),
            "risk_mean": float(attrs["climate_demographic_risk_score"].mean()),
            "top5": attrs.nlargest(5, "climate_demographic_risk_score")[
                ["adm1_name", "climate_demographic_risk_score", "hazard_score", "exposure_score", "signal_score"]
            ].to_dict(orient="records"),
        },
    }
    # Rewrite outputs after docs exist
    manifest["outputs"] = {
        p.name: {
            "path": str(p),
            "bytes": p.stat().st_size,
            "mb": round(p.stat().st_size / 1e6, 3),
        }
        for p in sorted(OUT.iterdir())
        if p.is_file()
    }
    (OUT / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    # refresh sizes including manifest itself
    manifest["outputs"] = {
        p.name: {
            "path": str(p),
            "bytes": p.stat().st_size,
            "mb": round(p.stat().st_size / 1e6, 3),
        }
        for p in sorted(OUT.iterdir())
        if p.is_file()
    }
    (OUT / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    log("Done.")
    log(f"Top-5 risk: {manifest['score_summary_adm1']['top5']}")


if __name__ == "__main__":
    main()
