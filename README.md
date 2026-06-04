# Bluebonnet Unified Election Data

When states redraw their political maps, directly comparing election results across cycles becomes challenging. You are looking at different slices of the population each time. A district might appear more Republican or Democratic simply because different neighborhoods got added or removed, not because of any real shift in how people voted.

This project aims to translate past election results onto current maps so campaigns can see how any district or neighborhood has genuinely trended over time. We are starting with Texas, where a 2025 mid-decade redraw created an urgent need for exactly this kind of historical context.

📄 **Project overview:** https://bluebonnet-data.github.io/bb-unified-election-data/onepager.html

## Why this matters

By standardizing historical votes onto today's exact district and precinct boundaries, this pipeline gives campaigns three vital advantages:

- Unmasking map changes: Quantifies exactly who a new map helps or hurts before a single new ballot is cast.
- Neighborhood-level trends: Bypasses years of messy, shifting precinct lines to reveal clear, multi-cycle political trajectories for stable geographic communities.
- Resource precision: Stops campaigns from making decisions based on outdated geographic boundaries.

## Who this is for

- Congressional Campaigns: See true multi-cycle performance within newly redrawn district lines.
- Down-Ballot Campaigns: Pinpoint base neighborhoods and direct resources using current geography, not outdated maps.
- Researchers and Engaged Citizens: Pull up any district and see its full electoral history on today's map.

## Two things we are building

### District-level analysis [In Progress]
Simulates past election results using current congressional boundaries to establish a true historical baseline.

### Neighborhood-level analysis [Planned]
Tracks localized political trajectories across multiple cycles, independent of shifting precinct lines.

## Current status

### Phase 1 pilot - Travis County, TX (complete)

| Issue | Task | Status |
|-------|------|--------|
| #1 | Repo setup | Done |
| #4 | Boundary shapefiles | Done |
| #5 | Census block population data | Done |
| #6 | Spatial intersection engine | Done |
| #7 | Vote interpolation 2020 Presidential | Done |
| #8 | Methodology documentation | Done |

2020 Presidential results successfully mapped onto 7 new congressional districts touching Travis County with zero vote leakage. Travis County's redistricting impact quantified — District 35 (38% Travis County) eliminated and District 11, the district with the next largest Travis County footprint (19%). See notebooks/04_vote_interpolation.ipynb.

### Next steps

- Add 2016, 2018, 2022, 2024 election cycles to build a time series (Issue #10)
- Build precinct-level time series on consistent boundaries (Issue #9)
- Scale district-level engine to a second Texas county (Issue #11)
- Design statewide scaling architecture for all 254 counties (Issue #12)
- Build the Unified Election Data Project dashboard

## Repo structure

- data/raw/boundaries: Precinct and district shapefiles (map boundary files)
- data/raw/census: Census block population data
- data/raw/election_results: Raw election result files
- data/processed: Analysis-ready outputs
- docs: Methodology, scoping, reference reading
- notebooks: Jupyter notebooks for exploration
- scripts: Standalone Python scripts
- tests: Validation and unit tests

## Getting started

1. Clone the repo
2. Move into the folder
3. Run: pip install -r requirements.txt

See docs/ for methodology and notebooks/ for step-by-step walkthroughs.

## How to contribute

Read CONTRIBUTING.md before starting. All open tasks are in the Issues tab.
