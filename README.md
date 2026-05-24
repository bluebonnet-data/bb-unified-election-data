# Bluebonnet Unified Election Data

When states redraw their political maps, directly comparing election results across cycles becomes challenging. You are looking at different slices of the population each time. A district might appear more Republican or Democratic simply because different neighborhoods got added or removed, not because of any real shift in how people voted.

This project will translate past election results onto current maps so campaigns can see how any district or neighborhood has genuinely trended over time. We are starting with Texas, where a 2025 mid-decade redraw created an urgent need for exactly this kind of historical context.


## Why this matters

By standardizing historical votes onto today's exact district and precinct boundaries, this pipeline gives campaigns three vital advantages:

- Unmasking map changes: Quantifies exactly who a new map helps or hurts before a single new ballot is cast.
- Neighborhood-level trends: Bypasses years of messy, shifting precinct lines to reveal clear, multi-cycle political trajectories for stable geographic communities.
- Resource precision: Stops campaigns from wasting limited time and money based on obsolete boundaries, shifting field strategy from guesswork to evidence-backed analysis.

## Who this is for

- Congressional Campaigns: Track true multi-cycle performance instantly within newly redrawn lines.
- Down-Ballot Campaigns: Pinpoint your baseline neighborhoods and high-leverage persuasion zones to protect tight budgets.
- Field Directors & Organizers: Prioritize door-knocking lists using true precinct trajectories, not un-adjusted historical data.

## Two things we are building

### District-level analysis [In Progress]
Simulates past election results using current congressional boundaries to establish a true historical baseline.

### Neighborhood-level analysis [Planned]
Tracks localized political trajectories across multiple cycles, independent of shifting precinct lines.

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
