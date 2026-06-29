"""
build_registry.py

Builds a full 254-county tracking registry by taking the authoritative
county list from data/reference/tx_county_population_2020.csv (all 254 Texas
counties) and layering on the known status + notes for the ones we've already
touched.

Run build_population_reference.py FIRST so the reference CSV exists.

This gives you a real "where are we across all 254" tracker, instead of a
hand-maintained list that drifts. Counties we haven't started show as
'not_started'; the ones with known state are filled in below.

Usage
-----
    python scripts/build_registry.py

Output
------
    scripts/county_registry.csv
    columns: county_fips, county_name, status, notebook_path, population_2020, notes

Edit KNOWN_STATUS below as counties progress (or, later, have the validator
update it automatically).
"""

import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REFERENCE_PATH = os.path.join(
    REPO_ROOT, "data", "reference", "tx_county_population_2020.csv"
)
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "county_registry.csv")


def nb(slug):
    return f"notebooks/07_time_series_pipeline_{slug}.ipynb"


# Keyed by county name. Everything not listed defaults to status 'not_started'.
KNOWN_STATUS = {
    "Travis": ("done", nb("travis"), ""),
    "Williamson": ("done", nb("williamson"), "patch cell present but no-op"),
    "Collin": ("done", nb("collin"), "2018 patch real (316->334); committed file was short until fixed"),
    "Bexar": ("done", nb("bexar"), "2018 patch real (1148->1162); committed file was short until fixed"),
    "Cameron": ("done", nb("cameron"), "2018 patch real (106->107); committed file was short until fixed"),
    "Galveston": ("done", nb("galveston"), "patch cell present but no-op (114=114)"),
    "Webb": ("done", nb("webb"), "has uncontested 2018 race(s)"),
    "Hidalgo": ("done", nb("hidalgo"), "large county"),
    "Fort Bend": ("done", nb("fort_bend"), "had an endpoint-uncontested case previously"),
    "Starr": ("done", nb("starr"), "has uncontested 2018 race(s)"),
    "Hays": ("blocked", "", "TLC boundary file only has 4 VTDs - too coarse; population data incomplete"),
}


def main():
    if not os.path.exists(REFERENCE_PATH):
        sys.exit(
            f"Reference file not found: {REFERENCE_PATH}\n"
            "Run build_population_reference.py first so the 254-county list exists."
        )

    with open(REFERENCE_PATH) as f:
        reference = list(csv.DictReader(f))

    rows = []
    for ref in reference:
        name = ref["county_name"]
        status, notebook, notes = KNOWN_STATUS.get(name, ("not_started", "", ""))
        rows.append({
            "county_fips": ref["county_fips"],
            "county_name": name,
            "status": status,
            "notebook_path": notebook,
            "population_2020": ref["population_2020"],
            "notes": notes,
        })

    with open(REGISTRY_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "county_fips", "county_name", "status",
                "notebook_path", "population_2020", "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    done = sum(1 for r in rows if r["status"] == "done")
    blocked = sum(1 for r in rows if r["status"] == "blocked")
    not_started = sum(1 for r in rows if r["status"] == "not_started")
    print(f"Wrote {len(rows)} counties to {REGISTRY_PATH}")
    print(f"  done: {done}   blocked: {blocked}   not_started: {not_started}")


if __name__ == "__main__":
    main()
