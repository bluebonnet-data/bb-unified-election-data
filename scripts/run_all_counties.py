"""
run_all_counties.py

Batch triage: run the pipeline over every county in the registry and report
which ran clean, which leaked or flagged, and which errored. This is the
scoping tool -- one pass turns "244 counties left" into a sorted list of how
much work each actually needs.

It calls run_county() from pipeline_utils for each registry row, catches the
outcome, and writes a triage report to data/triage_report.csv plus a summary
to stdout.

Usage (from repo root):
    python scripts/run_all_counties.py                  # all not-yet-done counties
    python scripts/run_all_counties.py --all            # every county incl. done
    python scripts/run_all_counties.py --limit 10       # first 10 (a test batch)
    python scripts/run_all_counties.py --dry-run        # run pipeline, save nothing
    python scripts/run_all_counties.py --county TRAVIS   # a single county by name

Registry expected at scripts/county_registry.csv with columns including
county_fips, county_name, status.

IMPORTANT: this executes the real geopandas pipeline. It's slow (each county
does five spatial joins). Expect the first full run to surface data/naming
quirks that worked for the pilot ten but not elsewhere -- that surfacing IS
the scoping result, not a failure.
"""

import argparse
import csv
import os
import sys
import time

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from pipeline_utils import (  # noqa: E402
    build_weights_table,
    load_medsl,
    patch_missing_precincts,
    interpolate_votes_to_districts,
    save_leakage_report,
    run_county,
)

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, 'county_registry.csv')
DATA_DIR = os.path.join(REPO_ROOT, 'data')
REPORT_PATH = os.path.join(DATA_DIR, 'triage_report.csv')

LEAKAGE_PCT_TOLERANCE = 0.05  # match health_check.py


def classify(res):
    """Turn a run_county result dict into a triage category + note."""
    if res['status'] == 'error':
        return 'error', f"{res['stage']}: {res['error']}"

    # ran to completion -- assess leakage as % of original per year
    worst_pct = 0.0
    worst_year = None
    for yr, diff in res['leakage'].items():
        # we only stored diff; recompute pct needs original, which we don't
        # keep here -- so treat any diff > a few votes as worth noting and
        # let health_check.py do the precise % check against saved files.
        # For triage we flag on absolute diff as a coarse first pass.
        if diff > worst_pct:
            worst_pct = diff
            worst_year = yr

    invalid = sum(res['weight_invalid'].values())
    missing = res.get('missing_years', [])
    miss_note = f"; missing {len(missing)} yr(s): {missing}" if missing else ""

    if worst_pct >= 50:  # coarse: tens of votes+ is worth a look at this stage
        return 'review', f"leakage {worst_pct:.0f} votes in {worst_year}{miss_note}"
    if invalid > 0:
        return 'review', f"{invalid} precinct-years with weights != 1.0{miss_note}"
    if missing:
        return 'partial', f"clean on {5-len(missing)} cycles{miss_note}"
    return 'clean', ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true',
                        help='include counties already marked done')
    parser.add_argument('--limit', type=int, default=None,
                        help='only run the first N counties (test batch)')
    parser.add_argument('--dry-run', action='store_true',
                        help='run the pipeline but write no processed files')
    parser.add_argument('--county', default=None,
                        help='run a single county by uppercase name')
    args = parser.parse_args()

    registry = pd.read_csv(REGISTRY_PATH)

    if args.county:
        registry = registry[registry['county_name'].str.upper() == args.county.upper()]
        if registry.empty:
            sys.exit(f"County {args.county!r} not in registry.")
    elif not args.all:
        registry = registry[registry['status'] != 'done']

    if args.limit:
        registry = registry.head(args.limit)

    total = len(registry)
    print(f"Triaging {total} counties (save={'off' if args.dry_run else 'on'})\n")

    rows = []
    counts = {'clean': 0, 'partial': 0, 'review': 0, 'error': 0}
    t0 = time.time()

    for i, (_, r) in enumerate(registry.iterrows(), 1):
        fips = int(r['county_fips']) % 1000  # registry stores 48xxx; pipeline wants 3-digit
        name = str(r['county_name']).upper()
        t_c = time.time()
        res = run_county(fips, name, data_dir=DATA_DIR, save=not args.dry_run)
        cat, note = classify(res)
        counts[cat] = counts.get(cat, 0) + 1
        elapsed = time.time() - t_c
        rows.append({
            'county_name': name,
            'county_fips': r['county_fips'],
            'category': cat,
            'note': note,
            'seconds': round(elapsed, 1),
        })
        print(f"[{i}/{total}] {name:16s} {cat:7s} {note[:60]}")

    # write report
    with open(REPORT_PATH, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['county_name', 'county_fips',
                                          'category', 'note', 'seconds'])
        w.writeheader()
        w.writerows(rows)

    dt = time.time() - t0
    print('\n' + '=' * 60)
    print('TRIAGE SUMMARY')
    print('=' * 60)
    print(f"  clean : {counts.get('clean', 0)}")
    print(f"  partial: {counts.get('partial', 0)}  (missing 1+ cycle, rest clean)")
    print(f"  review: {counts.get('review', 0)}")
    print(f"  error : {counts.get('error', 0)}")
    print(f"  total : {total}   ({dt/60:.1f} min, {dt/max(total,1):.1f}s/county)")
    print(f"\nWrote {REPORT_PATH}")
    print("Next: look at the 'review' and 'error' rows -- that's the work left.")


if __name__ == '__main__':
    main()
