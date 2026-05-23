# Bluebonnet Unified Election Data

When states redraw their political maps, directly comparing election results across cycles becomes challenging. You are looking at different slices of the population each time. A district might appear more Republican or Democratic simply because different neighborhoods got added or removed, not because of any real shift in how people voted.

This project translates past election results onto current maps so campaigns can see how any district or neighborhood has genuinely trended over time. We are starting with Texas, where a 2025 mid-decade redraw created an urgent need for exactly this kind of historical context.


## Why this matters

When election boundaries change, tracking political trends over time breaks down. This pipeline aims to fix that by re-sorting historical votes into today's brand-new district and precinct lines.

This gives campaigns three vital advantages:

- Unmasking map changes: provides evidence of exactly who a new map helps or hurts before a single new ballot is cast.
- Neighborhood trends: bypasses years of messy, shifting county precinct lines to reveal clear, multi-cycle political trendlines for those living in those neighborhoods today.
- Resource precision: stops campaigns from wasting limited time and money based on outdated maps, shifting field strategy from guesswork to data-backed analysis.

## Who this is for

- US House campaigns: see how your district has voted across multiple election cycles on a consistent map
- Down-ballot campaigns (state house, city council, school board): understand which neighborhoods are your base, which are persuadable, and which are not worth the resources
- Field organizers: know which precincts to prioritize before you knock a single door

## Two things we are building

### District-level analysis (in progress)
What would past elections have looked like under today's congressional boundaries?

### Neighborhood-level analysis (planned)
How has a specific precinct trended across the last four election cycles?

## Current status

### Phase 1 pilot - Travis County, TX (active)

| Issue | Task | Status |
|-------|------|--------|
| #1 | Repo setup | Done |
| #4 | Boundary shapefiles | Done |
| #5 | Census block population data | Done |
| #6 | Spatial intersection engine | Done |
| #7 | Vote interpolation 2020 Presidential | Done |
| #8 | Methodology documentation | In progress |

Pilot result: 2020 Presidential results successfully translated onto 7 new congressional districts touching Travis County. All votes accounted for. See notebooks/04_vote_interpolation.ipynb.

### Next steps

- Add 2016, 2018, 2022, 2024 election cycles to build a time series
- Scale district-level engine to all 254 Texas counties
- Build neighborhood-level time series engine
- Build the Power Shift Navigator dashboard

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
