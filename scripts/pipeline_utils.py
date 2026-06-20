"""
pipeline_utils.py

Shared functions for the Bluebonnet Unified Election Data time series pipeline.
Extracted from the per-county notebooks (Travis, Williamson, Fort Bend, Collin,
Bexar, Galveston) to eliminate copy-paste drift across counties.

All notebooks should import from this module rather than defining these
functions inline:

    from pipeline_utils import (
        load_medsl,
        build_weights_table,
        patch_missing_precincts,
        interpolate_votes_to_districts,
    )

Pipeline overview
------------------
1. build_weights_table()       — intersect precinct boundaries with 2026
                                  districts and census blocks to get
                                  population weights
2. load_medsl()                — load and clean a year's MEDSL election
                                  results for a given county
3. patch_missing_precincts()   — call unconditionally after building each
                                  year's weights table and loading that
                                  year's results; it's a no-op unless the
                                  boundary file is missing precincts that
                                  exist in the results (known VEST 2018 gap)
4. interpolate_votes_to_districts() — apply weights to election results to
                                  produce estimated votes by 2026 district

Typical notebook usage
-----------------------
    weights_2018 = build_weights_table(precincts_2018, districts, blocks, '2018')
    results_2018 = load_medsl(path_2018, ',', COUNTY_NAME, 2018, COUNTY_FIPS)
    weights_2018 = patch_missing_precincts(
        results_2018, weights_2018, precincts_2020, districts, blocks, '2018'
    )
    interp_2018 = interpolate_votes_to_districts(results_2018, weights_2018, 2018)
"""

import pandas as pd
import geopandas as gpd


def build_weights_table(precincts, districts, blocks, label):
    """
    Build a population-weighted interpolation table for a given set of
    precinct boundaries intersected with 2026 congressional districts.

    Parameters
    ----------
    precincts : GeoDataFrame
        Precinct boundaries for a single county and election cycle.
        Must have a 'PCTKEY' column.
    districts : GeoDataFrame
        2026 congressional district boundaries. Must have a 'District' column.
    blocks : GeoDataFrame
        Census blocks with population counts. Must have a 'total' column.
    label : str
        Label for print statements (e.g. '2020').

    Returns
    -------
    DataFrame
        Columns: old_precinct_id, new_district_id, fragment_population,
        precinct_total, weight.
    """
    # Reproject all to same CRS
    districts_proj = districts.to_crs(precincts.crs)
    blocks_proj = blocks.to_crs(precincts.crs)

    # Tag each block with its precinct
    blocks_with_precinct = gpd.sjoin(
        blocks_proj,
        precincts[['PCTKEY', 'geometry']],
        how='left',
        predicate='intersects'
    )
    blocks_with_precinct = blocks_with_precinct.drop(columns=['index_right'])

    # Tag each block with its district
    blocks_with_both = gpd.sjoin(
        blocks_with_precinct,
        districts_proj[['District', 'geometry']],
        how='left',
        predicate='intersects'
    )

    # Calculate fragment populations
    fragments = blocks_with_both.groupby(
        ['PCTKEY', 'District']
    )['total'].sum().reset_index()
    fragments.columns = ['old_precinct_id', 'new_district_id', 'fragment_population']

    # Calculate weights
    precinct_totals = fragments.groupby('old_precinct_id')['fragment_population'].sum()
    fragments['precinct_total'] = fragments['old_precinct_id'].map(precinct_totals)
    fragments['weight'] = fragments['fragment_population'] / fragments['precinct_total']

    # Validate
    weight_sums = fragments.groupby('old_precinct_id')['weight'].sum()
    invalid = weight_sums[weight_sums.round(6) != 1.0]
    print(f"{label} weights table: {len(fragments)} rows")
    print(f"{label} weight validation — precincts not summing to 1.0: {len(invalid)}")
    if len(invalid) > 0:
        print(f"{label} invalid precincts: {list(invalid.index)}")

    return fragments


def patch_missing_precincts(results, weights, precincts_patch_source, districts, blocks, year_label='patch'):
    """
    Patch a weights table when the boundary file for that cycle is missing
    precincts that exist in the election results.

    Known cause: VEST's Texas precinct shapefiles for 2016/2018 sometimes lack
    precincts that the county added later in the cycle (seen so far: 13
    precincts in Collin County, 8 in Bexar County). The same precinct IDs
    show up cleanly in the 2020 TLC boundary file, so we borrow those shapes
    as the best available approximation. This introduces minor uncertainty
    for the patched precincts only — their true mid-cycle boundaries may
    have differed slightly from their 2020 boundaries.

    If nothing is missing, this is a no-op and returns the original weights
    table unchanged (safe to call unconditionally for every county).

    Parameters
    ----------
    results : DataFrame
        Output of load_medsl() for the affected year. Must have 'PCTKEY'.
    weights : DataFrame
        The (possibly incomplete) weights table for that year, as built by
        build_weights_table(). Must have 'old_precinct_id'.
    precincts_patch_source : GeoDataFrame
        Boundary file to borrow missing precinct shapes from (typically the
        2020 TLC file, i.e. precincts_2020). Must have a 'PCTKEY' column.
    districts : GeoDataFrame
        2026 congressional district boundaries, passed through to
        build_weights_table().
    blocks : GeoDataFrame
        Census blocks with population counts, passed through to
        build_weights_table().
    year_label : str
        Label for print statements (e.g. '2018').

    Returns
    -------
    DataFrame
        The original weights table with patched rows appended if anything
        was missing, otherwise the original weights table unchanged.
    """
    missing = set(results['PCTKEY'].unique()) - set(weights['old_precinct_id'].astype(str).unique())
    print(f"Missing {year_label} precincts: {sorted(missing)}")

    if not missing:
        return weights

    patch_source = precincts_patch_source.copy()
    patch_source['PCTKEY_clean'] = patch_source['PCTKEY'].astype(str).str.lstrip('0')
    patch_precincts = patch_source[patch_source['PCTKEY_clean'].isin(missing)].copy()
    patch_precincts['PCTKEY'] = patch_precincts['PCTKEY_clean']
    patch_precincts = patch_precincts.drop(columns=['PCTKEY_clean'])

    print(f"Found {len(patch_precincts)} precincts in patch source to backfill")

    if len(patch_precincts) == 0:
        print(f"WARNING: {len(missing)} precincts missing from results but "
              f"none found in patch source ({year_label}) — those votes "
              f"will be dropped during interpolation.")
        return weights

    weights_patch = build_weights_table(patch_precincts, districts, blocks, f'{year_label} patch')
    combined = pd.concat([weights, weights_patch], ignore_index=True)
    print(f"Final {year_label} weights table: {len(combined)} rows")
    return combined


def load_medsl(path, sep, county_name, year, county_fips):
    """
    Load and filter MEDSL election results for a given county and year,
    producing a 'PCTKEY' column that matches the TLC boundary file format.

    Handles several known MEDSL data quirks:
    - Some county names are ambiguous across states (e.g. "Williamson
      County" exists in TX, IL, and TN) — always filters to TX.
    - 2016 file uses different column names than 2018+ (state_postal vs
      state_po, county_name in title case vs uppercase for later years —
      caller must pass county_name already formatted correctly for the year).
    - 2018/2020/2022 precinct IDs may have leading zeros not present in the
      TLC boundary file (e.g. '0850001' vs '850001') — stripped here.
    - 2022/2024 may contain split precinct IDs with letter suffixes (e.g.
      '4530150A', '4530150B') for precincts that straddle district
      boundaries — suffix is stripped before matching.
    - 2024 MEDSL precinct IDs sometimes use a different county-code prefix
      than the TLC boundary file (e.g. '227xxxx' vs '453xxxx' for Travis
      County). Fixed by replacing the prefix with the correct county FIPS.

    Parameters
    ----------
    path : str
        Path to the MEDSL CSV/TAB file.
    sep : str
        Field separator (',' for all known files so far, including the
        2016 '.tab' file which is comma-separated despite the extension).
    county_name : str
        County name as it appears in this particular MEDSL file. For 2016
        this is typically "<County> County" (title case); for 2018+ it is
        typically the uppercase county name (e.g. "TRAVIS").
    year : int
        Election year. Drives the PCTKEY construction logic above.
    county_fips : int or str
        The county's FIPS code (e.g. 453 for Travis), used to correct the
        2024 prefix mismatch.

    Returns
    -------
    DataFrame
        Filtered to US House races for the given county/year, with a
        'PCTKEY' column ready to merge against a weights table, and the
        party column standardized to 'party'.
    """
    df = pd.read_csv(path, sep=sep, dtype={'precinct': str, 'county_fips': str},
                      low_memory=False)

    # Filter to county and House races
    # Always filter by state to avoid ambiguity with same county name across states
    if 'state_po' in df.columns:
        county = df[(df['county_name'] == county_name) &
                    (df['state_po'] == 'TX')].copy()
    elif 'state_postal' in df.columns:
        county = df[(df['county_name'] == county_name) &
                    (df['state_postal'] == 'TX')].copy()
    else:
        county = df[df['county_name'] == county_name].copy()

    # Filter to House races
    if 'dataverse' in county.columns:
        house = county[county['dataverse'] == 'HOUSE'].copy()
    else:
        house = county[county['office'].str.upper() == 'US HOUSE'].copy()

    # Construct PCTKEY
    if year == 2016:
        house['PCTKEY'] = house['precinct']
        # Strip letter suffixes from split precincts
        house['PCTKEY'] = house['PCTKEY'].str.replace(r'[A-Z]$', '', regex=True)

    elif year == 2024:
        house['PCTKEY'] = house['precinct'].str.split('_').str[0]
        # Strip letter suffixes BEFORE extracting last 4 digits — order matters,
        # otherwise the letter gets included in the 4-char slice
        house['PCTKEY'] = house['PCTKEY'].str.replace(r'[A-Z]$', '', regex=True)
        # Fix county-specific prefix — MEDSL uses a different prefix than TLC
        # for some counties. Extract last 4 digits with zero padding and
        # prepend the correct county FIPS.
        house['PCTKEY'] = str(county_fips) + house['PCTKEY'].str[-4:].str.zfill(4)
    else:
        house['PCTKEY'] = house['precinct'].str.split('_').str[0]
        # Strip letter suffixes from split precincts
        house['PCTKEY'] = house['PCTKEY'].str.replace(r'[A-Z]$', '', regex=True)

    # Normalize PCTKEY — remove leading zeros to match TLC boundary format.
    # Safe for all years: counties we've checked (Travis, Williamson, Fort
    # Bend) never have leading zeros, so this is a no-op for them, but it's
    # required for counties with FIPS codes under 100 (e.g. Collin = 85,
    # Bexar = 29) where MEDSL pads to a fixed width.
    house['PCTKEY'] = house['PCTKEY'].str.lstrip('0')

    # Standardize party column
    if 'party_simplified' in house.columns:
        house = house.rename(columns={'party_simplified': 'party'})

    print(f"{year}: {len(house)} rows, {house['PCTKEY'].nunique()} unique precincts")
    return house


def interpolate_votes_to_districts(results, weights, year):
    """
    Apply population weights to precinct-level election results to produce
    estimated vote totals by 2026 congressional district.

    Parameters
    ----------
    results : DataFrame
        Output of load_medsl() for one election year. Must have 'PCTKEY',
        'votes', 'candidate', 'party'.
    weights : DataFrame
        Output of build_weights_table() (optionally patched via
        patch_missing_precincts()) for the matching year.
        Must have 'old_precinct_id', 'new_district_id', 'weight'.
    year : int
        Election year, attached to the output for stacking into a time series.

    Returns
    -------
    DataFrame
        Columns: new_district_id, candidate, party, estimated_votes, year.
        Also prints a vote-leakage check: original total votes in `results`
        vs. the interpolated total. A nonzero diff means some precincts in
        `results` didn't match any row in `weights` (commonly a remaining
        boundary-file gap — see patch_missing_precincts).
    """
    merged = results.merge(
        weights[['old_precinct_id', 'new_district_id', 'weight']],
        left_on='PCTKEY',
        right_on='old_precinct_id',
        how='inner'
    )

    merged['estimated_votes'] = merged['votes'].astype(float) * merged['weight']

    result = merged.groupby(
        ['new_district_id', 'candidate', 'party']
    )['estimated_votes'].sum().reset_index()

    result['year'] = year

    original_total = results['votes'].astype(float).sum()
    interpolated_total = result['estimated_votes'].sum()
    diff = abs(original_total - interpolated_total)
    print(f"{year}: original={original_total:,.0f}, interpolated={interpolated_total:,.0f}, diff={diff:.2f}")

    return result
