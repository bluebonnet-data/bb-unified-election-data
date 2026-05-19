# Bluebonnet Unified Election Data — Spatial Continuity Engine

## What this project does

When legislative boundaries change after redistricting, the link between 
historical votes and geographic regions breaks. This project builds a 
data pipeline that fixes that problem.

Using U.S. Census block-level population data as weights, we precisely 
map past election results onto new district lines — so that comparisons 
across election cycles remain accurate even as boundaries shift.

We are starting with a pilot in Travis County, TX, then scaling statewide.

## The three phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | Spatial Harmonization Pilot (Travis County) | In progress |
| 2 | Statewide Scaling Engine (all 254 TX counties) | Not started |
| 3 | Power Shift Navigator (strategic dashboard) | Not started |

## Repo structure
## Getting started

```bash
# 1. Clone the repo
git clone https://github.com/bluebonnet-data/bb-unified-election-data

# 2. Move into the folder
cd bb-unified-election-data

# 3. Install dependencies
pip install -r requirements.txt
```

## How to contribute

This is a 100% volunteer project. Read `CONTRIBUTING.md` before you start — 
it explains how we work asynchronously and how to pick up a task.

All open tasks are in the [Issues tab](../../issues). Filter by label to find 
something that matches your skills.
