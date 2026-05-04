# Campaign Repository

This repository was created by the [Bluebonnet Data Project Hub](https://hub.bluebonnetdata.org) to support a campaign data project.

# Unified Election Data

## Project Overview
This project will provide the database, mapping tools, and analysis to quantify the impact on precinct-level composition after redistricting. Initially focused on the Texas, this project will be designed as a scalable framework for national election data standardization.

## The Problem
Election results and legislative boundaries are fragmented. Because precinct shapes and district lines change at different intervals, it is difficult to perform accurate historical comparisons. This project aims to solves this by ...

## Background 
For a full list of research and methodology papers, see our [Reading List](./docs/reading-list.md).

--------------------------
## Getting Started

1. Clone this repo and start building in the `src/` directory
2. Put raw data files in `data/` and documentation in `docs/`
3. Update the `.project-status.yml` file as your project evolves

## Project Status YAML

The `.project-status.yml` file in the root of this repo powers the Project Hub dashboard. It tracks what your project does, what the team is working on, and what help is needed.

The hub automatically syncs whenever this file changes. You can edit it manually, or let the AI auto-updater keep it current based on your commits.

### Key fields

- **name** / **description** — What this project is
- **tools** — Technologies and data sources you're using
- **current_focus** — What the team is actively working on
- **needs** — Action items where volunteers can help (code review, testing, design, etc.)
- **team** — Lead and contributors (GitHub usernames)
- **campaign** — Candidate name and office/race

### AI Auto-Updates

The Project Hub uses AI to automatically update this file when you push code changes. It analyzes your commits and adjusts fields like `current_focus`, `tools`, and `needs` to keep the dashboard accurate.

**To opt out of AI updates**, set `auto_refresh: false` in your YAML:

```yaml
project:
  auto_refresh: false
```

The AI will never change the `auto_refresh` field itself — it respects your choice.
