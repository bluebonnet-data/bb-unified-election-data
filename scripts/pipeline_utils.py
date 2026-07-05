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

    result.attrs['leakage'] = {
        'original': original_total,
        'interpolated': interpolated_total,
        'diff': diff,
    }
    return result

def save_leakage_report(county_slug, interp_by_year, output_dir='../data/processed'):
    """
    Save the per-cycle vote-leakage check to disk as {slug}_leakage.csv.

    Reads the leakage stats that interpolate_votes_to_districts() attaches to
    each interpolated DataFrame via .attrs['leakage'], so call after
    interpolation. Near-zero diff each year means votes were conserved; a
    large diff means precincts in the results didn't match the weights table.
    """
    import os
    rows = []
    for yr in sorted(interp_by_year):
        interp = interp_by_year[yr]
        if 'leakage' not in interp.attrs:
            raise KeyError(
                f"{yr} interpolated frame has no .attrs['leakage'] -- "
                "restart the kernel and re-run so the patched "
                "interpolate_votes_to_districts() is loaded."
            )
        s = interp.attrs['leakage']
        rows.append({
            'year': yr,
            'original_votes': round(s['original'], 2),
            'interpolated_votes': round(s['interpolated'], 2),
            'diff': round(s['diff'], 2),
        })
    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, f'{county_slug}_leakage.csv')
    df.to_csv(path, index=False)
    print(f"Saved {county_slug}_leakage.csv")
    print(df.to_string(index=False))
    return df

def reconcile_precinct_ids(results, boundary_pctkeys, county_fips, year=None):
    """
    Fix precinct-ID mismatches between MEDSL results and the boundary file by
    matching against the boundary IDs directly, instead of applying a blind
    transform and hoping it lines up.

    Background
    ----------
    load_medsl() normalizes precinct IDs with fixed rules (strip letter
    suffixes, strip leading zeros, fix the 2024 county prefix). Those rules
    are right for some counties and wrong for others:
      * Group A (e.g. Rockwall, Hunt, Medina, Van Zandt): the RAW MEDSL ID
        already matches the boundary; stripping suffixes corrupts it.
      * Group B (e.g. Angelina, Aransas, Bowie): low-FIPS counties where MEDSL
        zero-pads the county prefix to 3 digits ('0050001') but the boundary
        uses the unpadded FIPS ('50001'); one leading zero must go.
    A single blind transform can't satisfy both. This function instead tries
    the raw ID and a small set of variants against the actual boundary IDs,
    and keeps whichever one is really present -- verification, not guessing.

    It rebuilds PCTKEY from the RAW 'precinct' column (which load_medsl leaves
    intact), so it recovers IDs even if load_medsl already mangled PCTKEY.

    Parameters
    ----------
    results : DataFrame
        Output of load_medsl(). Must have the original 'precinct' column and a
        'PCTKEY' column.
    boundary_pctkeys : iterable of str
        The PCTKEY values present in the boundary file for this county/year.
    county_fips : int or str
        County FIPS (e.g. 397). Used to reason about the prefix.
    year : int, optional
        For diagnostics only.

    Returns
    -------
    (DataFrame, dict)
        The results DataFrame with PCTKEY reassigned to the matched boundary
        ID where a match was found (rows with no match keep their prior PCTKEY
        so they still surface as leakage rather than silently changing), and a
        stats dict: {matched, unmatched, unmatched_ids, strategy_counts}.
    """
    boundary = set(str(k) for k in boundary_pctkeys)
    fips = str(county_fips)

    def variants(raw):
        """Candidate boundary IDs to try for a raw MEDSL precinct value,
        most-specific first. First one present in the boundary wins."""
        raw = str(raw).strip()

        # MEDSL sometimes appends a '_NNNN' instance id (e.g. '3970001_7553',
        # '397001A_7558'). The part before the underscore is the real precinct
        # id, so split on '_' first and build all variants from that base.
        base = raw.split('_')[0]

        cands = []

        # 1. base, as-is (Group A: suffixed IDs that already match)
        cands.append(('raw', base))

        # 2. base with a single leading zero dropped (Group B: '0050001'->'50001')
        if base.startswith('0'):
            cands.append(('drop_leading_zero', base[1:]))

        # 3. base with ALL leading zeros dropped (defensive)
        stripped = base.lstrip('0')
        if stripped and stripped != base:
            cands.append(('lstrip_zeros', stripped))

        # 4. letter suffix stripped (for counties where suffix really is noise)
        import re
        nosuffix = re.sub(r'[A-Za-z]+$', '', base)
        if nosuffix != base:
            cands.append(('strip_suffix', nosuffix))
            # and suffix-stripped + leading zero dropped
            if nosuffix.startswith('0'):
                cands.append(('strip_suffix+drop_zero', nosuffix[1:]))

        # 5. reduce a multi-letter suffix to its first letter, for split-of-
        #    split precincts finer than the boundary (e.g. '397001BA' -> the
        #    boundary only has '397001B'). Keep the digits + first suffix letter.
        m = re.match(r'^(\d+[A-Za-z])[A-Za-z]+$', base)
        if m:
            cands.append(('reduce_suffix', m.group(1)))

        # 6. swap a wrong county prefix for the correct FIPS. MEDSL 2024
        #    sometimes labels a county's precincts with a different county's
        #    code of the SAME length as the real FIPS (e.g. Rockwall/397 ->
        #    '199xxxx', Bowie/37 -> '19xxxx'). Strip len(fips) leading digits
        #    and prepend the correct FIPS; the remainder (digits + any suffix)
        #    is the real precinct. Also try reduced/stripped-suffix forms.
        pm = re.match(r'^\d{%d}(\d+[A-Za-z]*)$' % len(fips), base)
        if pm:
            rest = pm.group(1)
            cands.append(('swap_prefix', fips + rest))
            rm = re.match(r'^(\d+[A-Za-z])[A-Za-z]+$', rest)
            if rm:
                cands.append(('swap_prefix+reduce', fips + rm.group(1)))
            rest_nosuffix = re.sub(r'[A-Za-z]+$', '', rest)
            if rest_nosuffix != rest:
                cands.append(('swap_prefix+strip_suffix', fips + rest_nosuffix))

        return cands

    # Build a per-raw-precinct resolution map
    strategy_counts = {}
    resolved = {}   # raw precinct -> matched boundary id (or None)
    raw_col = results['precinct'] if 'precinct' in results.columns else results['PCTKEY']
    for raw in raw_col.dropna().unique():
        match = None
        for strat, cand in variants(raw):
            if cand in boundary:
                match = cand
                strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
                break
        resolved[str(raw)] = match

    # Apply: reassign PCTKEY to the matched boundary id where we found one
    def apply_row(row):
        raw = str(row['precinct']) if 'precinct' in results.columns else str(row['PCTKEY'])
        m = resolved.get(raw)
        return m if m is not None else row['PCTKEY']

    out = results.copy()
    out['PCTKEY'] = out.apply(apply_row, axis=1)

    matched_ids = {r for r, m in resolved.items() if m is not None}
    unmatched_ids = sorted(r for r, m in resolved.items() if m is None)
    stats = {
        'matched': len(matched_ids),
        'unmatched': len(unmatched_ids),
        'unmatched_ids': unmatched_ids[:20],
        'strategy_counts': strategy_counts,
    }
    return out, stats

def run_county(county_fips, county_name, data_dir='../data', save=True):
    """
    Run the full time-series pipeline (notebook Steps 1-8) for a single county
    and return a result dict. Designed for batch execution: any failure is
    caught and returned rather than raised, so one bad county doesn't halt a
    run over all 254.

    This is a faithful extraction of the per-county notebook orchestration.
    It calls the same building-block functions the notebooks use
    (build_weights_table, load_medsl, patch_missing_precincts,
    interpolate_votes_to_districts, save_leakage_report), in the same order.

    Parameters
    ----------
    county_fips : int
        County FIPS code (e.g. 453 for Travis).
    county_name : str
        Uppercase county name as it appears in 2018+ MEDSL files (e.g. 'TRAVIS').
        The 2016 title-case variant is derived from this.
    data_dir : str
        Path to the data/ directory (default '../data', matching notebook cwd).
    save : bool
        If True, write the processed outputs (weights, time series, leakage)
        to data/processed/. If False, run everything but write nothing --
        useful for a dry triage pass.

    Returns
    -------
    dict with keys:
        county_fips, county_name, slug
        status        : 'ok' | 'error'
        stage         : which step was running if it errored (else None)
        error         : exception message if status == 'error' (else None)
        leakage       : {year: diff} per cycle if it got that far (else {})
        n_precincts   : {year: unique-precinct count from results} (diagnostic)
        weight_invalid: {year: count of precincts not summing to 1.0}
    """
    import os
    import geopandas as gpd
    import pandas as pd

    slug = county_name.lower().replace(' ', '_')
    result = {
        'county_fips': county_fips,
        'county_name': county_name,
        'slug': slug,
        'status': 'ok',
        'stage': None,
        'error': None,
        'leakage': {},
        'n_precincts': {},
        'weight_invalid': {},
        'zero_pop': 0,
        'missing_years': [],
    }

    raw = os.path.join(data_dir, 'raw')
    processed = os.path.join(data_dir, 'processed')

    def _f(*parts):
        return os.path.join(*parts)

    try:
        # -- STEP 1: precinct boundaries per cycle -------------------------
        result['stage'] = 'load_boundaries'
        boundary_specs = {
            2016: ('zip://' + _f(raw, 'election_results', 'tx_2016.zip') + '!tx_2016.shp', county_fips),
            2018: ('zip://' + _f(raw, 'election_results', 'tx_2018.zip') + '!tx_2018.shp', county_fips),
            2020: ('zip://' + _f(raw, 'boundaries', 'precincts20g_2020.zip') + '!Precincts20G_2020.shp', county_fips),
            2022: ('zip://' + _f(raw, 'boundaries', 'precincts22g.zip') + '!Precincts22G.shp', county_fips),
            2024: ('zip://' + _f(raw, 'boundaries', 'precincts24g.zip') + '!Precincts24G.shp', county_fips),
        }
        precincts = {}
        for yr, (path, fips) in boundary_specs.items():
            gdf = gpd.read_file(path)
            gdf = gdf[gdf['CNTY'] == fips].copy()
            if len(gdf) == 0:
                raise ValueError(
                    f"{yr} boundary filter returned 0 precincts for CNTY={fips!r}. "
                    "County code type/value mismatch in this boundary file."
                )
            precincts[yr] = gdf

        # -- STEP 2: 2026 districts ----------------------------------------
        result['stage'] = 'load_districts'
        districts = gpd.read_file(
            'zip://' + _f(raw, 'boundaries', 'PLANC2333.zip') + '!PLANC2333/PLANC2333.shp'
        )

        # -- STEP 3: census blocks + population ----------------------------
        result['stage'] = 'load_blocks'
        blocks = gpd.read_file('zip://' + _f(raw, 'census', 'Blocks.zip') + '!Blocks.shp')
        blocks = blocks[blocks['CNTY'] == str(county_fips).zfill(3)].copy()
        if len(blocks) == 0:
            raise ValueError(
                f"census block filter returned 0 blocks for CNTY={str(county_fips).zfill(3)!r}."
            )
        pop = pd.read_csv(_f(raw, 'census', 'Blocks_Pop.txt'), dtype={'SCTBKEY': str})
        pop = pop[pop['SCTBKEY'].str.startswith('48' + str(county_fips).zfill(3))].copy()
        blocks = blocks.merge(pop[['SCTBKEY', 'total']], on='SCTBKEY', how='left')
        blocks['total'] = blocks['total'].fillna(0)

        # -- STEP 4: weights tables per cycle ------------------------------
        result['stage'] = 'build_weights'
        weights = {}
        for yr in [2016, 2018, 2020, 2022, 2024]:
            w = build_weights_table(precincts[yr], districts, blocks, str(yr))
            weights[yr] = w
            # Count only GENUINELY broken precincts. A precinct with
            # precinct_total == 0 produces weight = 0/0 = NaN and sums to 0,
            # not 1.0 -- but that's a benign empty precinct, not breakage
            # (matches health_check.py's zero-pop handling). Exclude those,
            # then check whether any real precinct's weights miss 1.0.
            if 'precinct_total' in w.columns:
                zero_pop_ids = set(
                    w.loc[w['precinct_total'] == 0, 'old_precinct_id'].unique())
            else:
                zero_pop_ids = set()
            real = w[~w['old_precinct_id'].isin(zero_pop_ids)]
            ws = real.groupby('old_precinct_id')['weight'].sum()
            result['weight_invalid'][yr] = int((ws.round(6) != 1.0).sum())
            result['zero_pop'] = result.get('zero_pop', 0) + len(zero_pop_ids)

        # -- STEP 5: weights built; saving deferred until leakage verdict --
        # (We only write files for counties that come back clean/partial, so
        #  all saving happens at the end once leakage is known.)

        # -- STEP 6: election results per cycle ----------------------------
        result['stage'] = 'load_results'
        # Most counties' 2016 MEDSL name is title-case + ' County', but some
        # have irregular internal capitalization that .title() gets wrong
        # (e.g. MCLENNAN -> 'Mclennan' but MEDSL has 'McLennan'). Override those.
        NAME_2016_OVERRIDES = {
            'DEWITT': 'DeWitt County',
            'MCCULLOCH': 'McCulloch County',
            'MCLENNAN': 'McLennan County',
            'MCMULLEN': 'McMullen County',
        }
        name_2016 = NAME_2016_OVERRIDES.get(
            county_name.upper(), county_name.title() + ' County')
        result_specs = {
            2016: (_f(raw, 'election_results', 'HOUSE_precinct_general_2016.tab'), name_2016),
            2018: (_f(raw, 'election_results', 'HOUSE_precinct_general_2018.csv'), county_name),
            2020: (_f(raw, 'election_results', 'HOUSE_precinct_general_2020.csv'), county_name),
            2022: (_f(raw, 'election_results', 'HOUSE_precinct_general_2022.csv'), county_name),
            2024: (_f(raw, 'election_results', 'HOUSE_precinct_general_2024.csv'), county_name),
        }
        results = {}
        missing_years = []
        for yr, (path, name) in result_specs.items():
            r = load_medsl(path, ',', name, yr, county_fips)
            if len(r) == 0:
                # Genuinely no results for this year. For 2016 this is a known
                # MEDSL coverage gap for some counties (e.g. the uncontested
                # TX-08 counties). Rather than failing the whole county, skip
                # the year and process the cycles that do exist. Recorded so
                # it's visible, not silent.
                missing_years.append(yr)
                continue
            results[yr] = r
            result['n_precincts'][yr] = int(r['PCTKEY'].nunique())

        result['missing_years'] = missing_years
        if not results:
            raise ValueError(
                f"no results found for any year (county_name={county_name!r}). "
                "Likely a name-spelling mismatch across all files."
            )

        # years we actually have data for, in order
        active_years = [y for y in [2016, 2018, 2020, 2022, 2024] if y in results]

        # -- STEP 6a: reconcile precinct IDs against the boundary ----------
        # load_medsl applies blind ID normalizations that are wrong for some
        # counties (suffix precincts that already match, low-FIPS leading-zero
        # differences). Reconcile against the actual boundary PCTKEYs so each
        # precinct maps to a real boundary geometry where one exists.
        result['stage'] = 'reconcile'
        result['reconcile'] = {}
        for yr in active_years:
            boundary_keys = precincts[yr]['PCTKEY'].astype(str).unique()
            results[yr], rstats = reconcile_precinct_ids(
                results[yr], boundary_keys, county_fips, yr)
            result['reconcile'][yr] = {
                'matched': rstats['matched'],
                'unmatched': rstats['unmatched'],
            }

        # -- STEP 6b: patch 2018 (no-op unless VEST gap; skip if no 2018) --
        result['stage'] = 'patch_2018'
        if 2018 in results:
            weights[2018] = patch_missing_precincts(
                results[2018], weights[2018], precincts[2020], districts, blocks, '2018'
            )

        # -- STEP 7: interpolate (only years we have results for) ----------
        result['stage'] = 'interpolate'
        interp = {}
        for yr in active_years:
            iv = interpolate_votes_to_districts(results[yr], weights[yr], yr)
            interp[yr] = iv
            result['leakage'][yr] = round(float(iv.attrs['leakage']['diff']), 2)

        # -- STEP 8: combine time series (in memory) -----------------------
        result['stage'] = 'combine_time_series'
        time_series = pd.concat([interp[y] for y in active_years],
                                ignore_index=True)
        time_series = time_series[['year', 'new_district_id', 'candidate',
                                   'party', 'estimated_votes']]
        time_series['party'] = time_series['party'].str.upper()
        time_series['party'] = time_series['party'].replace(
            {'DEMOCRATIC': 'DEMOCRAT', 'GREEN': 'OTHER'})

        # -- Verdict: is this county trustworthy? --------------------------
        # Save to data/processed/ ONLY if the county is clean or partial:
        #   * no genuine weight breakage, and
        #   * leakage under LEAKAGE_PCT_TOLERANCE in every active year.
        # Review/error counties run fully (so we get their diagnostics) but
        # write nothing, keeping data/processed/ free of untrusted output.
        LEAKAGE_PCT_TOLERANCE = 0.5  # match health_check.py
        worst_pct = 0.0
        for yr in active_years:
            orig = interp[yr].attrs['leakage']['original']
            diff = interp[yr].attrs['leakage']['diff']
            if orig > 0:
                worst_pct = max(worst_pct, 100.0 * diff / orig)
        weight_broken = sum(result['weight_invalid'].values()) > 0
        trustworthy = (worst_pct <= LEAKAGE_PCT_TOLERANCE) and not weight_broken
        result['worst_leak_pct'] = round(worst_pct, 4)
        result['trustworthy'] = trustworthy

        if save and trustworthy:
            result['stage'] = 'save'
            for yr in active_years:
                weights[yr].to_csv(
                    _f(processed, f'{slug}_population_weights_{yr}.csv'), index=False)
            save_leakage_report(slug, interp, output_dir=processed)
            time_series.to_csv(
                _f(processed, f'{slug}_house_time_series.csv'), index=False)
            result['saved'] = True
        else:
            result['saved'] = False

        result['stage'] = None
        return result

    except Exception as e:
        result['status'] = 'error'
        result['error'] = f"{type(e).__name__}: {e}"
        return resultxz 