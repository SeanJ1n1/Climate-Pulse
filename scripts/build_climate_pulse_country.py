#!/usr/bin/env python3
"""Build UNFPA PopIntel Track 1 Climate Pulse product layers for one country.

Mirrors Kenya (scripts/build_climate_pulse_layers.py) for NGA / MEX:
  hazard = SPI-3 from IRI CHIRPS v2p0 ADM1 zonal means
  exposure = WorldPop 2020 1km UNadj zonal + national age-sex shares (estimated)
  signal = when DIOS inventory on disk (incl. fertility-only): 0.7*dios + 0.3*modes;
           else modes-only (dios_available=false)
  composite = 0.4*hazard + 0.35*exposure + 0.25*signal
  DIOS topics are never invented — fertility-only inventories stay fertility-only.

Usage:
  python scripts/build_climate_pulse_country.py NGA
  python scripts/build_climate_pulse_country.py MEX
  python scripts/build_climate_pulse_country.py IND
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from exactextract import exact_extract
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from scipy import stats as scipy_stats

# Repo root: climate_pulse_oss_v1/ when packaged; or parent unfpa-dios checkout.
# Prefer local data layout under this package; fall back to sibling unfpa-dios.
_PKG = Path(__file__).resolve().parents[1]
_CANDIDATES = [_PKG, _PKG.parent, Path.cwd()]
ROOT = next((c for c in _CANDIDATES if (c / "data").exists() or (c / "track1_data").exists() or (c / "demo_data").exists()), _PKG)
FEAT = ROOT / "data" / "features"
IRI_DIR = FEAT / "chirps_iri"
MODES = FEAT / "modes_monthly.parquet"
SHARES = FEAT / "agesex_shares" / "national_agesex_shares_2020.json"

W_HAZARD = 0.40
W_EXPOSURE = 0.35
W_SIGNAL = 0.25

# Signal blend when DIOS inventory present (Kenya continuity)
W_SIGNAL_DIOS = 0.70
W_SIGNAL_MODES = 0.30

# Common DIOS location label → geoBoundaries ADM1 name
DIOS_ADM1_ALIASES = {
    "federal capital territory": "Abuja Federal Capital Territory",
    "fct": "Abuja Federal Capital Territory",
    "abuja": "Abuja Federal Capital Territory",
    "ciudad de mexico": "Distrito Federal",
    "ciudad de méxico": "Distrito Federal",
    "cdmx": "Distrito Federal",
    "mexico city": "Distrito Federal",
    "estado de mexico": "México",
    "estado de méxico": "México",
}

COUNTRY = {
    "NGA": {
        "name": "Nigeria",
        "slug": "nigeria",
        "iso2": "NG",
        "out": ROOT / "outputs" / "climate_pulse_dashboard_nga",
        "adm1": ROOT / "track1_data" / "geoBoundaries-NGA-ADM1.geojson",
        "adm2": ROOT / "track1_data" / "geoBoundaries-NGA-ADM2.geojson",
        "wp": ROOT / "track1_data" / "worldpop" / "nga_ppp_2020_1km_Aggregated_UNadj.tif",
        "chirps_hist": IRI_DIR / "chirps_v2_nga_1991_2020.nc",
        "chirps_recent": IRI_DIR / "chirps_v2_nga_2015_2026.nc",
        "chirps_parquet": FEAT / "chirps_adm1_monthly_nga.parquet",
        "expected_adm1": 37,
        "simplify_adm1": 0.001,
        "simplify_adm2": 0.003,
        "max_mb_adm1": 18.0,
        "max_mb_adm2": 25.0,
    },
    "MEX": {
        "name": "Mexico",
        "slug": "mexico",
        "iso2": "MX",
        "out": ROOT / "outputs" / "climate_pulse_dashboard_mex",
        "adm1": ROOT / "track1_data" / "geoBoundaries-MEX-ADM1.geojson",
        "adm2": ROOT / "track1_data" / "geoBoundaries-MEX-ADM2.geojson",
        "wp": ROOT / "track1_data" / "worldpop" / "mex_ppp_2020_1km_Aggregated_UNadj.tif",
        "chirps_hist": IRI_DIR / "chirps_v2_mex_1991_2020.nc",
        "chirps_recent": IRI_DIR / "chirps_v2_mex_2015_2026.nc",
        "chirps_parquet": FEAT / "chirps_adm1_monthly_mex.parquet",
        "expected_adm1": 32,
        "simplify_adm1": 0.002,
        "simplify_adm2": 0.008,
        "max_mb_adm1": 18.0,
        "max_mb_adm2": 30.0,
    },
    "IND": {
        "name": "India",
        "slug": "india",
        "iso2": "IN",
        "out": ROOT / "outputs" / "climate_pulse_dashboard_ind",
        "adm1": ROOT / "track1_data" / "geoBoundaries-IND-ADM1.geojson",
        "adm2": ROOT / "track1_data" / "geoBoundaries-IND-ADM2.geojson",
        "wp": ROOT / "track1_data" / "worldpop" / "ind_ppp_2020_1km_Aggregated_UNadj.tif",
        # No 1991-2020 IRI subset on disk yet (download timed out); SPI uses available
        # 2015-2026 history with documented short reference (see PRODUCT_STATUS).
        "chirps_hist": ROOT / "data" / "features" / "chirps_iri_india" / "chirps_india_2015_2026.nc",
        "chirps_recent": ROOT / "data" / "features" / "chirps_iri_india" / "chirps_india_2015_2026.nc",
        "chirps_parquet": FEAT / "chirps_adm1_monthly_ind.parquet",
        "expected_adm1": 36,
        "simplify_adm1": 0.003,
        "simplify_adm2": 0.01,
        "max_mb_adm1": 18.0,
        "max_mb_adm2": 35.0,
        "spi_ref_note": "SPI-3 reference uses available CHIRPS months in 2015-2026 (prefer calendar-month subset overlapping 2015-2020); full 1991-2020 IRI hist not on disk.",
    },
}


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


def adm_key(s: object) -> str:
    return str(s).lower().strip()


def fix_mojibake(s: object) -> str:
    """Repair UTF-8 text that was mis-decoded as Latin-1 (common in some geoBoundaries dumps)."""
    if s is None:
        return s
    s = str(s)
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin1").decode("utf-8")
        except Exception:
            return s
    return s


def clip01(x):
    return np.clip(x, 0.0, 100.0)


def months_since_1960_to_timestamp(tvals):
    out = []
    for t in np.asarray(tvals, dtype=float):
        months = int(round(float(t)))
        y = 1960 + (months // 12)
        m = 1 + (months % 12)
        out.append(pd.Timestamp(year=y, month=m, day=1))
    return out


def load_nc(path: Path):
    ds = xr.open_dataset(path, decode_times=False)
    v = "precipitation" if "precipitation" in ds else list(ds.data_vars)[0]
    da = ds[v]
    t = months_since_1960_to_timestamp(da["T"].values)
    x = np.asarray(da["X"].values, dtype=float)
    y = np.asarray(da["Y"].values, dtype=float)
    data = np.asarray(da.values, dtype=float)
    dims = list(da.dims)
    log(f"NC {path.name} dims={dims} shape={data.shape} {t[0].date()}..{t[-1].date()}")
    if dims == ["T", "Y", "X"]:
        pass
    elif dims == ["T", "X", "Y"]:
        data = np.transpose(data, (0, 2, 1))
    else:
        order = [dims.index("T"), dims.index("Y"), dims.index("X")]
        data = np.transpose(data, order)
    ds.close()
    return data, t, x, y


def build_masks(gdf, x, y):
    x = np.asarray(x)
    y = np.asarray(y)
    dx = float(np.abs(np.diff(x).mean()))
    dy = float(np.abs(np.diff(y).mean()))
    transform = from_origin(x.min() - dx / 2, y.max() + dy / 2, dx, dy)
    height, width = len(y), len(x)
    flip_y = y[0] < y[-1]
    masks = {}
    for _, feat in gdf.iterrows():
        m = geometry_mask(
            [feat.geometry], transform=transform, invert=True, out_shape=(height, width)
        )
        if flip_y:
            m = m[::-1, :]
        masks[feat.adm1_key] = (feat.adm1_name, m)
    return masks


def zonal_series(data, times, masks):
    rows = []
    for ti, ts in enumerate(times):
        arr = data[ti]
        for key, (name, m) in masks.items():
            vals = arr[m]
            vals = vals[np.isfinite(vals)]
            vals = vals[vals > -9000]
            val = float(np.mean(vals)) if len(vals) else np.nan
            rows.append({"adm1_key": key, "adm1_name": name, "date": ts, "precip_mm": val})
        if (ti + 1) % 60 == 0:
            log(f"  zonal months {ti+1}/{len(times)}")
    return pd.DataFrame(rows)


def build_chirps_adm1(cfg: dict, g1: gpd.GeoDataFrame) -> pd.DataFrame:
    out_pq = cfg["chirps_parquet"]
    if out_pq.exists():
        df = pd.read_parquet(out_pq)
        log(f"Loaded cached CHIRPS {out_pq.name}: {len(df)} rows, {df['date'].min()}..{df['date'].max()}")
        return df
    frames = []
    seen_nc = set()
    for nc in [cfg["chirps_hist"], cfg["chirps_recent"]]:
        key = str(nc.resolve()) if nc.exists() else str(nc)
        if key in seen_nc:
            log(f"Skip duplicate CHIRPS path {nc.name}")
            continue
        seen_nc.add(key)
        if not nc.exists():
            raise FileNotFoundError(nc)
        data, times, x, y = load_nc(nc)
        masks = build_masks(g1, x, y)
        frames.append(zonal_series(data, times, masks))
        del data
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(["adm1_key", "date"], keep="last").sort_values(["adm1_key", "date"])
    df.to_parquet(out_pq, index=False)
    log(f"Wrote {out_pq}: {len(df)} rows, months={df['date'].nunique()}")
    return df


def compute_spi3(chirps: pd.DataFrame, end_month: str) -> pd.DataFrame:
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
        # SPI reference: prefer 1991-2020 calendar-month history (Kenya policy)
        hist = g[
            (g["cal_month"] == target_cal)
            & g["precip_3m"].notna()
            & (g["date"] >= "1991-01-01")
            & (g["date"] <= "2020-12-31")
        ].copy()
        if len(hist) < 20:
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
        # Prefer climatology excluding the snapshot month itself
        hist_vals = hist[hist["month"] != end_month] if "month" in hist.columns else hist
        if len(hist_vals) < 5:
            hist_vals = hist
        vals = hist_vals["precip_3m"].astype(float).values
        vals = vals[np.isfinite(vals) & (vals >= 0)]
        x = float(cur_row["precip_3m"])
        # Full Kenya path needs >=15; short-history countries (e.g. IND 2015-2026 only)
        # fall back to empirical CDF when 8 <= n < 15 (documented in PRODUCT_STATUS).
        if len(vals) < 8 or not np.isfinite(x):
            spi = np.nan
        else:
            n = len(vals)
            n_zero = int(np.sum(vals == 0))
            p_zero = n_zero / n
            use_empirical = n < 15
            if x == 0:
                cdf = p_zero / 2.0
            else:
                pos = vals[vals > 0]
                if use_empirical or len(pos) < 10:
                    # Weibull plotting position
                    ranks = scipy_stats.rankdata(np.append(vals, x), method="average")
                    cdf = float(ranks[-1] / (n + 1))
                else:
                    try:
                        shape, loc, scale = scipy_stats.gamma.fit(pos, floc=0)
                        cdf_pos = float(scipy_stats.gamma.cdf(x, shape, loc=loc, scale=scale))
                        cdf = p_zero + (1.0 - p_zero) * cdf_pos
                    except Exception:
                        ranks = scipy_stats.rankdata(np.append(vals, x), method="average")
                        cdf = float(ranks[-1] / (n + 1))
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
    stress = np.clip(-spi_3.astype(float), 0.0, 3.0)
    return clip01(100.0 * stress / 3.0)


def modes_component(end_month: str) -> tuple[float, dict]:
    modes = pd.read_parquet(MODES)
    modes["month"] = pd.to_datetime(modes["date"]).dt.strftime("%Y-%m")
    row = modes[modes["month"] == end_month]
    if row.empty:
        # fallback: latest available
        last = modes.dropna(subset=["oni"]).iloc[-1]
        end_month = pd.to_datetime(last["date"]).strftime("%Y-%m")
        row = modes[modes["month"] == end_month]
        log(f"Modes: requested month missing; using {end_month}")
    r = row.iloc[0]
    oni = float(r["oni"]) if pd.notna(r["oni"]) else 0.0
    dmi = float(r["dmi"]) if pd.notna(r.get("dmi")) else np.nan
    score = float(clip01(100.0 * min(abs(oni) / 2.5, 1.0)))
    ctx = {
        "oni": oni,
        "dmi": None if not np.isfinite(dmi) else dmi,
        "oni_seas": None if pd.isna(r.get("oni_seas")) else str(r["oni_seas"]),
        "modes_month_used": end_month,
    }
    return score, ctx


def simplify_gdf(gdf: gpd.GeoDataFrame, tol: float) -> gpd.GeoDataFrame:
    out = gdf.copy()
    out["geometry"] = out.geometry.simplify(tol, preserve_topology=True)
    return out


def write_geojson(gdf: gpd.GeoDataFrame, path: Path, max_mb: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    size_mb = path.stat().st_size / 1e6
    if size_mb > max_mb:
        log(f"{path.name} is {size_mb:.1f}MB > {max_mb}; simplifying...")
        for tol in (0.002, 0.005, 0.01, 0.02, 0.04, 0.08):
            sg = simplify_gdf(gdf, tol)
            sg.to_file(path, driver="GeoJSON")
            size_mb = path.stat().st_size / 1e6
            log(f"  tol={tol} -> {size_mb:.2f}MB")
            if size_mb <= max_mb:
                break


def zonal_pop(tif: Path, gdf: gpd.GeoDataFrame) -> pd.Series:
    zonal = exact_extract(str(tif), gdf, ["sum"], output="pandas")
    return zonal["sum"].astype(float)



def resolve_dios_inventory(iso: str) -> tuple[Path | None, list[str], str]:
    """Find on-disk DIOS article inventory for ISO.

    Prefers all-topics; falls back to fertility-topic / enriched twins.
    Returns (path_or_None, topics_list, coverage_note).
    Never invents topics that are not present in the file.
    """
    downloads = ROOT / "downloads"
    candidates = [
        (downloads / f"dios_articles_{iso}_all_topics_inventory.csv", "all_topics"),
        (downloads / f"dios_articles_{iso}_fertility_topic_inventory.csv", "fertility"),
        (downloads / f"unfpa_dios_{iso.lower()}_fertility_articles_from_global_enriched.csv", "fertility"),
    ]
    for path, kind in candidates:
        if not path.exists() or path.stat().st_size < 100:
            continue
        topics: list[str] = []
        try:
            df = pd.read_csv(path, usecols=lambda c: c in {"export_topic", "primary_topic", "all_topics"})
            if "export_topic" in df.columns and df["export_topic"].notna().any():
                topics = sorted({str(x).strip().lower() for x in df["export_topic"].dropna().unique() if str(x).strip()})
            elif "primary_topic" in df.columns and df["primary_topic"].notna().any():
                topics = sorted({str(x).strip().lower() for x in df["primary_topic"].dropna().unique() if str(x).strip()})
        except Exception:
            topics = ["fertility"] if kind == "fertility" else []
        if not topics and kind == "fertility":
            topics = ["fertility"]
        if kind == "fertility" or topics == ["fertility"]:
            note = (
                f"DIOS inventory on disk is fertility-topic only ({path.name}). "
                "climate-change and other DIOS topics are NOT included yet; "
                "do not invent missing topics."
            )
            topics = ["fertility"]
        else:
            note = f"DIOS inventory on disk: {path.name}; topics detected={topics}."
        return path, topics, note
    return None, [], (
        "DIOS article inventory not on disk. "
        f"Expected e.g. downloads/dios_articles_{iso}_fertility_topic_inventory.csv "
        f"or dios_articles_{iso}_all_topics_inventory.csv."
    )


def build_dios_signal(
    inv_path: Path,
    end_month: str,
    adm1_keys: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """ADM1 DIOS article surge as early-signal input (NOT a prediction label).

    Matches Kenya: 3-month count vs prior 24-month mean of rolling 3m counts;
    saturate at 3x baseline → 100. Dedupes (article_id, adm1_key). Applies
    DIOS_ADM1_ALIASES for common label mismatches (e.g. FCT → Abuja FCT).
    """
    inv = pd.read_csv(inv_path)
    n_rows_raw = len(inv)
    n_unique_articles = int(inv["article_id"].nunique()) if "article_id" in inv.columns else n_rows_raw
    inv["dt"] = pd.to_datetime(inv["publication_date"], errors="coerce")
    inv = inv.dropna(subset=["dt"])

    # Build name → adm1_key map (+ aliases)
    key_map = {norm_name(r.adm1_name): r.adm1_key for r in adm1_keys.itertuples()}
    for alias, target in DIOS_ADM1_ALIASES.items():
        tn = norm_name(target)
        if tn in key_map:
            key_map[norm_name(alias)] = key_map[tn]

    inv["nk"] = inv["adm1_name"].map(norm_name)
    inv["adm1_key"] = inv["nk"].map(key_map)
    inv = inv.dropna(subset=["adm1_key"])
    if "article_id" in inv.columns:
        inv = inv.drop_duplicates(["article_id", "adm1_key"], keep="first")
    n_matched_articles = int(inv["article_id"].nunique()) if "article_id" in inv.columns else len(inv)
    n_matched_adm1 = int(inv["adm1_key"].nunique()) if len(inv) else 0

    end_dt = pd.Timestamp(f"{end_month}-01") + pd.offsets.MonthEnd(0)
    start_3 = (pd.Timestamp(f"{end_month}-01") - pd.DateOffset(months=2)).replace(day=1)

    inv["month"] = inv["dt"].dt.strftime("%Y-%m")
    monthly = (
        inv.groupby(["adm1_key", "month"], as_index=False)
        .size()
        .rename(columns={"size": "n_articles"})
    )

    all_months = pd.period_range("2021-01", end_month, freq="M").astype(str)
    keys = adm1_keys["adm1_key"].tolist()
    full = pd.MultiIndex.from_product([keys, all_months], names=["adm1_key", "month"]).to_frame(
        index=False
    )
    monthly = full.merge(monthly, on=["adm1_key", "month"], how="left").fillna({"n_articles": 0})
    monthly = monthly.sort_values(["adm1_key", "month"])
    monthly["n_3m"] = (
        monthly.groupby("adm1_key")["n_articles"].transform(lambda s: s.rolling(3, min_periods=1).sum())
    )

    cur = monthly[monthly["month"] == end_month][["adm1_key", "n_articles", "n_3m"]].copy()
    cur = cur.rename(columns={"n_articles": "dios_n_month", "n_3m": "dios_n_3m"})

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

    win = inv[(inv["dt"] >= start_3) & (inv["dt"] <= end_dt)].copy()
    if len(win) and "export_topic" in win.columns:
        win["is_climate"] = win["export_topic"].fillna("").str.contains("climate", case=False) | win[
            "primary_topic"
        ].fillna("").str.contains("climate", case=False)
    elif len(win) and "primary_topic" in win.columns:
        win["is_climate"] = win["primary_topic"].fillna("").str.contains("climate", case=False)
    else:
        win["is_climate"] = False
    if len(win):
        clim = win.groupby("adm1_key")["is_climate"].sum().rename("dios_n_climate_3m").reset_index()
        cur = cur.merge(clim, on="adm1_key", how="left")
    else:
        cur["dios_n_climate_3m"] = 0
    cur["dios_n_climate_3m"] = cur["dios_n_climate_3m"].fillna(0).astype(int)

    meta = {
        "inventory_path": str(inv_path),
        "inventory_rows_raw": n_rows_raw,
        "inventory_unique_article_ids": n_unique_articles,
        "matched_unique_article_ids": n_matched_articles,
        "matched_adm1_count": n_matched_adm1,
        "signal_dios_min": float(cur["signal_dios"].min()) if len(cur) else None,
        "signal_dios_max": float(cur["signal_dios"].max()) if len(cur) else None,
        "signal_dios_mean": float(cur["signal_dios"].mean()) if len(cur) else None,
    }
    return cur, meta


def build_preview_html(
    out_dir: Path,
    country_name: str,
    iso: str,
    end_month: str,
    g1_geojson_path: Path,
    top10: pd.DataFrame,
    dios_available: bool,
    blockers: list[str],
) -> Path:
    # Embed ADM1 geojson
    geo = json.loads(g1_geojson_path.read_text(encoding="utf-8"))
    rows_html = "\n".join(
        f"<tr><td>{int(r.risk_rank)}</td><td>{r.adm1_name}</td>"
        f"<td>{r.climate_demographic_risk_score:.1f}</td>"
        f"<td>{r.hazard_score:.1f}</td><td>{r.exposure_score:.1f}</td>"
        f"<td>{r.signal_score:.1f}</td></tr>"
        for r in top10.itertuples()
    )
    blocker_txt = "; ".join(blockers) if blockers else "none"
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Climate Pulse — {country_name} Climate-Demographic Risk Score ({end_month})</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
  :root {{ --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; height:100%; font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--text); }}
  header {{ padding:12px 16px; background:var(--panel); border-bottom:1px solid #334155; display:flex; flex-wrap:wrap; gap:8px 16px; align-items:baseline; justify-content:space-between; }}
  header h1 {{ font-size:1.05rem; margin:0; font-weight:650; }}
  header .sub {{ color:var(--muted); font-size:0.8rem; max-width:780px; line-height:1.35; }}
  #layout {{ display:grid; grid-template-columns:1fr 320px; height:calc(100% - 78px); }}
  @media (max-width:900px) {{ #layout {{ grid-template-columns:1fr; height:auto; }} #map {{ height:55vh; }} }}
  #map {{ width:100%; height:100%; background:#0b1220; }}
  aside {{ overflow:auto; background:var(--panel); border-left:1px solid #334155; padding:12px 14px; font-size:0.82rem; }}
  aside h2 {{ font-size:0.9rem; margin:0 0 8px; }}
  aside p.note {{ color:var(--muted); margin:0 0 12px; line-height:1.4; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.75rem; }}
  th, td {{ padding:4px 5px; text-align:right; border-bottom:1px solid #334155; }}
  th:nth-child(2), td:nth-child(2) {{ text-align:left; }}
  th {{ color:var(--muted); font-weight:600; }}
  .legend {{ background:rgba(15,23,42,.85); padding:8px 10px; border-radius:6px; color:#e2e8f0; font-size:12px; line-height:1.4; }}
  .swatch {{ display:inline-block; width:14px; height:10px; margin-right:4px; vertical-align:middle; border:1px solid #334155; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Climate Pulse — {country_name} ({iso}) · {end_month}</h1>
    <div class="sub">UNFPA PopIntel Track 1 · climate–population risk view (association ≠ causation).
      DIOS available: <b>{"yes" if dios_available else "no (modes-only signal)"}</b>.
      week_lead_measured=false. Not displacement P/R.</div>
  </div>
</header>
<div id="layout">
  <div id="map"></div>
  <aside>
    <h2>Top-10 ADM1 risk</h2>
    <p class="note">Score = 0.4·hazard + 0.35·exposure + 0.25·signal. Blockers: {blocker_txt}</p>
    <table>
      <thead><tr><th>#</th><th>ADM1</th><th>Risk</th><th>Haz</th><th>Exp</th><th>Sig</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </aside>
</div>
<script>
const GEO = {json.dumps(geo, ensure_ascii=False)};
function colorFor(v) {{
  if (v == null || isNaN(v)) return '#334155';
  if (v >= 80) return '#7f1d1d';
  if (v >= 65) return '#b91c1c';
  if (v >= 50) return '#ea580c';
  if (v >= 35) return '#ca8a04';
  return '#16a34a';
}}
const map = L.map('map');
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; OSM &copy; CARTO', maxZoom: 12
}}).addTo(map);
const layer = L.geoJSON(GEO, {{
  style: f => ({{
    color: '#94a3b8', weight: 0.6, fillColor: colorFor(f.properties.climate_demographic_risk_score), fillOpacity: 0.72
  }}),
  onEachFeature: (f, ly) => {{
    const p = f.properties;
    ly.bindPopup(`<b>${{p.adm1_name}}</b><br/>risk=${{(+p.climate_demographic_risk_score).toFixed(1)}}
      <br/>hazard=${{(+p.hazard_score).toFixed(1)}} (SPI-3=${{p.spi_3}})
      <br/>exposure=${{(+p.exposure_score).toFixed(1)}}
      <br/>signal=${{(+p.signal_score).toFixed(1)}}
      <br/>pop_total=${{Math.round(p.pop_total||0).toLocaleString()}}`);
  }}
}}).addTo(map);
map.fitBounds(layer.getBounds(), {{ padding: [12,12] }});
const legend = L.control({{ position: 'bottomleft' }});
legend.onAdd = () => {{
  const d = L.DomUtil.create('div', 'legend');
  d.innerHTML = '<b>Risk score</b><br/>'
    + '<span class="swatch" style="background:#7f1d1d"></span>≥80<br/>'
    + '<span class="swatch" style="background:#b91c1c"></span>65–80<br/>'
    + '<span class="swatch" style="background:#ea580c"></span>50–65<br/>'
    + '<span class="swatch" style="background:#ca8a04"></span>35–50<br/>'
    + '<span class="swatch" style="background:#16a34a"></span>&lt;35';
  return d;
}};
legend.addTo(map);
</script>
</body>
</html>
"""
    path = out_dir / "climate_pulse_preview.html"
    path.write_text(html, encoding="utf-8")
    return path


def build_country(iso: str) -> dict:
    iso = iso.upper()
    if iso not in COUNTRY:
        raise SystemExit(f"Unsupported ISO {iso}; choose from {list(COUNTRY)}")
    cfg = COUNTRY[iso]
    out = cfg["out"]
    out.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []
    shares_all = json.loads(SHARES.read_text(encoding="utf-8"))
    shares = shares_all[iso]

    # --- Geography ---
    g1 = gpd.read_file(cfg["adm1"]).to_crs(epsg=4326)
    g1["adm1_name"] = g1["shapeName"].map(fix_mojibake)
    g1["adm1_key"] = g1["adm1_name"].map(adm_key)
    g1 = g1.drop_duplicates("adm1_key", keep="first").reset_index(drop=True)

    g2 = gpd.read_file(cfg["adm2"]).to_crs(epsg=4326)
    g2["adm2_name"] = g2["shapeName"].map(fix_mojibake)
    g2["adm2_key"] = g2["adm2_name"].map(adm_key)
    # Disambiguate duplicate ADM2 names by appending shapeID suffix
    if g2["adm2_key"].duplicated().any():
        dup = g2["adm2_key"].duplicated(keep=False)
        g2.loc[dup, "adm2_key"] = (
            g2.loc[dup, "adm2_key"] + "_" + g2.loc[dup, "shapeID"].astype(str).str[-8:]
        )
    log(f"{iso} ADM1={len(g1)} ADM2={len(g2)}")

    # --- CHIRPS / snapshot month ---
    chirps = build_chirps_adm1(cfg, g1[["adm1_key", "adm1_name", "geometry"]])
    chirps["date"] = pd.to_datetime(chirps["date"])
    # latest complete month with precip for majority of ADM1
    month_cov = (
        chirps.dropna(subset=["precip_mm"])
        .assign(month=lambda d: d["date"].dt.strftime("%Y-%m"))
        .groupby("month")["adm1_key"]
        .nunique()
    )
    eligible = month_cov[month_cov >= max(1, int(0.8 * len(g1)))].index.tolist()
    end_month = max(eligible) if eligible else chirps["date"].max().strftime("%Y-%m")
    log(f"Snapshot month: {end_month} (ADM1 precip coverage max={int(month_cov.max())}/{len(g1)})")

    haz = compute_spi3(chirps, end_month)
    haz["hazard_score"] = hazard_from_spi(haz["spi_3"])
    log(f"Hazard SPI-3 non-null: {haz['spi_3'].notna().sum()}/{len(haz)}")
    if haz["spi_3"].isna().all():
        blockers.append("SPI-3 all-NaN; hazard_score set to 0")
    if cfg.get("spi_ref_note"):
        log(f"SPI ref note: {cfg['spi_ref_note']}")
        blockers.append(f"SPI_REF_SHORT: {cfg['spi_ref_note']}")

    # --- Exposure ---
    note_exposure_approx = False
    estimated_age_sex = True
    if not cfg["wp"].exists():
        blockers.append(f"WorldPop missing: {cfg['wp']}")
        g1_pop = g1[["adm1_key", "adm1_name"]].copy()
        g1_pop["pop_total"] = np.nan
        note_exposure_approx = True
    else:
        try:
            pops = zonal_pop(cfg["wp"], g1)
            g1_pop = g1[["adm1_key", "adm1_name"]].copy()
            g1_pop["pop_total"] = pops.values
            log(f"ADM1 WorldPop zonal sum={g1_pop['pop_total'].sum():.0f}")
        except Exception as e:
            blockers.append(f"ADM1 WorldPop zonal failed: {e}")
            note_exposure_approx = True
            g1_pop = g1[["adm1_key", "adm1_name"]].copy()
            g1_pop["pop_total"] = np.nan

    sc = float(shares["share_children_0_14"] or 0)
    sw = float(shares["share_women_15_49"] or 0)
    so = float(shares["share_older_65"] or 0)
    g1_pop["pop_children_0_14"] = g1_pop["pop_total"] * sc
    g1_pop["pop_women_15_49"] = g1_pop["pop_total"] * sw
    g1_pop["pop_older_65"] = g1_pop["pop_total"] * so
    g1_pop["pop_vulnerable"] = (
        g1_pop["pop_children_0_14"].fillna(0)
        + g1_pop["pop_women_15_49"].fillna(0)
        + g1_pop["pop_older_65"].fillna(0)
    )
    vmax = float(g1_pop["pop_vulnerable"].max()) if g1_pop["pop_vulnerable"].notna().any() else 1.0
    vmax = max(vmax, 1.0)
    g1_pop["exposure_score"] = clip01(100.0 * np.log1p(g1_pop["pop_vulnerable"]) / np.log1p(vmax))
    g1_pop["estimated_age_sex"] = True
    g1_pop["n_adm2"] = None  # filled later

    # --- Signal (DIOS inventory if present, else modes-only) ---
    modes_score, modes_ctx = modes_component(end_month)
    log(f"Modes national score={modes_score:.1f} ONI={modes_ctx['oni']} DMI={modes_ctx['dmi']}")

    dios_path, dios_topics, dios_coverage_note = resolve_dios_inventory(iso)
    dios_meta: dict = {
        "inventory_path": None,
        "inventory_rows_raw": 0,
        "inventory_unique_article_ids": 0,
        "matched_unique_article_ids": 0,
        "matched_adm1_count": 0,
        "signal_dios_min": None,
        "signal_dios_max": None,
        "signal_dios_mean": None,
    }
    dios_df = None
    if dios_path is not None:
        dios_available = True
        dios_df, dios_meta = build_dios_signal(
            dios_path, end_month, g1[["adm1_key", "adm1_name"]].drop_duplicates()
        )
        log(
            f"DIOS inventory={dios_path.name} topics={dios_topics} "
            f"unique_articles={dios_meta['inventory_unique_article_ids']} "
            f"matched_articles={dios_meta['matched_unique_article_ids']} "
            f"matched_adm1={dios_meta['matched_adm1_count']} "
            f"signal_dios range="
            f"{dios_meta['signal_dios_min']:.2f}..{dios_meta['signal_dios_max']:.2f}"
        )
    else:
        dios_available = False
        dios_topics = []
        log(f"DIOS absent for {iso}: {dios_coverage_note}")

    attrs = g1[["adm1_key", "adm1_name"]].drop_duplicates().copy()
    attrs = attrs.merge(
        haz[["adm1_key", "precip_mm", "precip_3m", "spi_3", "hazard_score"]],
        on="adm1_key",
        how="left",
    )
    attrs = attrs.merge(g1_pop, on=["adm1_key", "adm1_name"], how="left")
    attrs["dios_available"] = bool(dios_available)
    attrs["modes_score_national"] = modes_score
    attrs["signal_modes"] = modes_score
    if dios_available and dios_df is not None:
        attrs = attrs.merge(dios_df, on="adm1_key", how="left")
        for c in ["dios_n_month", "dios_n_3m", "dios_baseline_3m", "dios_ratio", "signal_dios"]:
            attrs[c] = attrs[c].fillna(0.0)
        attrs["dios_n_climate_3m"] = attrs["dios_n_climate_3m"].fillna(0).astype(int)
        attrs["signal_score"] = clip01(
            W_SIGNAL_DIOS * attrs["signal_dios"] + W_SIGNAL_MODES * attrs["signal_modes"]
        )
        signal_note = (
            f"DIOS present topics={dios_topics}; blend "
            f"{W_SIGNAL_DIOS}*signal_dios+{W_SIGNAL_MODES}*signal_modes; "
            f"{dios_coverage_note}"
        )
    else:
        attrs["signal_dios"] = 0.0
        attrs["dios_n_month"] = 0.0
        attrs["dios_n_3m"] = 0.0
        attrs["dios_baseline_3m"] = 0.0
        attrs["dios_ratio"] = 0.0
        attrs["dios_n_climate_3m"] = 0
        attrs["signal_score"] = modes_score  # 100% modes when DIOS absent
        signal_note = "DIOS absent → signal=modes only"

    signal_score_before_blend = float(modes_score)  # modes-only baseline for reporting
    signal_score_after_min = float(attrs["signal_score"].min())
    signal_score_after_max = float(attrs["signal_score"].max())
    signal_score_after_mean = float(attrs["signal_score"].mean())

    attrs["climate_demographic_risk_score"] = clip01(
        W_HAZARD * attrs["hazard_score"].fillna(0)
        + W_EXPOSURE * attrs["exposure_score"].fillna(0)
        + W_SIGNAL * attrs["signal_score"].fillna(0)
    )
    attrs["risk_rank"] = (
        attrs["climate_demographic_risk_score"].rank(ascending=False, method="min").astype(int)
    )
    attrs["month"] = end_month
    attrs["oni"] = modes_ctx["oni"]
    attrs["dmi"] = modes_ctx["dmi"]
    attrs["oni_seas"] = modes_ctx["oni_seas"]
    attrs["week_lead_measured"] = False
    attrs["hazard_inherited"] = False
    attrs["layer_notes"] = (
        f"{cfg['name']} Climate Pulse snapshot; {signal_note}; "
        "week-scale lead not measured; hazard=drought-side SPI-3; "
        "age-sex from national WB shares (estimated_age_sex=true); "
        "association≠causation; not displacement P/R"
    )
    conf = np.full(len(attrs), 0.45)
    conf = np.where(attrs["spi_3"].notna(), conf + 0.25, conf)
    conf = np.where(attrs["pop_total"].notna(), conf + 0.2, conf)
    if dios_available:
        conf = np.where(attrs["dios_baseline_3m"] > 0, conf + 0.15, conf)
    attrs["confidence"] = np.clip(conf, 0, 1)
    attrs["driver_hazard"] = W_HAZARD * attrs["hazard_score"].fillna(0)
    attrs["driver_exposure"] = W_EXPOSURE * attrs["exposure_score"].fillna(0)
    attrs["driver_signal"] = W_SIGNAL * attrs["signal_score"].fillna(0)

    float_cols = [
        "precip_mm", "precip_3m", "spi_3", "hazard_score", "exposure_score", "signal_score",
        "signal_dios", "signal_modes", "modes_score_national", "climate_demographic_risk_score",
        "pop_total", "pop_children_0_14", "pop_women_15_49", "pop_older_65", "pop_vulnerable",
        "dios_n_month", "dios_n_3m", "dios_baseline_3m", "dios_ratio", "confidence",
        "driver_hazard", "driver_exposure", "driver_signal", "oni", "dmi",
    ]
    for c in float_cols:
        if c in attrs.columns:
            attrs[c] = pd.to_numeric(attrs[c], errors="coerce").round(4)

    if cfg["expected_adm1"] and len(attrs) != cfg["expected_adm1"]:
        log(f"WARN expected ADM1={cfg['expected_adm1']} got {len(attrs)}")

    keep_cols = [
        "adm1_key", "adm1_name", "month", "climate_demographic_risk_score", "risk_rank",
        "hazard_score", "exposure_score", "signal_score", "signal_dios", "signal_modes",
        "spi_3", "precip_mm", "precip_3m", "pop_total", "pop_children_0_14", "pop_women_15_49",
        "pop_older_65", "pop_vulnerable", "estimated_age_sex", "dios_available",
        "dios_n_month", "dios_n_3m", "dios_baseline_3m", "dios_ratio", "dios_n_climate_3m",
        "oni", "dmi", "oni_seas", "modes_score_national", "driver_hazard", "driver_exposure",
        "driver_signal", "confidence", "week_lead_measured", "hazard_inherited", "layer_notes",
    ]
    g1_out = g1[["adm1_key", "geometry"]].merge(attrs[keep_cols], on="adm1_key", how="left")
    g1_out = simplify_gdf(g1_out, cfg["simplify_adm1"])
    slug = cfg["slug"]
    adm1_geo = out / f"{slug}_climate_demographic_risk_adm1.geojson"
    write_geojson(g1_out, adm1_geo, cfg["max_mb_adm1"])
    attrs[keep_cols].to_csv(out / f"{slug}_climate_demographic_risk_adm1.csv", index=False)
    log(f"ADM1 written: {len(g1_out)} features, {adm1_geo.stat().st_size/1e6:.2f}MB")

    # component views
    for name, cols in {
        "climate_risk_adm1.geojson": [
            "adm1_key", "adm1_name", "month", "hazard_score", "spi_3", "precip_mm",
            "precip_3m", "driver_hazard", "hazard_inherited", "layer_notes",
        ],
        "population_exposure_adm1.geojson": [
            "adm1_key", "adm1_name", "month", "exposure_score", "pop_total",
            "pop_children_0_14", "pop_women_15_49", "pop_older_65", "pop_vulnerable",
            "estimated_age_sex", "driver_exposure", "layer_notes",
        ],
        "dios_signal_adm1.geojson": [
            "adm1_key", "adm1_name", "month", "signal_score", "signal_dios", "signal_modes",
            "dios_available", "dios_n_month", "dios_n_3m", "dios_baseline_3m", "dios_ratio",
            "oni", "dmi", "oni_seas", "driver_signal", "layer_notes",
        ],
    }.items():
        sub = g1_out[["geometry"] + [c for c in cols if c in g1_out.columns]]
        write_geojson(sub, out / name, cfg["max_mb_adm1"])

    # --- ADM2 ---
    log("Building ADM2 (spatial parent + WorldPop zonal)...")
    # Pre-simplify ADM2 geometry for memory / upload
    g2_s = simplify_gdf(g2, cfg["simplify_adm2"])
    cent = g2_s.copy()
    cent["geometry"] = cent.representative_point()
    joined = gpd.sjoin(
        cent[["adm2_key", "adm2_name", "geometry"]],
        g1[["adm1_key", "adm1_name", "geometry"]],
        how="left",
        predicate="within",
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    parent = joined[["adm2_key", "adm1_key", "adm1_name"]].copy()
    missing_parent = int(parent["adm1_key"].isna().sum())
    if missing_parent:
        # fallback: nearest ADM1 by distance
        log(f"ADM2 parent within-miss={missing_parent}; filling via nearest")
        miss_idx = parent["adm1_key"].isna()
        miss_keys = parent.loc[miss_idx, "adm2_key"]
        miss_geoms = g2_s.set_index("adm2_key").loc[miss_keys].geometry
        g1_proj = g1.to_crs(epsg=3857)
        for k, geom in miss_geoms.items():
            if geom is None or geom.is_empty:
                continue
            pt = gpd.GeoSeries([geom.representative_point()], crs=4326).to_crs(epsg=3857).iloc[0]
            dist = g1_proj.distance(pt)
            i = int(dist.idxmin())
            parent.loc[parent["adm2_key"] == k, "adm1_key"] = g1.loc[i, "adm1_key"]
            parent.loc[parent["adm2_key"] == k, "adm1_name"] = g1.loc[i, "adm1_name"]

    note_exposure_approx_adm2 = False
    try:
        pops2 = zonal_pop(cfg["wp"], g2_s)
        g2_pop = g2_s[["adm2_key", "adm2_name"]].copy()
        g2_pop["pop_total"] = pops2.values
        log(f"ADM2 WorldPop zonal OK; sum={g2_pop['pop_total'].sum():.0f}")
    except Exception as e:
        log(f"ADM2 WorldPop zonal failed ({e}); area-share split")
        blockers.append(f"ADM2 WorldPop zonal failed: {e}")
        note_exposure_approx_adm2 = True
        g2_tmp = g2_s.copy()
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

    # n_adm2 per parent
    n_adm2 = parent.groupby("adm1_key").size().rename("n_adm2").reset_index()
    attrs = attrs.drop(columns=["n_adm2"], errors="ignore").merge(n_adm2, on="adm1_key", how="left")

    adm2_attrs = parent.merge(g2_pop[["adm2_key", "adm2_name", "pop_total"]], on="adm2_key", how="left")
    shares_df = attrs[
        [
            "adm1_key", "pop_total", "pop_children_0_14", "pop_women_15_49", "pop_older_65",
            "hazard_score", "signal_score", "signal_dios", "signal_modes", "spi_3",
            "climate_demographic_risk_score", "oni", "dmi", "oni_seas", "month", "confidence",
            "dios_available",
        ]
    ].copy()
    shares_df = shares_df.rename(
        columns={"pop_total": "adm1_pop_total", "climate_demographic_risk_score": "risk_adm1"}
    )
    for c, num in [
        ("share_children", "pop_children_0_14"),
        ("share_women", "pop_women_15_49"),
        ("share_older", "pop_older_65"),
    ]:
        shares_df[c] = shares_df[num] / shares_df["adm1_pop_total"].replace(0, np.nan)

    adm2_attrs = adm2_attrs.merge(shares_df, on="adm1_key", how="left")
    adm2_attrs["pop_children_0_14"] = adm2_attrs["pop_total"] * adm2_attrs["share_children"]
    adm2_attrs["pop_women_15_49"] = adm2_attrs["pop_total"] * adm2_attrs["share_women"]
    adm2_attrs["pop_older_65"] = adm2_attrs["pop_total"] * adm2_attrs["share_older"]
    adm2_attrs["pop_vulnerable"] = (
        adm2_attrs["pop_children_0_14"].fillna(0)
        + adm2_attrs["pop_women_15_49"].fillna(0)
        + adm2_attrs["pop_older_65"].fillna(0)
    )
    vmax2 = float(adm2_attrs["pop_vulnerable"].max()) if len(adm2_attrs) else 1.0
    vmax2 = max(vmax2, 1.0)
    adm2_attrs["exposure_score"] = clip01(
        100.0 * np.log1p(adm2_attrs["pop_vulnerable"]) / np.log1p(vmax2)
    )
    adm2_attrs["climate_demographic_risk_score"] = clip01(
        W_HAZARD * adm2_attrs["hazard_score"].fillna(0)
        + W_EXPOSURE * adm2_attrs["exposure_score"].fillna(0)
        + W_SIGNAL * adm2_attrs["signal_score"].fillna(0)
    )
    adm2_attrs["risk_rank"] = (
        adm2_attrs["climate_demographic_risk_score"].rank(ascending=False, method="min").astype(int)
    )
    adm2_attrs["driver_hazard"] = W_HAZARD * adm2_attrs["hazard_score"].fillna(0)
    adm2_attrs["driver_exposure"] = W_EXPOSURE * adm2_attrs["exposure_score"].fillna(0)
    adm2_attrs["driver_signal"] = W_SIGNAL * adm2_attrs["signal_score"].fillna(0)
    adm2_attrs["note_exposure_approx"] = bool(note_exposure_approx_adm2)
    adm2_attrs["hazard_inherited"] = True
    adm2_attrs["note_hazard_inherited"] = True
    adm2_attrs["note_agesex_from_adm1_share"] = True
    adm2_attrs["estimated_age_sex"] = True
    adm2_attrs["week_lead_measured"] = False
    adm2_attrs["layer_notes"] = (
        "ADM2 MVP: hazard/signal inherited from parent ADM1 (hazard_inherited=true); "
        "pop_total from WorldPop 1km zonal when available; age-sex via national→ADM1 shares; "
        "week-scale lead not measured; not displacement P/R"
    )

    adm2_keep = [
        "adm2_key", "adm2_name", "adm1_key", "adm1_name", "month",
        "climate_demographic_risk_score", "risk_rank", "hazard_score", "exposure_score",
        "signal_score", "signal_dios", "signal_modes", "spi_3", "pop_total",
        "pop_children_0_14", "pop_women_15_49", "pop_older_65", "pop_vulnerable",
        "estimated_age_sex", "dios_available", "driver_hazard", "driver_exposure",
        "driver_signal", "oni", "dmi", "oni_seas", "confidence", "note_exposure_approx",
        "note_hazard_inherited", "hazard_inherited", "note_agesex_from_adm1_share",
        "week_lead_measured", "layer_notes",
    ]
    for c in [
        "pop_total", "pop_children_0_14", "pop_women_15_49", "pop_older_65", "pop_vulnerable",
        "hazard_score", "exposure_score", "signal_score", "climate_demographic_risk_score",
        "spi_3", "driver_hazard", "driver_exposure", "driver_signal", "confidence", "oni", "dmi",
    ]:
        if c in adm2_attrs.columns:
            adm2_attrs[c] = pd.to_numeric(adm2_attrs[c], errors="coerce").round(4)

    g2_out = g2_s[["adm2_key", "geometry"]].merge(adm2_attrs[adm2_keep], on="adm2_key", how="left")
    adm2_geo = out / f"{slug}_climate_demographic_risk_adm2.geojson"
    write_geojson(g2_out, adm2_geo, cfg["max_mb_adm2"])
    adm2_attrs[adm2_keep].to_csv(out / f"{slug}_climate_demographic_risk_adm2.csv", index=False)
    log(f"ADM2 written: {len(g2_out)} features, {adm2_geo.stat().st_size/1e6:.2f}MB")

    # TOP10
    top10 = attrs.nsmallest(10, "risk_rank")[
        ["risk_rank", "adm1_name", "climate_demographic_risk_score", "hazard_score",
         "exposure_score", "signal_score", "spi_3", "pop_total"]
    ]
    top10.to_csv(out / f"{slug}_top10_adm1_risk.csv", index=False)
    top10_adm2 = adm2_attrs.nsmallest(10, "risk_rank")[
        ["risk_rank", "adm2_name", "adm1_name", "climate_demographic_risk_score",
         "hazard_score", "exposure_score", "signal_score", "pop_total"]
    ]
    top10_adm2.to_csv(out / f"{slug}_top10_adm2_risk.csv", index=False)

    # Preview
    build_preview_html(
        out, cfg["name"], iso, end_month, adm1_geo, top10, dios_available, blockers
    )

    # DIOS_STATUS.md (replaces DIOS_NEEDED.md)
    old_needed = out / "DIOS_NEEDED.md"
    if old_needed.exists():
        old_needed.unlink()

    if dios_available:
        dios_status = f"""# DIOS_STATUS — {cfg['name']} ({iso})

## Status

- `dios_available=true`
- `dios_topics={dios_topics}`
- Coverage: **{dios_coverage_note}**
- Inventory file: `{dios_meta.get('inventory_path')}`
- Inventory unique `article_id`: **{dios_meta.get('inventory_unique_article_ids')}**
  (raw rows {dios_meta.get('inventory_rows_raw')}; ADM1-matched unique articles **{dios_meta.get('matched_unique_article_ids')}** across **{dios_meta.get('matched_adm1_count')}** ADM1s)
- Signal blend (Kenya continuity): `signal_score = {W_SIGNAL_DIOS}*signal_dios + {W_SIGNAL_MODES}*signal_modes`
- `signal_dios` range (ADM1): {dios_meta.get('signal_dios_min')} – {dios_meta.get('signal_dios_max')} (mean {dios_meta.get('signal_dios_mean')})
- Modes-only baseline (national): {signal_score_before_blend:.2f}
- Blended `signal_score` range: {signal_score_after_min:.2f} – {signal_score_after_max:.2f} (mean {signal_score_after_mean:.2f})

## Still missing

- **climate-change** and other DIOS topics are **NOT** in this package yet.
- Do **not** invent topic coverage beyond `{dios_topics}`.
- To upgrade: export all-topics inventory to
  `./downloads/dios_articles_{iso}_all_topics_inventory.csv` and rebuild.

## Do not

- Do not invent ADM1 article counts beyond the inventory.
- Do not treat DIOS as a displacement label / Y.
- Association ≠ causation; `week_lead_measured=false`.
"""
    else:
        dios_status = f"""# DIOS_STATUS — {cfg['name']} ({iso})

## Status

- `dios_available=false`
- `signal_dios=0`
- `signal_score = signal_modes` (national |ONI|/2.5 → 0–100)
- {dios_coverage_note}

## What to export next

1. Open UNFPA DIOS Looker: https://unfpa-looker-web-app-126183358624.us-east1.run.app/dashboard
2. Filter country = **{cfg['name']}** (ISO `{iso}` / `{cfg['iso2']}`).
3. Prefer **all topics**; fertility-only is acceptable interim.
4. Save under `./downloads/dios_articles_{iso}_*_inventory.csv`
5. Re-run `build_climate_pulse_country.py {iso}` → blend `{W_SIGNAL_DIOS}*dios+{W_SIGNAL_MODES}*modes`.

## Do not

- Do not invent ADM1 article counts.
- Do not treat DIOS as a displacement label / Y.
"""
    (out / "DIOS_STATUS.md").write_text(dios_status, encoding="utf-8")

    if dios_available:
        signal_dios_formula = (
            "100 * min((dios_articles_3m / max(baseline_3m_mean_prior_24m, 1)) / 3, 1); "
            f"fertility-topic inventory only ({Path(dios_meta['inventory_path']).name})"
        )
        signal_score_formula = f"{W_SIGNAL_DIOS}*signal_dios + {W_SIGNAL_MODES}*signal_modes"
    else:
        signal_dios_formula = "0 (dios_available=false; see DIOS_STATUS.md)"
        signal_score_formula = "signal_modes only while DIOS absent"

    formula = {
        "hazard_score": "100 * clip(-spi_3, 0, 3) / 3; spi_3 = SPI of 3-month CHIRPS precip ending snapshot month (gamma+zeros, calendar month; ref prefer 1991-2020)",
        "exposure_score_adm1": "100 * log1p(vulnerable) / log1p(national_max_vulnerable); vulnerable=children_0_14+women_15_49+older_65 from WorldPop total × national WB 2020 shares",
        "exposure_score_adm2": "same log formula on ADM2 vulnerable; pop_total=WorldPop 1km zonal; age-sex = ADM2_total * parent ADM1 age shares (which themselves use national shares)",
        "signal_dios": signal_dios_formula,
        "signal_modes": "national: 100 * min(|ONI|/2.5, 1)",
        "signal_score": signal_score_formula,
        "climate_demographic_risk_score": f"{W_HAZARD}*hazard_score + {W_EXPOSURE}*exposure_score + {W_SIGNAL}*signal_score",
        "weights": {"hazard": W_HAZARD, "exposure": W_EXPOSURE, "signal": W_SIGNAL},
        "signal_blend_weights": {"dios": W_SIGNAL_DIOS, "modes": W_SIGNAL_MODES},
    }

    dictionary_md = f"""# Climate Pulse Layer Dictionary ({cfg['name']})

中文说明：本目录是 UNFPA PopIntel Track 1 **Climate Pulse** 可发布图层打包（对齐肯尼亚四件套）。**关联 ≠ 因果**。DIOS 状态见 `DIOS_STATUS.md`（`dios_available={str(dios_available).lower()}`；topics={dios_topics}）。周尺度提前量**未实测**（`week_lead_measured=false`）。**不是**位移 P/R 产品。

## Snapshot

- **Country:** {cfg['name']} ({iso})
- **Month:** `{end_month}`
- **CRS:** EPSG:4326 (WGS84)
- **ADM1 features:** {len(g1_out)} (geoBoundaries)
- **ADM2 features:** {len(g2_out)} (geoBoundaries)
- **Primary files:** `{slug}_climate_demographic_risk_adm1.geojson`, `{slug}_climate_demographic_risk_adm2.geojson`

## Official four pieces → fields

| Official piece | Primary fields |
|---|---|
| Climate Risk Layer (Hazard) | `hazard_score`, `spi_3`, `precip_mm`, `precip_3m`, `driver_hazard` |
| Population Exposure Engine | `exposure_score`, `pop_*`, `estimated_age_sex` |
| DIOS Early Signal Layer | `signal_score`, `signal_dios`, `signal_modes`, `dios_available`, `dios_*`, `oni`, `dmi` |
| Climate-Demographic Risk Score | `climate_demographic_risk_score`, `risk_rank`, `driver_*` |

## Formulas

- **hazard_score:** `{formula['hazard_score']}`
- **exposure_score ADM1:** `{formula['exposure_score_adm1']}`
- **exposure_score ADM2:** `{formula['exposure_score_adm2']}`
- **signal_score:** `{formula['signal_score']}`
- **composite:** `{formula['climate_demographic_risk_score']}`
- **Weights:** hazard={W_HAZARD}, exposure={W_EXPOSURE}, signal={W_SIGNAL}

## ADM2 caveats

- `hazard_inherited=true` / `note_hazard_inherited=true`: hazard & signal from parent ADM1.
- `estimated_age_sex=true` / `note_agesex_from_adm1_share=true`: age-sex not from age-sex rasters.
- `note_exposure_approx={str(note_exposure_approx_adm2).lower()}`

## Sources

- IRI CHIRPS v2p0 monthly (ADM1 zonal)
- WorldPop 2020 1km Aggregated UNadj
- World Bank 2020 age structure (national shares)
- ONI/DMI modes parquet
- geoBoundaries {iso} ADM1/ADM2
- DIOS article inventory (see DIOS_STATUS.md; topics={dios_topics})
"""
    (out / "LAYER_DICTIONARY.md").write_text(dictionary_md, encoding="utf-8")

    status_md = f"""# Climate Pulse 产品状态（{cfg['name']}）

> 对齐肯尼亚 Climate Pulse 四件套本地打包。**本阶段不登录 Esri / Africa GeoPortal**；上传由父代理浏览器完成。

- **快照月：** `{end_month}`
- **范围：** {cfg['name']} ADM1 = **{len(g1_out)}**；ADM2 = **{len(g2_out)}**
- **CRS：** EPSG:4326
- **DIOS：** {"✅ fertility-only" if (dios_available and dios_topics == ["fertility"]) else (("✅ " + ",".join(dios_topics)) if dios_available else "❌ 未到位")} → `dios_available={str(dios_available).lower()}`（见 `DIOS_STATUS.md`）
- **信号：** {"`0.7*signal_dios + 0.3*signal_modes`" if dios_available else "modes-only"}
- **公式：** `risk = 0.4*hazard + 0.35*exposure + 0.25*signal`
- **主张边界：** 气候–人口风险视图；关联≠因果；`week_lead_measured=false`；**不是**位移 P/R

## 文件

| 组件 | 文件 | 状态 |
|---|---|---|
| Hazard | `climate_risk_adm1.geojson` | ✅ |
| Exposure | `population_exposure_adm1.geojson` | ✅（age-sex 为国家份额估计） |
| Signal | `dios_signal_adm1.geojson` | {"✅ fertility DIOS blend" if dios_available else "⚠️ modes-only"} |
| Composite ADM1/ADM2 | `{slug}_climate_demographic_risk_adm*.geojson` + CSV | ✅ |
| Preview | `climate_pulse_preview.html` | ✅ |
| Top10 | `{slug}_top10_adm1_risk.csv`, `{slug}_top10_adm2_risk.csv` | ✅ |

## Blockers

{chr(10).join('- ' + b for b in blockers) if blockers else ('- （无硬阻断；DIOS fertility-only 已接入，见 DIOS_STATUS.md）' if dios_available else '- （无硬阻断；DIOS 缺失已显式标记）')}

## Sanity

| 检查 | 结果 |
|---|---|
| ADM1 n | {len(g1_out)} |
| ADM2 n | {len(g2_out)} |
| risk range ADM1 | {float(attrs['climate_demographic_risk_score'].min()):.2f} – {float(attrs['climate_demographic_risk_score'].max()):.2f} |
| SPI-3 non-null | {int(attrs['spi_3'].notna().sum())}/{len(attrs)} |
| pop_total non-null | {int(attrs['pop_total'].notna().sum())}/{len(attrs)} |
"""
    (out / "PRODUCT_STATUS.md").write_text(status_md, encoding="utf-8")

    manifest = {
        "product": f"UNFPA PopIntel Track 1 Climate Pulse — {cfg['name']}",
        "iso3": iso,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_month": end_month,
        "crs": "EPSG:4326",
        "weights": formula["weights"],
        "formulas": formula,
        "modes_context": modes_ctx,
        "modes_score_national": modes_score,
        "dios_available": bool(dios_available),
        "dios_topics": list(dios_topics),
        "dios_coverage_note": dios_coverage_note,
        "dios_meta": dios_meta,
        "signal_blend": (
            {"dios": W_SIGNAL_DIOS, "modes": W_SIGNAL_MODES}
            if dios_available
            else {"dios": 0.0, "modes": 1.0}
        ),
        "signal_score_modes_only_baseline": signal_score_before_blend,
        "signal_score_after_blend": {
            "min": signal_score_after_min,
            "max": signal_score_after_max,
            "mean": signal_score_after_mean,
        },
        "estimated_age_sex": True,
        "week_lead_measured": False,
        "claim_boundary": "climate_population_risk_view_not_displacement_PR",
        "adm1_feature_count": int(len(g1_out)),
        "adm2_feature_count": int(len(g2_out)),
        "adm2_note_exposure_approx": bool(note_exposure_approx_adm2),
        "adm2_hazard_inherited": True,
        "blockers": blockers,
        "agesex_shares": shares,
        "inputs": {
            "chirps_hist": str(cfg["chirps_hist"]),
            "chirps_recent": str(cfg["chirps_recent"]),
            "chirps_parquet": str(cfg["chirps_parquet"]),
            "modes": str(MODES),
            "adm1_geo": str(cfg["adm1"]),
            "adm2_geo": str(cfg["adm2"]),
            "worldpop_tif": str(cfg["wp"]),
            "agesex_shares": str(SHARES),
            "dios_inventory": dios_meta.get("inventory_path"),
        },
        "score_summary_adm1": {
            "risk_min": float(attrs["climate_demographic_risk_score"].min()),
            "risk_max": float(attrs["climate_demographic_risk_score"].max()),
            "risk_mean": float(attrs["climate_demographic_risk_score"].mean()),
            "hazard_min": float(attrs["hazard_score"].min()),
            "hazard_max": float(attrs["hazard_score"].max()),
            "exposure_min": float(attrs["exposure_score"].min()),
            "exposure_max": float(attrs["exposure_score"].max()),
            "signal_score_min": signal_score_after_min,
            "signal_score_max": signal_score_after_max,
            "signal_score_mean": signal_score_after_mean,
            "signal_modes_national": float(modes_score),
            "top5": attrs.nlargest(5, "climate_demographic_risk_score")[
                ["adm1_name", "climate_demographic_risk_score", "hazard_score", "exposure_score", "signal_score"]
            ].to_dict(orient="records"),
        },
        "outputs": {},
    }
    for _ in range(2):
        manifest["outputs"] = {
            p.name: {"path": str(p), "bytes": p.stat().st_size, "mb": round(p.stat().st_size / 1e6, 3)}
            for p in sorted(out.iterdir())
            if p.is_file()
        }
        (out / "BUILD_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )

    # ArcGIS-ready short upload path (ADM1 primary)
    upload = out / "UPLOAD_adm1.geojson"
    upload.write_bytes(adm1_geo.read_bytes())
    log(f"UPLOAD_adm1.geojson ready ({upload.stat().st_size/1e6:.2f}MB)")

    # refresh outputs listing after UPLOAD copy
    manifest["outputs"] = {
        p.name: {"path": str(p), "bytes": p.stat().st_size, "mb": round(p.stat().st_size / 1e6, 3)}
        for p in sorted(out.iterdir())
        if p.is_file()
    }
    (out / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    log(f"Done {iso}. Top-5: {manifest['score_summary_adm1']['top5']}")
    return manifest


if __name__ == "__main__":
    isos = sys.argv[1:] or ["NGA", "MEX", "IND"]
    for iso in isos:
        build_country(iso)
