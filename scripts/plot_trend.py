"""
plot_trend.py — quick trend chart for a county straight from its saved
data/processed/<slug>_house_time_series.csv, using the REAL pipeline_viz
functions (so uncontested races render correctly, identical to notebook output).

This is a thin wrapper: it loads the saved time series and calls
pipeline_viz.build_two_party_pivot + pipeline_viz.plot_trend_lines. No plotting
logic is duplicated here, so the output matches what the notebooks produce
(including the Webb-style uncontested handling).

Usage (from repo root):
    python scripts/plot_trend.py harris
    python scripts/plot_trend.py tarrant

The chart is saved wherever plot_trend_lines saves it (docs/images/), same as
a notebook run.
"""

import argparse
import os
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

import pipeline_viz as viz  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROCESSED = os.path.join(REPO_ROOT, "data", "processed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="county slug, e.g. harris")
    ap.add_argument("--name", default=None,
                    help="display name (defaults to Title-cased slug)")
    args = ap.parse_args()

    slug = args.slug.lower().replace(" ", "_")
    name = args.name or slug.replace("_", " ").title()

    path = os.path.join(PROCESSED, f"{slug}_house_time_series.csv")
    if not os.path.exists(path):
        sys.exit(f"No time series found at {path}")

    time_series = pd.read_csv(path)

    # Use the real viz pipeline so uncontested handling matches the notebooks.
    pivot = viz.build_two_party_pivot(time_series)
    viz.plot_trend_lines(pivot, name, slug)

    print(f"Plotted {name} County from {path}")
    print("(saved by plot_trend_lines, same location as a notebook run)")


if __name__ == "__main__":
    main()
