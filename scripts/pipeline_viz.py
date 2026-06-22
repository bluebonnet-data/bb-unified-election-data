"""
pipeline_viz.py — shared plotting functions for the Bluebonnet time-series pipeline.

Centralizes the Step 9 / Step 10 figures so that fixes (e.g. the uncontested-race
handling and the dynamic turnout vmax) live in one place instead of being copy-pasted
across per-county notebooks.

Four figures:
    plot_trend_lines()     — Step 9: per-district two-party share over time (Image 1)
    plot_vote_share_map()  — Step 10: dem-share choropleth, hatched for uncontested (Image 2)
    plot_change_map()      — Step 10: 2016->2024 shift, single panel (Image 3)
    plot_turnout_map()     — Step 10: total estimated votes, dynamic vmax (Image 4)

Plus one helper:
    build_two_party_pivot() — computes the D/R pivot + dem_share/rep_share/uncontested
                              flags consumed by the trend lines and both share maps.

Design notes:
    - Plotting functions are pure: data in -> figure out. They do NOT read from disk.
      The notebook builds `time_series` / `districts_clipped` / `pivot` and passes them in.
    - Each function saves a PNG (side effect) AND returns `fig` so the notebook can
      tweak/inspect if needed.
    - Panel counts are fully data-driven (district count comes from the pivot), so the
      same functions work for a 2-district county (Starr) and a 7-district county (Travis)
      with no special-casing.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np


# Brand colors (kept consistent with the original notebook cells)
DEM_COLOR = '#185FA5'
REP_COLOR = '#A32D2D'

DEFAULT_YEARS = (2016, 2018, 2020, 2022, 2024)


# ---------------------------------------------------------------------------
# Helper: build the two-party pivot
# ---------------------------------------------------------------------------
def build_two_party_pivot(time_series):
    """
    Collapse a long time_series frame into one row per (year, district) with
    Democrat/Republican vote totals, two-party shares, and an uncontested flag.

    Expects `time_series` to have columns:
        year, new_district_id, party, estimated_votes

    Returns a DataFrame with columns:
        year, new_district_id, DEMOCRAT, REPUBLICAN,
        uncontested (bool), total, dem_share, rep_share
    """
    two_party = time_series[time_series['party'].isin(['DEMOCRAT', 'REPUBLICAN'])].copy()
    two_party_total = (
        two_party
        .groupby(['year', 'new_district_id', 'party'])['estimated_votes']
        .sum()
        .reset_index()
    )
    pivot = two_party_total.pivot_table(
        index=['year', 'new_district_id'],
        columns='party',
        values='estimated_votes',
    ).reset_index()
    pivot.columns.name = None

    # Make sure both party columns exist even if one is entirely absent
    for col in ('DEMOCRAT', 'REPUBLICAN'):
        if col not in pivot.columns:
            pivot[col] = np.nan

    # Uncontested = one party has no votes at all that cycle/district
    pivot['uncontested'] = pivot['DEMOCRAT'].isna() | pivot['REPUBLICAN'].isna()
    pivot['total'] = pivot['DEMOCRAT'] + pivot['REPUBLICAN']
    pivot['dem_share'] = pivot['DEMOCRAT'] / pivot['total'] * 100
    pivot['rep_share'] = pivot['REPUBLICAN'] / pivot['total'] * 100

    # Who won an uncontested race: the one party that actually has votes.
    # NaN for contested rows. Derived purely from which party column is populated,
    # so no extra data is needed — the winner is already implied by the pivot.
    # (x == x is False only when x is NaN, so it's a NaN check without importing isna.)
    pivot['uncontested_winner'] = pivot.apply(
        lambda r: 'DEMOCRAT' if (r['uncontested'] and r['DEMOCRAT'] == r['DEMOCRAT'])
        else ('REPUBLICAN' if (r['uncontested'] and r['REPUBLICAN'] == r['REPUBLICAN'])
              else np.nan),
        axis=1,
    )
    return pivot


# ---------------------------------------------------------------------------
# Image 1 — Step 9 trend lines
# ---------------------------------------------------------------------------
def plot_trend_lines(pivot, county_name, county_slug,
                     years_to_plot=DEFAULT_YEARS, save_dir='../docs/images'):
    """
    Per-district two-party vote share over time. Uncontested (district, year)
    pairs get a vertical dotted line + 'uncontested' label, and a dynamic
    footnote appears only if at least one uncontested race exists.

    `pivot` is the output of build_two_party_pivot().
    Returns the matplotlib Figure.
    """
    years = list(years_to_plot)
    districts = sorted(pivot['new_district_id'].unique())
    n_districts = len(districts)

    uncontested_pairs = (
        pivot[pivot['uncontested']][['new_district_id', 'year']].values.tolist()
    )

    n_cols = min(4, n_districts) if n_districts else 1
    n_rows = (n_districts + n_cols - 1) // n_cols if n_districts else 1
    # Scale the figure so each panel gets a roughly constant footprint (~4x4 in)
    # regardless of how many districts a county has. This keeps font sizes reading
    # consistently across counties from 2 districts (Starr) to 10+ (large counties),
    # instead of fonts looking tiny on wide 2-panel figures and cramped on 7-panel ones.
    panel_w, panel_h = 4.0, 4.0
    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(panel_w * n_cols, panel_h * n_rows))
    axes = np.atleast_1d(axes).flatten()

    i = -1  # guard so the "turn off unused axes" loop works even with 0 districts
    for i, district in enumerate(districts):
        ax = axes[i]
        d = pivot[pivot['new_district_id'] == district]

        ax.plot(d['year'], d['dem_share'], color=DEM_COLOR, marker='o',
                linewidth=2, label='Democrat')
        ax.plot(d['year'], d['rep_share'], color=REP_COLOR, marker='o',
                linewidth=2, label='Republican')
        ax.axhline(50, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)

        # Mark uncontested years: vertical dotted line marks WHERE the gap is
        # (two-party share is genuinely undefined, so no point is plotted there),
        # and the label is colored by who won unopposed so the viewer still sees
        # the outcome. Works regardless of whether the gap is an endpoint year
        # (2016/2024) or interior (2018) — it only depends on that row's data.
        for _, urow in d[d['uncontested']].iterrows():
            uy = urow['year']
            winner = urow['uncontested_winner']
            if winner == 'DEMOCRAT':
                label, lcolor = 'D uncontested', '#0d3a66'
            elif winner == 'REPUBLICAN':
                label, lcolor = 'R uncontested', '#6b1a1a'
            else:
                label, lcolor = 'uncontested', '#555555'  # fallback if winner unknown
            ax.axvline(uy, color='gray', linestyle=':', linewidth=1, alpha=0.6)
            ax.text(uy, 50, label, ha='center', fontsize=9,
                    color=lcolor, rotation=90, va='center', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='none', alpha=0.85))

        ax.set_title(f'District {district}', fontweight='bold', fontsize=12)
        ax.set_ylim(0, 100)
        ax.set_xticks(years)
        ax.set_xticklabels(years, rotation=45, fontsize=10)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.tick_params(axis='y', labelsize=10)
        ax.grid(axis='y', alpha=0.3)

        if i == 0:
            ax.legend(fontsize=10)

    # Turn off any unused axes in the grid
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    fig.text(0.07, 0.5, 'Two-party vote share', va='center',
             rotation='vertical', fontsize=12)
    plt.suptitle(
        f'U.S. House Two-Party Vote Share by 2026 District\n'
        f'{county_name.title()} County Contribution — 2016 to 2024',
        fontsize=15, fontweight='bold',
    )

    if uncontested_pairs:
        note_text = ('* Dotted line marks an uncontested race (one party had no candidate '
                     'that cycle) — two-party share is undefined, so none is plotted; '
                     'the colored label shows which party won uncontested.')
        fig.text(0.5, -0.02, note_text, ha='center', fontsize=10,
                 style='italic', color='gray')

    plt.tight_layout(rect=[0.07, 0, 1, 1])
    plt.savefig(f'{save_dir}/{county_slug}_house_vote_share_trend.png',
                dpi=150, bbox_inches='tight')
    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Image 2 — Step 10 vote-share map
# ---------------------------------------------------------------------------
def plot_vote_share_map(pivot, districts_clipped, county_name, county_slug,
                        years_to_plot=DEFAULT_YEARS, save_dir='../docs/images'):
    """
    Dem-share choropleth, one panel per year. A year that is entirely
    uncontested (no dem_share anywhere) renders as a hatched gray panel
    with an 'Uncontested' label instead of a colored map.

    `pivot` is the output of build_two_party_pivot().
    Returns the matplotlib Figure.
    """
    years = list(years_to_plot)
    fig, axes = plt.subplots(1, len(years), figsize=(25, 6))
    axes = np.atleast_1d(axes)

    bounds = districts_clipped.total_bounds

    for i, year in enumerate(years):
        ax = axes[i]
        year_data = pivot[pivot['year'] == year][['new_district_id', 'dem_share']].copy()
        year_data.columns = ['District', 'dem_share']
        districts_year = districts_clipped.merge(year_data, on='District', how='left')

        is_uncontested_year = districts_year['dem_share'].isna().all()
        if is_uncontested_year:
            # Color the hatched panel by who won unopposed (faded tint of the party
            # color), so the viewer sees the outcome even though no share is plotted.
            # Label text is dark for contrast and sits on a white box so the hatch
            # lines don't cut through it.
            yr_winners = pivot[(pivot['year'] == year) & pivot['uncontested']]['uncontested_winner'].dropna().unique()
            if len(yr_winners) == 1 and yr_winners[0] == 'DEMOCRAT':
                fill, txt, label = '#b3c6dd', '#0d3a66', 'D uncontested'
            elif len(yr_winners) == 1 and yr_winners[0] == 'REPUBLICAN':
                fill, txt, label = '#e0b3b3', '#6b1a1a', 'R uncontested'
            else:
                # mixed or unknown winners across districts — fall back to neutral
                fill, txt, label = '#dddddd', '#555555', 'Uncontested'
            districts_year.plot(ax=ax, color=fill, edgecolor='white',
                                linewidth=0.5, hatch='///')
            ax.text(0.5, 0.5, label, transform=ax.transAxes,
                    ha='center', va='center', fontsize=11,
                    color=txt, style='italic', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                              edgecolor='none', alpha=0.85))
        else:
            districts_year.plot(column='dem_share', ax=ax, cmap='RdBu',
                                vmin=30, vmax=70, legend=False,
                                edgecolor='white', linewidth=0.5)

        ax.set_title(f'{year}', fontweight='bold', fontsize=18)
        ax.set_axis_off()
        ax.set_xlim(bounds[0] - 2000, bounds[2] + 2000)
        ax.set_ylim(bounds[1] - 2000, bounds[3] + 2000)

    sm = plt.cm.ScalarMappable(cmap='RdBu', norm=plt.Normalize(vmin=30, vmax=70))
    sm.set_array([])
    cbar_ax = fig.add_axes([0.35, 0.08, 0.3, 0.03])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')
    cbar.ax.tick_params(labelsize=11)
    cbar.set_label('Two-party vote share (%)', fontsize=11)
    cbar.ax.text(0, -1.8, 'R', transform=cbar.ax.transAxes, fontsize=9,
                 color=REP_COLOR, fontweight='bold')
    cbar.ax.text(1, -1.8, 'D', transform=cbar.ax.transAxes, fontsize=9,
                 color=DEM_COLOR, fontweight='bold', ha='right')

    plt.suptitle(
        f'U.S. House Two-Party Vote Share by 2026 District\n'
        f'{county_name.title()} County — 2016 to 2024',
        fontsize=20, fontweight='bold', y=1.0,
    )
    plt.savefig(f'{save_dir}/{county_slug}_house_maps.png',
                dpi=150, bbox_inches='tight')
    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Image 3 — Step 10 change map
# ---------------------------------------------------------------------------
def plot_change_map(pivot, districts_clipped, county_name, county_slug,
                    year_start=2016, year_end=2024, clim=12,
                    save_dir='../docs/images'):
    """
    Single-panel choropleth of the shift in dem two-party share between
    `year_start` and `year_end`. Color scale is fixed at +/- `clim` so maps
    are directly comparable across counties (override clim for a county with
    an unusually large swing).

    If either endpoint year is uncontested for a district, the shift is
    genuinely uncomputable (you can't measure change in a share that didn't
    exist at one end). Those districts are hatched gray and the chart carries
    an explanatory note, rather than showing a misleading number or a silent
    blank.

    `pivot` is the output of build_two_party_pivot().
    Returns the matplotlib Figure.
    """
    dem_start = pivot[pivot['year'] == year_start][
        ['new_district_id', 'dem_share', 'uncontested']].copy()
    dem_end = pivot[pivot['year'] == year_end][
        ['new_district_id', 'dem_share', 'uncontested']].copy()

    change = dem_start.merge(dem_end, on='new_district_id',
                             suffixes=('_start', '_end'))
    change['delta'] = change['dem_share_end'] - change['dem_share_start']
    # A district's shift is uncomputable if either endpoint year was uncontested.
    change['endpoint_uncontested'] = (
        change['uncontested_start'] | change['uncontested_end']
    )
    change = change.rename(columns={'new_district_id': 'District'})

    districts_change = districts_clipped.merge(
        change[['District', 'delta', 'endpoint_uncontested']],
        on='District', how='left',
    )

    # Split into computable vs. uncomputable districts
    computable = districts_change[districts_change['endpoint_uncontested'] != True]
    flagged = districts_change[districts_change['endpoint_uncontested'] == True]

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    if len(computable):
        computable.plot(column='delta', ax=ax, cmap='RdBu',
                        vmin=-clim, vmax=clim, legend=False,
                        edgecolor='white', linewidth=0.5)
    if len(flagged):
        # Hatch out districts whose shift can't be computed, and label them.
        flagged.plot(ax=ax, color='#dddddd', edgecolor='white',
                     linewidth=0.5, hatch='///')
        ax.text(0.5, 0.5, 'Shift undefined\n(endpoint uncontested)',
                transform=ax.transAxes, ha='center', va='center',
                fontsize=10, color='#555555', style='italic', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                          edgecolor='none', alpha=0.85))
    ax.set_axis_off()

    sm = plt.cm.ScalarMappable(cmap='RdBu', norm=plt.Normalize(vmin=-clim, vmax=clim))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.03, pad=0.02)
    cbar.set_label('Change in two-party vote share (percentage points)', fontsize=12)

    plt.title(
        f'Shift in U.S. House Two-Party Vote Share\n'
        f'{county_name.title()} County — {year_start} to {year_end}',
        fontsize=13, fontweight='bold',
    )
    if len(flagged):
        fig.text(0.5, 0.04,
                 f'* Hatched districts had an uncontested race in {year_start} or '
                 f'{year_end}, so the two-party shift cannot be computed.',
                 ha='center', fontsize=8, style='italic', color='gray')
    plt.savefig(f'{save_dir}/{county_slug}_house_change_map.png',
                dpi=150, bbox_inches='tight')
    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Image 4 — Step 10 turnout map
# ---------------------------------------------------------------------------
def plot_turnout_map(time_series, districts_clipped, county_name, county_slug,
                     years_to_plot=DEFAULT_YEARS, save_dir='../docs/images'):
    """
    Total estimated votes per district per year, grayscale. vmax is derived
    from the county's own data (single source of truth, used by both the
    panels and the colorbar) so the scale never blows out.

    Computes its own turnout table directly from `time_series` (it groups
    across all parties, so it doesn't use the two-party pivot).
    Returns the matplotlib Figure.
    """
    years = list(years_to_plot)
    turnout = (
        time_series
        .groupby(['year', 'new_district_id'])['estimated_votes']
        .sum()
        .reset_index()
    )
    turnout.columns = ['year', 'District', 'total_votes']
    vmax = turnout['total_votes'].max()

    fig, axes = plt.subplots(1, len(years), figsize=(25, 6))
    axes = np.atleast_1d(axes)
    bounds = districts_clipped.total_bounds

    for i, year in enumerate(years):
        ax = axes[i]
        year_data = turnout[turnout['year'] == year][['District', 'total_votes']].copy()
        districts_year = districts_clipped.merge(year_data, on='District', how='left')

        districts_year.plot(column='total_votes', ax=ax, cmap='Greys',
                            vmin=0, vmax=vmax, legend=False,
                            edgecolor='white', linewidth=0.5)
        ax.set_title(f'{year}', fontweight='bold', fontsize=16)
        ax.set_axis_off()
        ax.set_xlim(bounds[0] - 2000, bounds[2] + 2000)
        ax.set_ylim(bounds[1] - 2000, bounds[3] + 2000)

    sm = plt.cm.ScalarMappable(cmap='Greys', norm=plt.Normalize(vmin=0, vmax=vmax))
    sm.set_array([])
    cbar_ax = fig.add_axes([0.25, 0.11, 0.5, 0.03])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')
    cbar.ax.tick_params(labelsize=11)
    cbar.set_label('Total estimated votes', fontsize=16, labelpad=10)

    plt.suptitle(
        f'U.S. House Total Votes by 2026 District\n'
        f'{county_name.title()} County — 2016 to 2024',
        fontsize=18, fontweight='bold', y=1.02,
    )
    plt.savefig(f'{save_dir}/{county_slug}_house_turnout_maps.png',
                dpi=150, bbox_inches='tight')
    plt.show()
    return fig
