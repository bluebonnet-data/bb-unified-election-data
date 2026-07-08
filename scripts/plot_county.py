"""
plot_county.py — generate ALL FOUR figures (trend lines + 3 choropleth maps)
for a county from the command line, using the saved time series plus freshly
built district geometry. No notebook needed.

Unlike plot_trend.py (CSV only, trend lines only), this rebuilds the
`districts_clipped` geometry the map functions need — it loads the 2026
district plan and the county's 2020 precincts, dissolves the precincts into a
county boundary, and clips the districts to it (the same Step 10 logic the
notebooks use). Then it calls all four pipeline_viz functions.

Usage (from repo root):
    python scripts/plot_county.py harris 201
    python scripts/plot_county.py tarrant 439
    python scripts/plot_county.py harris 201 --only trend,voteshare

The FIPS is the 3-digit county code (Harris = 201, Tarrant = 439). It's
needed to filter the statewide boundary file, same as the pipeline config.

Figures are saved to docs/images/ (same names/locations as a notebook run):
    <slug>_house_vote_share_trend.png   (trend lines)
    <slug>_house_maps.png               (vote-share choropleth)
    <slug>_house_change_map.png         (2016->2024 shift)
    <slug>_house_turnout_maps.png       (total votes)
"""

import argparse
import os
import sys

import pandas as pd
import geopandas as gpd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

import pipeline_viz as viz  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATA = os.path.join(REPO_ROOT, "data")
PROCESSED = os.path.join(DATA, "processed")
RAW = os.path.join(DATA, "raw")


def build_districts_clipped(county_fips):
    """Reproduce the notebook's Step 10 geometry: load the 2026 district plan
    and the county's 2020 precincts, dissolve precincts to a county boundary,
    clip districts to it. Returns districts_clipped (GeoDataFrame)."""
    districts = gpd.read_file(
        "zip://" + os.path.join(RAW, "boundaries", "PLANC2333.zip")
        + "!PLANC2333/PLANC2333.shp"
    )
    precincts_2020 = gpd.read_file(
        "zip://" + os.path.join(RAW, "boundaries", "precincts20g_2020.zip")
        + "!Precincts20G_2020.shp"
    )
    precincts_2020 = precincts_2020[precincts_2020["CNTY"] == county_fips].copy()
    if len(precincts_2020) == 0:
        raise ValueError(
            f"No 2020 precincts for CNTY={county_fips!r} — check the FIPS."
        )

    county_boundary = precincts_2020.dissolve()
    districts_clipped = gpd.clip(
        districts.to_crs(precincts_2020.crs), county_boundary
    )
    return districts_clipped


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="county slug, e.g. harris")
    ap.add_argument("fips", type=int, help="3-digit county FIPS, e.g. 201")
    ap.add_argument("--name", default=None,
                    help="display name (defaults to Title-cased slug)")
    ap.add_argument("--only", default=None,
                    help="comma list of figures to make: "
                         "trend,voteshare,change,turnout (default: all)")
    args = ap.parse_args()

    slug = args.slug.lower().replace(" ", "_")
    name = args.name or slug.replace("_", " ").title()
    want = set(args.only.split(",")) if args.only else \
        {"trend", "voteshare", "change", "turnout"}

    ts_path = os.path.join(PROCESSED, f"{slug}_house_time_series.csv")
    if not os.path.exists(ts_path):
        sys.exit(f"No time series found at {ts_path}")

    print(f"Loading time series for {name} County...")
    time_series = pd.read_csv(ts_path)
    pivot = viz.build_two_party_pivot(time_series)

    print("Building district geometry (this loads + clips shapefiles)...")
    districts_clipped = build_districts_clipped(args.fips)
    print(f"  clipped to {len(districts_clipped)} districts: "
          f"{sorted(districts_clipped['District'].unique())}")

    if "trend" in want:
        print("Trend lines...")
        viz.plot_trend_lines(pivot, name, slug)
    if "voteshare" in want:
        print("Vote-share map...")
        viz.plot_vote_share_map(pivot, districts_clipped, name, slug)
    if "change" in want:
        print("Change map...")
        viz.plot_change_map(pivot, districts_clipped, name, slug)
    if "turnout" in want:
        print("Turnout map...")
        viz.plot_turnout_map(time_series, districts_clipped, name, slug)

    print(f"\nDone. Figures saved to docs/images/ for {name} County.")


if __name__ == "__main__":
    main()
