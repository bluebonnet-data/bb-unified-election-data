# Bluebonnet Unified Election Data

When states redraw their political maps, directly comparing election results across cycles becomes challenging. You are looking at different slices of the population each time. A district might appear more Republican or Democratic simply because different neighborhoods got added or removed, not because of any real shift in how people voted.

This project aims to translate past election results onto current maps so campaigns can see how any district or neighborhood has genuinely trended over time. We are starting with Texas, where a 2025 mid-decade redraw created an urgent need for exactly this kind of historical context.

📄 **Project explainer:** https://bluebonnet-data.github.io/bb-unified-election-data/onepager.html
📊 **Where we stand:** https://bluebonnet-data.github.io/bb-unified-election-data/where_we_stand.html

## Current status

**236 of 254 Texas counties** have U.S. House results (2016 to 2024) translated onto the 2026 congressional map. Every county passes a vote leakage check, and all of it is committed to `data/processed/`.

A batch runner takes any county through the full pipeline in one command. A precinct ID reconciler handles the ID mismatches between election results and boundary files that were silently dropping votes, which took the review pile from 47 counties down to 8.

[Where we stand](https://bluebonnet-data.github.io/bb-unified-election-data/where_we_stand.html) has the full picture, including the open question about whether district level is granular enough.

## What is next

* **[#13] A front end** to explore the dataset. Front end and data viz, a creative eye. Ideas welcomed.
* **[#14] The last 8 counties** with precinct IDs the reconciler could not match.
* **[#9] Precinct level**, the neighborhood view. The method is proven; the question is scale.

## Getting started

```
pip install -r requirements.txt
```

Process a single county:

```
python scripts/run_all_counties.py --county TRAVIS
```

Generate figures for a county from its saved data:

```
python scripts/plot_county.py travis 453
```

## Repo structure

| Path | Contents |
|---|---|
| `data/raw/` | Boundary shapefiles, census blocks, raw election results |
| `data/processed/` | One time series and weights table per county |
| `scripts/` | Pipeline (`pipeline_utils.py`), batch runner (`run_all_counties.py`), figures (`plot_county.py`), validation (`health_check.py`) |
| `notebooks/` | Step by step walkthroughs |
| `docs/` | Methodology, project pages, generated figures |

## Contributing

Async first, one to three hours a week. Python, GIS, front end, or docs all welcome. Read CONTRIBUTING.md, then pick something from the Issues tab.
