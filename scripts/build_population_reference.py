"""
build_population_reference.py

Fetches the authoritative 2020 Census P.L. 94-171 total population for every
Texas county directly from the Census Bureau API and writes it to
data/reference/tx_county_population_2020.csv.

Why this exists
---------------
The health check's population test is only as trustworthy as the reference
number it compares against. Rather than hardcode populations (which risks a
"plausible but wrong" reference -- the exact failure mode we're trying to
catch), this pulls the official 2020 decennial P.L. 94-171 county totals
from the Census Bureau directly. That's the same vintage as the census-block
population the pipeline weights on, so a correctly-built county should match
its reference closely.

Field notes
-----------
- P1_001N is the total population variable in the 2020 P.L. 94-171 file.
- state:48 is Texas.
- No API key is required for a request this small.
- FIPS is returned as a 3-digit county code; we prefix '48' to get the full
  5-digit county FIPS that matches the registry.

Usage
-----
    python scripts/build_population_reference.py

Output
------
    data/reference/tx_county_population_2020.csv
    with columns: county_fips, county_name, population_2020

If your environment can't reach api.census.gov, you can instead paste the
URL printed by this script into a browser, save the JSON, and the script
will read it from a local file if you pass --from-file <path>.
"""

import argparse
import csv
import json
import os
import sys
import urllib.request

CENSUS_URL = (
    "https://api.census.gov/data/2020/dec/pl"
    "?get=NAME,P1_001N&for=county:*&in=state:48"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUT_DIR = os.path.join(REPO_ROOT, "data", "reference")
OUT_PATH = os.path.join(OUT_DIR, "tx_county_population_2020.csv")


def fetch_from_api():
    print(f"Fetching from Census API:\n  {CENSUS_URL}\n")
    with urllib.request.urlopen(CENSUS_URL, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def load_from_file(path):
    with open(path) as f:
        return json.load(f)


def normalize(rows):
    """Census API returns a list-of-lists; first row is the header.
    Header: ['NAME', 'P1_001N', 'state', 'county']
    NAME looks like 'Travis County, Texas'.
    """
    header = rows[0]
    name_i = header.index("NAME")
    pop_i = header.index("P1_001N")
    county_i = header.index("county")

    out = []
    for row in rows[1:]:
        full_name = row[name_i]
        # 'Travis County, Texas' -> 'Travis'
        county_name = full_name.split(" County")[0].strip()
        population = int(row[pop_i])
        county_fips = "48" + row[county_i]  # 3-digit -> 5-digit
        out.append((county_fips, county_name, population))

    out.sort(key=lambda r: r[1])  # alphabetical by county name
    return out


def write_csv(records):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["county_fips", "county_name", "population_2020"])
        writer.writerows(records)
    print(f"Wrote {len(records)} counties to {OUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-file",
        help="Read Census JSON from a local file instead of the API "
        "(use if your environment can't reach api.census.gov)",
    )
    args = parser.parse_args()

    try:
        if args.from_file:
            rows = load_from_file(args.from_file)
        else:
            rows = fetch_from_api()
    except Exception as e:
        print(f"\nCouldn't fetch the data: {e}\n", file=sys.stderr)
        print(
            "Workaround: open this URL in a browser, save the JSON to a file,\n"
            f"then run:  python scripts/build_population_reference.py --from-file <saved.json>\n\n"
            f"  {CENSUS_URL}\n",
            file=sys.stderr,
        )
        sys.exit(1)

    records = normalize(rows)

    # Sanity check: Texas has 254 counties. Warn if we didn't get them all.
    if len(records) != 254:
        print(
            f"WARNING: expected 254 Texas counties, got {len(records)}. "
            "Check the API response before trusting this file.",
            file=sys.stderr,
        )

    write_csv(records)

    # Print a few known counties as a spot-check the user can eyeball.
    spot = {"Travis", "Bexar", "Collin", "Hays"}
    print("\nSpot-check (verify these look right):")
    for fips, name, pop in records:
        if name in spot:
            print(f"  {name:12s} {fips}  {pop:>10,}")


if __name__ == "__main__":
    main()
