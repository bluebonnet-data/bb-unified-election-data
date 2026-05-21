# Census Data Notes

## 2020 Census P.L. 94-171 Redistricting File — Texas
- **Source:** U.S. Census Bureau
- **URL:** https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/Texas/
- **File:** tx2020.pl.zip (95MB)
- **Download date:** May 2026
- **Key file:** tx000012020.pl (population table), txgeo2020.pl (geography)
- **Population field:** Column 5 (P0010001) = total population
- **Geography field:** LOGRECNO links population table to geo file

## Travis County Summary
- **FIPS code:** 453
- **Summary level for blocks:** SUMLEV = 750
- **Total blocks:** 16,906
- **Total population:** 1,290,188
- **Processed file:** /data/processed/travis_census_blocks_2020.csv

## Notes
- Population counts are exact 2020 Census counts (not estimates)
- Some blocks have zero population (commercial areas, parks, etc.)
- This data was designed specifically for redistricting work

## Census Block Geometries (TLC)
- **Source:** Texas Legislative Council Capitol Data Portal
- **URL:** https://data.capitol.texas.gov/dataset/2020-census-geography
- **File:** Blocks.zip (371MB — too large for GitHub, download manually)
- **Also download:** Blocks_Pop.zip (30MB — already in repo)
- **Instructions:** Download Blocks.zip, save to `/data/raw/census/`
- **Note:** Blocks.zip contains block geometries for all of Texas.
  Filter to Travis County using CNTY == '453'

## Processed Output
- **File:** `/data/processed/travis_blocks_2020.gpkg`
- **Contains:** 16,906 Travis County census blocks with geometry and 
  population counts (total, anglo, asian, hisp, black)
- **This file is in the repo** — you only need Blocks.zip if you want 
  to re-run the processing from scratch
