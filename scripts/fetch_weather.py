"""Download NOAA ISD global-hourly 2015 observations for the busiest airports.

Station resolution: US continental airports use ICAO = "K" + IATA, matched against
NOAA's isd-history.csv. Non-continental airports (Hawaii PHNL/PHOG, Puerto Rico TJSJ)
do not follow that pattern, so they fall back to the nearest station by coordinates.

Run:  .venv/bin/python scripts/fetch_weather.py [n_airports]
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
WEATHER = ROOT / "data" / "weather"
RAW = WEATHER / "raw"
HISTORY_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
YEAR_URL = "https://www.ncei.noaa.gov/data/global-hourly/access/2015"


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def resolve_stations(n_airports: int) -> pd.DataFrame:
    hist_path = WEATHER / "isd-history.csv"
    if not hist_path.exists():
        WEATHER.mkdir(parents=True, exist_ok=True)
        hist_path.write_bytes(requests.get(HISTORY_URL, timeout=120).content)

    h = pd.read_csv(hist_path, dtype=str)
    h.columns = [c.strip().strip('"') for c in h.columns]
    for c in ("BEGIN", "END"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    for c in ("LAT", "LON"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h["ICAO"] = h["ICAO"].fillna("").str.strip()

    active = h[(h.BEGIN <= 20150101) & (h.END >= 20151231)
               & h.LAT.notna() & h.LON.notna()].copy()

    ap = pd.read_parquet(ROOT / "data" / "marts" / "airport_metrics.parquet")
    top = ap.sort_values("total_flights", ascending=False).head(n_airports)

    rows = []
    for _, a in top.iterrows():
        hit = active[active.ICAO == "K" + a.airport_code]
        method = "icao"
        if hit.empty and pd.notna(a.lat):
            d = haversine_km(a.lat, a.lon, active.LAT.values, active.LON.values)
            hit = active.iloc[[int(np.argmin(d))]]
            method = f"nearest_{d.min():.1f}km"
        if hit.empty:
            continue
        s = hit.sort_values("END", ascending=False).iloc[0]
        rows.append({"iata": a.airport_code, "usaf": s.USAF, "wban": s.WBAN,
                     "station": s["STATION NAME"], "method": method,
                     "flights": int(a.total_flights)})
    return pd.DataFrame(rows)


def fetch(station_id: str) -> tuple[str, int, str]:
    out = RAW / f"{station_id}.csv"
    if out.exists() and out.stat().st_size > 1000:
        return station_id, out.stat().st_size, "cached"
    try:
        r = requests.get(f"{YEAR_URL}/{station_id}.csv", timeout=180)
        if r.status_code != 200:
            return station_id, 0, f"http {r.status_code}"
        out.write_bytes(r.content)
        return station_id, len(r.content), "ok"
    except Exception as e:                      # network failures must not abort the batch
        return station_id, 0, f"error {type(e).__name__}"


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    RAW.mkdir(parents=True, exist_ok=True)

    stations = resolve_stations(n)
    stations.to_csv(WEATHER / "stations.csv", index=False)
    print(f"Resolved {len(stations)} stations "
          f"({(stations.method == 'icao').sum()} by ICAO, "
          f"{(stations.method != 'icao').sum()} by proximity)")

    ids = [f"{r.usaf}{r.wban}" for r in stations.itertuples()]
    total = failed = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, sid): sid for sid in ids}
        for i, fut in enumerate(as_completed(futures), 1):
            sid, size, status = fut.result()
            total += size
            if status not in ("ok", "cached"):
                failed += 1
                print(f"  [{i}/{len(ids)}] {sid} FAILED: {status}")
            elif i % 10 == 0:
                print(f"  [{i}/{len(ids)}] {total/1e6:.0f} MB so far")

    print(f"\nDownloaded {len(ids)-failed}/{len(ids)} stations, {total/1e6:.0f} MB")
    if failed:
        print(f"{failed} failed -- those airports get null weather and fall back to "
              "the global mean, exactly as unseen routes do.")


if __name__ == "__main__":
    main()
