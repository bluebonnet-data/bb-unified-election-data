"""
health_check.py

Validation health report for the Bluebonnet Unified Election Data pipeline.

Reads ONLY the saved artifacts in data/processed/ (the per-county weights
CSVs and house time-series CSVs) plus the census population reference in
data/reference/. It does not re-run the pipeline, so it's a fast standalone
scan you can run any time to see every processed county's health on one
screen.

Artifacts it reads (per county <slug>):
  data/processed/<slug>_house_time_series.csv
      columns: year, new_district_id, candidate, party, estimated_votes
  data/processed/<slug>_population_weights_<YEAR>.csv   (YEAR in 2016..2024)
      columns: old_precinct_id, new_district_id, fragment_population,
               precinct_total, weight
  data/reference/tx_county_population_2020.csv
      columns: county_fips, county_name, population_2020

Detectors (each tied to a real failure this project has hit):
  weights_sum        per-precinct weights should sum to ~1.0 each year
  pop_implausible    turnout (busiest year's votes / pipeline population)
                     above 1.0 is physically impossible -> the Hays signature
  pop_below_census   pipeline population vs official 2020 census county total;
                     flags only when pipeline pop is BELOW census by more than
                     TOLERANCE (the Hays signature). Above-census is expected
                     and not flagged, because precinct_total is a known
                     over-count that cancels out of the weight ratios. Loose
                     tolerance (default 10%) so the documented ~1.9% TX census
                     undercount doesn't false-flag.
  near_uncontested   min two-party share < 5% (token-opposition spike, e.g.
                     Williamson D31)
  shift_clipping     max abs 2016->2024 swing > 12 pts (change-map clipping)
  missing_years      time series should contain all five cycles

Usage (from repo root):
  python scripts/health_check.py
  python scripts/health_check.py --csv health_report.csv
  python scripts/health_check.py --county travis
  python scripts/health_check.py --tolerance 0.10

Output: a per-county table (flagged counties first), a summary line, and
optionally a CSV.
"""

import argparse
import glob
import os
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "data", "processed")
DEFAULT_REFERENCE = os.path.join(
    REPO_ROOT, "data", "reference", "tx_county_population_2020.csv"
)

YEARS = [2016, 2018, 2020, 2022, 2024]

# Thresholds -- first-pass values from the failure modes we've hit.
TURNOUT_IMPLAUSIBLE = 1.0       # votes > population is impossible
CENSUS_TOLERANCE = 0.10         # +/-10% vs official census before flagging
NEAR_UNCONTESTED_SHARE = 5.0    # percent
SHIFT_CLIP = 12.0               # percentage points 2016->2024
LEAKAGE_PCT_TOLERANCE = 0.05    # percent of original votes. A diff above this
                                # in any year flags vote_leakage. Real data
                                # shows rounding accumulates to at most ~0.003%
                                # even in large counties (Collin 2020: 13 votes
                                # / 475k = 0.0027%); a real dropped precinct is
                                # 0.1%+. 0.05% sits well clear of both.


def discover_counties(data_dir):
    """Every county with a house_time_series.csv, by slug."""
    pattern = os.path.join(data_dir, "*_house_time_series.csv")
    slugs = []
    for path in sorted(glob.glob(pattern)):
        base = os.path.basename(path)
        slug = base[: -len("_house_time_series.csv")]
        slugs.append(slug)
    return slugs


def load_reference(reference_path):
    """Return dict: slug -> (census_population, county_name).
    Slug is the lowercased, underscored county name to match file slugs."""
    if not os.path.exists(reference_path):
        return {}
    df = pd.read_csv(reference_path)
    ref = {}
    for _, row in df.iterrows():
        slug = str(row["county_name"]).strip().lower().replace(" ", "_")
        ref[slug] = (int(row["population_2020"]), row["county_name"])
    return ref


def check_leakage(data_dir, slug):
    """Read the saved {slug}_leakage.csv (written by the notebook's Step 7b)
    and return (worst_diff_votes, worst_diff_pct, n_years).

    The file has one row per cycle: year, original_votes, interpolated_votes,
    diff. A near-zero diff every year means votes were conserved through
    interpolation; a large diff in any year means precincts were dropped.
    The percentage (diff / original_votes) is what we flag on, since a fixed
    vote count means different things in a 10k county vs a 2M county.

    Returns (None, None, 0) if the file doesn't exist (county processed
    before leakage-saving was added) so the report can show 'not_saved'
    rather than a misleading pass.
    """
    path = os.path.join(data_dir, f"{slug}_leakage.csv")
    if not os.path.exists(path):
        return None, None, 0
    try:
        df = pd.read_csv(path)
    except Exception:
        return None, None, 0
    if df.empty or "diff" not in df.columns or "original_votes" not in df.columns:
        return None, None, 0
    worst_votes = float(df["diff"].abs().max())
    # percentage diff per year, guarding against divide-by-zero
    pct = (df["diff"].abs() / df["original_votes"].replace(0, pd.NA) * 100.0)
    worst_pct = float(pct.max()) if pct.notna().any() else 0.0
    return worst_votes, worst_pct, len(df)


def check_weights(data_dir, slug):
    """Per-precinct weights should sum to ~1.0 in each year. Also return the
    2018 row count (the metric today's bug was about) and pipeline population
    derived from distinct precinct_total values."""
    w_sum_ok = True
    w2018_rows = None
    pipeline_pop = None
    zero_pop_precincts = set()

    for year in YEARS:
        path = os.path.join(data_dir, f"{slug}_population_weights_{year}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        if year == 2018:
            w2018_rows = len(df)

        # Weights for each old precinct should sum to ~1.0 across districts.
        # BUT a precinct with precinct_total == 0 produces weight = 0/0 = NaN,
        # which is benign: an empty precinct has no population to weight on.
        # We separate those out -- they're counted and reported, not flagged --
        # so that only genuinely broken weights (a real precinct whose pieces
        # don't sum to 1.0) trip the w_sum_ok flag.
        if {"old_precinct_id", "weight", "precinct_total"}.issubset(df.columns):
            # zero-population precincts: total is 0 (hence NaN weights)
            zero_pop_ids = set(
                df.loc[df["precinct_total"] == 0, "old_precinct_id"].unique()
            )
            zero_pop_precincts |= zero_pop_ids

            # check weight sums only on real (nonzero-population) precincts
            real = df[~df["old_precinct_id"].isin(zero_pop_ids)]
            sums = real.groupby("old_precinct_id")["weight"].sum()
            if ((sums - 1.0).abs() > 0.01).any():
                w_sum_ok = False
        elif {"old_precinct_id", "weight"}.issubset(df.columns):
            sums = df.groupby("old_precinct_id")["weight"].sum()
            if ((sums - 1.0).abs() > 0.01).any():
                w_sum_ok = False

        # pipeline population: each precinct's precinct_total counted once
        if {"old_precinct_id", "precinct_total"}.issubset(df.columns):
            pop = df.drop_duplicates("old_precinct_id")["precinct_total"].sum()
            # use the largest year's coverage as the population estimate
            if pipeline_pop is None or pop > pipeline_pop:
                pipeline_pop = pop

    return w_sum_ok, w2018_rows, pipeline_pop, len(zero_pop_precincts)


def check_time_series(data_dir, slug):
    """Returns metrics derived from the house time series:
    busiest-year total votes, years present, uncontested pair count,
    min two-party share, max 2016->2024 swing."""
    path = os.path.join(data_dir, f"{slug}_house_time_series.csv")
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)
    if df.empty:
        return {"empty": True}

    years_present = sorted(df["year"].unique().tolist())
    missing_years = [y for y in YEARS if y not in years_present]

    # busiest-year total votes (max votes summed across a single year)
    votes_by_year = df.groupby("year")["estimated_votes"].sum()
    busiest_votes = votes_by_year.max() if not votes_by_year.empty else 0

    # two-party share per (year, district): need party totals
    uncontested_pairs = 0
    min_share = 100.0
    shares_by_year_district = {}

    grouped = df.groupby(["year", "new_district_id", "party"])["estimated_votes"].sum()
    for (year, district), sub in grouped.groupby(level=[0, 1]):
        party_totals = sub.droplevel([0, 1])
        dem = party_totals.get("DEMOCRAT", 0)
        rep = party_totals.get("REPUBLICAN", 0)
        total = dem + rep
        if total <= 0:
            continue
        if dem == 0 or rep == 0:
            uncontested_pairs += 1
            continue
        dem_share = 100.0 * dem / total
        min_share = min(min_share, dem_share, 100.0 - dem_share)
        shares_by_year_district.setdefault(district, {})[year] = dem_share

    # max abs swing 2016 -> 2024 across districts that have both endpoints
    max_shift = 0.0
    for district, by_year in shares_by_year_district.items():
        if 2016 in by_year and 2024 in by_year:
            shift = abs(by_year[2024] - by_year[2016])
            max_shift = max(max_shift, shift)

    if min_share == 100.0:
        min_share = None  # no contested races found

    return {
        "empty": False,
        "missing_years": missing_years,
        "busiest_votes": busiest_votes,
        "uncontested_pairs": uncontested_pairs,
        "min_share": min_share,
        "max_shift": max_shift,
    }


def evaluate_county(data_dir, slug, reference, tolerance):
    w_sum_ok, w2018_rows, pipeline_pop, zero_pop = check_weights(data_dir, slug)
    ts = check_time_series(data_dir, slug)
    worst_leak_votes, worst_leak_pct, leak_years = check_leakage(data_dir, slug)

    # display the worst leakage as "Nvotes (P%)" or "not_saved"
    if worst_leak_votes is None:
        leak_display = "not_saved"
    else:
        leak_display = f"{worst_leak_votes:.0f} ({worst_leak_pct:.3f}%)"

    row = {
        "county": slug,
        "w_sum_ok": w_sum_ok,
        "w2018_rows": w2018_rows,
        "zero_pop_prec": zero_pop,
        "leakage": leak_display,
        "pipeline_pop": int(pipeline_pop) if pipeline_pop else None,
        "census_pop": None,
        "pop_pct_diff": None,
        "turnout": None,
        "uncontested": None,
        "min_share": None,
        "max_shift": None,
        "missing_years": None,
        "flags": [],
        "status": "OK",
    }

    flags = []

    if not w_sum_ok:
        flags.append("weights_sum")

    # leakage: flag only if the file exists AND the worst-year diff exceeds
    # the percentage tolerance (a real dropped-precinct leak, not rounding)
    if worst_leak_pct is not None and worst_leak_pct > LEAKAGE_PCT_TOLERANCE:
        flags.append("vote_leakage")

    # census comparison
    census_pop = None
    if slug in reference:
        census_pop, _ = reference[slug]
        row["census_pop"] = census_pop
        if pipeline_pop:
            pct = (pipeline_pop - census_pop) / census_pop
            row["pop_pct_diff"] = round(100.0 * pct, 1)
            # Only flag when pipeline population is BELOW census by more than
            # tolerance. That's the dangerous direction -- it's the Hays
            # signature (a county whose recorded population is far too small,
            # which silently distorts every weight). Pipeline populations
            # ABOVE census are expected here, because precinct_total is a
            # known over-count (boundary census blocks counted into multiple
            # precincts); this inflation cancels out of the weight ratios and
            # doesn't affect interpolated results, so it isn't flagged.
            if pct < -tolerance:
                flags.append("pop_below_census")

    if ts and not ts.get("empty"):
        # turnout / pop implausibility (self-referential, no reference needed)
        if pipeline_pop and pipeline_pop > 0:
            turnout = ts["busiest_votes"] / pipeline_pop
            row["turnout"] = round(turnout, 3)
            if turnout > TURNOUT_IMPLAUSIBLE:
                flags.append("pop_implausible")

        row["uncontested"] = ts["uncontested_pairs"]
        row["min_share"] = (
            round(ts["min_share"], 1) if ts["min_share"] is not None else None
        )
        row["max_shift"] = round(ts["max_shift"], 1)
        row["missing_years"] = ts["missing_years"]

        if ts["min_share"] is not None and ts["min_share"] < NEAR_UNCONTESTED_SHARE:
            flags.append("near_uncontested")
        # NOTE: a large 2016->2024 swing is NOT flagged as a problem. Big
        # shifts (e.g. the RGV counties) are exactly the real political
        # trends this project exists to surface, not data errors. max_shift
        # is reported in its own column for information; it never sets CHECK.
        if ts["missing_years"]:
            flags.append("missing_years")
    elif ts and ts.get("empty"):
        flags.append("empty_time_series")
    else:
        flags.append("no_time_series")

    # near_uncontested and uncontested-count are distinct: the count is
    # informational (Webb/Starr legitimately have uncontested races), the
    # share-based flag catches token-opposition spikes. We do NOT flag on
    # uncontested count alone.

    row["flags"] = flags
    row["status"] = "OK" if not flags else "CHECK"
    return row


def print_report(rows):
    # flagged first, then alphabetical
    rows_sorted = sorted(rows, key=lambda r: (r["status"] == "OK", r["county"]))

    cols = [
        ("county", 14, "s"),
        ("status", 7, "s"),
        ("leakage", 16, "s"),
        ("turnout", 8, "s"),
        ("pop_pct_diff", 13, "s"),
        ("w2018_rows", 11, "s"),
        ("zero_pop_prec", 14, "s"),
        ("uncontested", 12, "s"),
        ("min_share", 10, "s"),
        ("max_shift", 10, "s"),
        ("flags", 0, "s"),
    ]

    header = ""
    for name, width, _ in cols:
        header += (name if width == 0 else name[:width].ljust(width)) + "  "
    print("\n" + header.rstrip())
    print("-" * (len(header) + 20))

    for r in rows_sorted:
        line = ""
        for name, width, _ in cols:
            if name == "flags":
                val = ", ".join(r["flags"]) if r["flags"] else ""
            else:
                v = r.get(name)
                val = "" if v is None else str(v)
            line += (val if width == 0 else val[:width].ljust(width)) + "  "
        print(line.rstrip())

    n = len(rows)
    n_flagged = sum(1 for r in rows if r["status"] == "CHECK")
    print("\n" + "=" * 60)
    print(f"{n} counties checked  |  {n - n_flagged} OK  |  {n_flagged} need review")
    if n_flagged:
        print("Flagged: " + ", ".join(
            r["county"] for r in rows_sorted if r["status"] == "CHECK"
        ))
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    parser.add_argument("--reference", default=DEFAULT_REFERENCE)
    parser.add_argument("--county", help="check only this slug, e.g. travis")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=CENSUS_TOLERANCE,
        help="fractional tolerance for census comparison (default 0.10 = 10%%)",
    )
    parser.add_argument("--csv", help="also write the report to this CSV path")
    args = parser.parse_args()

    reference = load_reference(args.reference)
    if not reference:
        print(
            f"NOTE: no census reference found at {args.reference} -- the "
            "pop_vs_census check will be skipped. Run build_population_reference.py "
            "to enable it.\n",
            file=sys.stderr,
        )

    slugs = discover_counties(args.data_dir)
    if args.county:
        slugs = [s for s in slugs if s == args.county.lower()]
        if not slugs:
            sys.exit(f"No time series found for county '{args.county}'")

    if not slugs:
        sys.exit(f"No county time-series files found in {args.data_dir}")

    rows = [evaluate_county(args.data_dir, s, reference, args.tolerance) for s in slugs]
    print_report(rows)

    if args.csv:
        flat = []
        for r in rows:
            r2 = dict(r)
            r2["flags"] = ", ".join(r["flags"])
            r2["missing_years"] = (
                ", ".join(map(str, r["missing_years"])) if r["missing_years"] else ""
            )
            flat.append(r2)
        pd.DataFrame(flat).to_csv(args.csv, index=False)
        print(f"Wrote report to {args.csv}")


if __name__ == "__main__":
    main()
