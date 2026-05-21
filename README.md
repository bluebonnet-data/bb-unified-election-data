# Bluebonnet Unified Election Data — Spatial Continuity Engine

## What this project does

When legislative boundaries change after redistricting, the link between historical votes and geographic regions breaks. This makes it impossible to accurately track how neighborhoods and districts shift politically over time — which is exactly what campaigns need to know.

This project builds a data pipeline that fixes that problem by using U.S. Census block-level population data to precisely remap historical election results onto new boundary lines. The result is a consistent, apples-to-apples view of how any geography has voted over time — regardless of how the maps have changed.

## Who this is for

- **US House campaigns** — understand how your district has trended across election cycles on a consistent map
- **Down-ballot campaigns** — see how specific neighborhoods and precincts have shifted over time, identify base vs persuadable vs lost-cause areas
- **Field organizers** — target the right precincts with the right message

## Two levels of analysis

### District level (Phase 1 — in progress)
Reconstruct past election results onto new congressional district boundaries. Answers: "How would District 37 have voted in 2016, 2018, 2020, 2022 if today's boundaries had existed?"

### Precinct level (Phase 2 — planned)
Reconstruct past election results onto a consistent precinct boundary map. Answers: "How has this specific neighborhood voted over the last four cycles and which direction is it moving?" This is the unit campaigns actually organize around.

## Current status

### Phase 1 pilot — Travis County, TX (active)

| Issue | Task | Status |
|-------|------|--------|
| #1 | Repo setup | Done |
| #4 | Boundary shapefiles | Done |
| #5 | Census block population data | Done |
| #6 | Spatial intersection engine | Done |
| #7 | Vote interpolation 2020 Presidential | Done |
| #8 | Methodology documentation | In progress |

Pilot result: 2020 Presidential results successfully interpolated onto 7 new congressional districts touching Travis County. Zero vote loss. Weights validated. See notebooks/04_vote_interpolation.ipynb.

### Next steps

- Add 2016, 2018, 2022, 2024 election cycles to build a time series
- Scale district-level engine to all 254 Texas counties
- Build precinct-level time series engine
- Build the Power Shift Navigator dashboard

## Repo structure

- `data/raw/boundaries/` — Precinct and district shapefiles
- `data/raw/census/` — Census block population data
- `data/raw/election_results/` — Raw election result files
- `data/processed/` — Analysis-ready outputs
- `docs/` — Methodology, scoping, reference reading
- `notebooks/` — Jupyter notebooks for exploration
- `scripts/` — Standalone Python scripts
- `tests/` — Validation and unit tests

## Getting started

1. Clone the repo: `git clone https://github.com/bluebonnet-data/bb-unified-election-data`
2. Move into the folder: `cd bb-unified-election-data`
3. Install dependencies: `pip install -r requirements.txt`

See `docs/` for methodology and `notebooks/` for step-by-step walkthroughs.

## How to contribute

Read `CONTRIBUTING.md` before starting. All open tasks are in the [Issues tab](../../issues).
