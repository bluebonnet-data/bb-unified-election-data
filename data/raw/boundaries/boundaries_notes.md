# Boundary Data Notes

## 2020 Precinct Boundaries
- **Source:** Texas Legislative Council Capitol Data Portal
- **URL:** https://data.capitol.texas.gov/dataset/precincts
- **File:** precincts20g_2020.zip
- **Download date:** May 2026
- **CRS:** NAD 1983 Lambert Conformal Conic
- **Total precincts (statewide):** 9,014
- **Travis County precincts:** 247
- **Key fields:** CNTY (county code), PREC (precinct name), PCTKEY (unique ID)
- **Notes:** CNTY field is numeric. Travis County code is 453.

## 2026 Congressional District Boundaries (PlanC2333)
- **Source:** Texas Legislative Council Capitol Data Portal
- **URL:** https://data.capitol.texas.gov/dataset/planc2333
- **File:** PLANC2333.zip
- **Download date:** May 2026
- **CRS:** NAD 1983 Lambert Conformal Conic (matches precinct file exactly)
- **Total districts:** 38
- **Districts touching Travis County:** 7 (Districts 10, 11, 17, 21, 27, 31, 37)
- **Key fields:** District (district number)
- **Notes:** Shapefile is nested inside PLANC2333/ subfolder within the zip.
  Load with: gpd.read_file('zip://path/PLANC2333.zip!PLANC2333/PLANC2333.shp')
- **Legal status:** PlanC2333 enacted by 89th Legislature, 2nd C.S., 2025.
  Subject to ongoing litigation as of early 2026; U.S. Supreme Court stay
  in effect keeping PlanC2333 operative for 2026 elections.

## CRS Notes
Both files use identical CRS — no reprojection needed before spatial join.
