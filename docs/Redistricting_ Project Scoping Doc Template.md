*![][image1]*

# Bluebonnet Fellowship Partner Project Scoping Doc

Please try to provide detailed outlines for around 2-4 projects below. This should take anywhere from 30 minutes to a couple hours.

 Please provide input for each section and get all of your thoughts on paper, then we will help refine it and prepare it for fellows. You may have more or less than 3 projects, that’s fine, just edit this doc as needed.

You should reference this document for ideas on common Bluebonnet projects: [Bluebonnet Data Common Projects Guide](https://docs.google.com/document/d/1EJTd0RUPNDCPFW0TgSPTDxjsDHwkhB7vDstU5yhEIJQ/edit)

To see an example of a scoped Bluebonnet project, see here: [EXAMPLE: Scoped Project](https://docs.google.com/document/d/1_IAA6y-fv1hhi5XOFoA9ToBC2JryQuPfEKiVaTYoY_o/edit#heading=h.ymjovzpf1o3z)

Elevator Pitch  
We are building a data tool that can quickly and easily map past election results onto brand new district lines (or other given regions) so we can see how voting patterns are actually changing. 

Redistricting often makes it difficult to track how neighborhoods are actually changing because new map lines no longer match up with old election results. This tool will solve that problem by precisely mapping historical data onto future district lines using neighborhood level census data. This approach ensures that political trends remain granular and accurate, even as the boundaries around voters continue to shift.

The Projects Roadmap:

1. Pilot: validate the methodology in a high-impact county to establish a statistical gold standard.  
2. Limited Product: scale this to a modular system covering all 254 Texas counties.  
3. Final Product: launch an easy-to-use database (or other interface) across multiple states.

# 

# **PROJECT 1: \<The Spatial Continuity Pilot\>**

---

## **Project Context, Overview, & Goals:**

This pilot does two things in a single Texas county: validate the methodology for mapping past election results onto new district lines, and produce the first version of the crosswalk table that Projects 2 and 3 are built on. Redistricting often bisects existing voting precincts (VTDs), forcing analysts to estimate how historical votes should be allocated to new districts. Standard land area weighting is often inaccurate because it assumes voters are distributed evenly across a precinct, a false assumption that leads to significant Proration Error. This pilot will test the hypothesis that using Census Blocks as the atomic unit of analysis provides a statistically superior view of voter behavior compared to land area estimates. The crosswalk produced here is the core data product of the broader tool. The schema, keys, and access pattern defined in this pilot are inherited by every downstream use case, so it’s critical to define them well.

Key Technical Definitions:

* **VTD (Voting Tabulation District)**: A geographic boundary created by the Census Bureau that approximates a local voting precinct. While the Census does not report election results, VTDs are designed to follow Census Block lines, making them the essential geographic bridge between county election returns and census demographic data.  
* **Geospatial Crosswalk**: A relational lookup table that links disparate geographic layers like Census Blocks to VTDs to Legislative Districts.  
* **Areal Interpolation**: The statistical method being evaluated here to estimate values from one geographic shape into another based on shared overlapping areas.  
* **Proration Error**: The statistical discrepancy caused by incorrectly allocating data from one geographic shape to another.

Measurable Objectives:

* **Methodology Evaluation**: Implement population weighted Areal Interpolation and prove it reduces proration error compared to land area weighting.  
* **Define the Partisan Index**: Establish a composite baseline, such as a weighted average of 2022 to 2024 top of ticket races, to be used for all future Delta calculations.  
* **Establish Audit Tolerance**: Define a statistical pass or fail threshold, such as 0.5 percent, for validating aggregated block level votes against official top down county totals.

## **Key Deliverable(s):**

- **Relational Crosswalk Table**: A master translator dataset that links Census Block IDs to their past 2024 voting precincts and their new 2026 legislative districts.  
- **The Methodology Playbook**: A Standard Operating Procedure that ensures any rotating fellow can replicate the pilot logic in a new county without reinventing the workflow.  
- **Methodology Validation Brief**: A document quantifying the accuracy gain or limitations of the population weighted approach.

## **Existing Work & Stakeholders:**

Stakeholders: Bluebonnet Data.

Current Status: Theoretical methodology is established for evaluation. Fellows are responsible for data acquisition, pilot county selection justification, and technical implementation.

## 

## **Timeline:**

* Week 1: County Selection and Data Acquisition. Fellows identify and justify a high impact pilot county and extract raw returns and shapefiles.  
* Week 2 to 3: Geometry Alignment. Execution of the spatial intersection between VTDs, Census Blocks, and Districts.  
* Week 4: Calculation and Audit. Weighting vote totals by block population and auditing against official county totals.  
* Week 5: Evaluation and Review. Finalizing the methodology brief and Playbook to ensure the approach is ready for team wide scaling.

## **Data Sources and Tools**

* Datasets:   
  * Texas Secretary of State: Provides the raw election returns (the vote counts) for every precinct in the state.  
  * Texas Legislative Council: Provides the official digital maps (shapefiles) for both the old 2024 precincts and the new 2026 district boundaries.  
  * U.S. Census Bureau (PL 94-171): Provides the high-resolution population counts at the neighborhood block level, which we use to accurately move votes from old maps to new ones.  
* Tools: Fellows will evaluate and propose the technical stack such as PostGIS, BigQuery GIS, or Python based spatial libraries.

---

## **TECH ADVISING – FOR BLUEBONNET**

*This is intended for Bluebonnet, but you’re welcome to contribute if you’d like*

## 

### Data Sourcing and Collection

*The primary challenge is the Join Key problem. Fellows must resolve inconsistencies between county reported precinct names and state issued VTD codes. This requires rigorous data cleaning and string normalization to ensure geographic IDs align perfectly with election return IDs.*

### Suggested Methods

*Apply Population Weighted Areal Interpolation using the PL 94 171 Census dataset to refine the distribution of votes.*

### 

### Skills Required of Fellows

* *Spatial SQL / GIS: Proficiency with spatial joins and coordinate reference systems.*  
* *Data Engineering: Experience in cleaning messy datasets and performing bottom up data validation.*  
* *String Manipulation: Comfort with Regex or Fuzzy Matching to handle non standardized naming conventions.*  
* *Technical Documentation: Ability to write clean code and operating procedures that allow rotating team members to pick up work seamlessly.*

### Project Summary (for matching)

*A geospatial engineering project to evaluate a population weighted crosswalk for election data. Fellows will harmonize fragmented Texas results with Census level geometry to test if this approach enables more accurate analysis across changing legislative boundaries, while creating documentation for long term team continuity.*

# **PROJECT 2: \<THE STATEWIDE SCALING ENGINE\>**

---

## **Project Context, Overview, & Goals:**

This project builds the automated pipeline required to scale the validated spatial harmonization logic to all 254 Texas counties. While the pilot proves the theory, this project is an engineering challenge of massive scale. Texas election data is a fragmented landscape of various formats including PDFs, HTML tables, and inconsistent CSVs. The goal is to build a resilient, production grade ingestion engine that transforms this chaos into a single, unified source of truth. This is an opportunity for fellows to architect a statewide data infrastructure from the ground up.

Key Technical Definitions:

* **ETL (Extract, Transform, Load)**: The three stage process of pulling raw data from disparate sources, cleaning it, and loading it into a final database.  
* **Fuzzy Matching**: A technique used to identify and match strings such as precinct names that are similar but not identical.  
* **Schema Standardization**: Creating a uniform structure for data so that results from different counties can be merged seamlessly.  
* **Technical Debt**: The future cost of rework caused by choosing an easy but messy solution now instead of a better, well documented approach.

Measurable Objectives:

* **Tiered Ingestion**: Design and execute a workflow to ingest election reports, prioritizing the Top 15 most populous counties to cover the majority of the state voter population early.  
* **Automated Normalization**: Build a Fuzzy Matching library to resolve the naming discrepancies between county level reports and state level VTD codes.  
* **System Resiliency**: Develop the engine to be map agnostic, allowing users to swap between State House, Senate, or Congressional boundaries without rewriting the code.

## **Key Deliverable(s):**

- **Unified Election Database**: A centralized SQL based repository housing standardized, harmonized results for the entire state.  
- **The Ingestion Playbook**: A modular set of scripts and documentation that allows the engine to be maintained and updated as new election cycles occur.  
- **Data Integrity Dashboard**: A tracker for leadership to monitor ingestion status and quality control across all 254 counties.

## **Existing Work & Stakeholders:**

Stakeholders: Bluebonnet Data.

Current Status: The technical blueprint is established by the Project 1 pilot. Fellows have autonomy to design the scaling architecture and manage the statewide data acquisition.

## 

## **Timeline:**

* Weeks 1 to 4: Priority 1 Sourcing. Identifying and extracting data for the 15 largest counties.  
* Weeks 5 to 8: Pipeline Automation. Developing the core logic to standardize and harmonize the first tier of counties and beginning the expansion to mid sized counties.  
* Weeks 9 to 12: The Long Tail. Automating the remaining rural counties and finalizing the statewide database.

## **Data Sources and Tools**

* Datasets:   
  * Texas Secretary of State Archives: Provides the certified official totals for the entire state used as our final source of truth to ensure scaled numbers match official records.  
  * Individual County Clerk Websites: Provides the granular precinct level reports that often come in messy formats like PDFs or HTML tables and require specialized extraction tools.  
  * OpenElections Repositories: Provides a volunteer cleared head start where some Texas counties have already been cleaned and standardized to save time.  
* Tools: Fellows will propose and build the stack. Recommended tools include Python with Pandas or GeoPandas, SQL using BigQuery or PostGIS, and GitHub for version control.

---

## **TECH ADVISING – FOR BLUEBONNET**

*This is intended for Bluebonnet, but you’re welcome to contribute if you’d like*

## 

### Data Sourcing and Collection

*The challenge here is the lack of digital standardization across 254 counties. Some data will require scraping, while others may require Optical Character Recognition for PDFs. Fellows must solve for the Join Key problem across varying reporting conventions.*

### Suggested Methods

*Implement a tiered scaling strategy to cover the 15 largest counties first to achieve 70 percent population coverage, then move to the competitive districts. Use modular code so that cleaning scripts for one county can be easily adapted for another.*

### 

### Skills Required of Fellows

* *Data Engineering: Strong experience in ETL pipelines and database architecture.*  
* *Python and SQL: Mastery of data manipulation and relational database management.*  
* *Fuzzy String Matching: Proficiency in Regex or string matching libraries to resolve naming inconsistencies.*  
* *System Architecture: Ability to think about how a data system lives and grows over an entire election year.*

### Project Summary (for matching)

*A high level data engineering project to build a statewide automated pipeline. Fellows will scale a validated pilot methodology to all 254 Texas counties, transforming a fragmented data landscape into a clean, unified infrastructure for statewide election analysis.*

# **PROJECT 3: \<The Power Shift Navigator\>**

---

## **Project Context, Overview, & Goals:**

This project builds the analytical interface that quantifies how political power and demographics shifted as a result of redistricting. While the previous projects focused on the data engineering plumbing, Project 3 focuses on the strategic insight. By comparing the harmonized historical data against the new district lines, we can identify the Delta, which is the exact change in the partisan lean or demographic makeup of a district. The goal is to provide a tool that allows non-technical users to see if a neighborhood is trending in a certain direction, independent of how the lines were redrawn around them.

Key Technical Definitions:

* **Delta Analysis**: The process of measuring the specific change between two data points, in this case, comparing the political performance of an old district versus a new district.  
* **Longitudinal Trendlines**: Visual representations that track data over time across a consistent geographic unit, even when political names or numbers change.  
* **Partisan Lean**: A calculated metric that describes the baseline political orientation of a geographic area based on a weighted average of past election results.  
* **User Interface (UI)**: The space where interactions between humans and the data occur; in this project, it is the dashboard or reporting tool used by stakeholders.

**Measurable Objectives**:

* **Define the Delta Logic**: Formalize the math for calculating the partisan and demographic shift for every redrawn district in Texas.  
* **Visualize Continuity**: Build a dashboard that allows users to search for a neighborhood and view its multi cycle political history projected onto 2026 boundaries.  
* **Actionable Reporting**: Generate summary reports that highlight the most significantly shifted districts in the 2026 map cycle to identify areas of unexpected political change.

## **Key Deliverable(s):**

- **Impact Analysis Dashboard**: An interactive tool where users can toggle between different election cycles and see the results projected onto current boundaries.  
- **The Shift Report**: A summary document or data visualization identifying the top 20 districts where redistricting most significantly altered the partisan baseline.  
- **Stakeholder Documentation**: A guide for non technical users explaining how to interpret the harmonized data for strategic decision making.

## **Existing Work & Stakeholders:**

Stakeholders: Bluebonnet Data and their partner organizations.

Current Status: This project relies on the standardized output from Project 2\. Fellows are responsible for the front end design, the analytical math of the Delta, and the overall user experience.

## 

## **Timeline:**

* Weeks 1 to 3: Design and Requirement Gathering. Fellows interview potential users to determine which metrics, such as turnout versus partisan split, are most critical to visualize.  
* Weeks 4 to 6: Analytical Build. Writing the queries to calculate shifts and trends from the Project 2 database.  
* Weeks 8 to 10: Tool Launch and Handover. Finalizing the interface and presenting the impact findings to leadership.

## **Data Sources and Tools**

* Datasets: The standardized and harmonized election results produced in Projects 1 and 2\.  
* Tools: Fellows will evaluate and propose the best platform for data storytelling and visualization, such as Hex, Streamlit, or interactive SQL backed dashboards.

---

## **TECH ADVISING – FOR BLUEBONNET**

*This is intended for Bluebonnet, but you’re welcome to contribute if you’d like*

## 

### Data Sourcing and Collection

*This project is an internal consumer of the previous projects. The primary challenge is not getting the data, but structuring it for high speed visualization and ensuring the math behind the partisan shifts is rigorous and defensible.*

### Suggested Methods

*Focus on comparative visualization by using side by side maps or before and after metrics to show the impact of redistricting. Ensure that all demographic data is normalized to the same year as the election results to avoid data lag.*

### 

### Skills Required of Fellows

* *Data Storytelling: The ability to take complex geospatial data and make it understandable for non technical users.*  
* *Advanced Analytics: Comfort with calculating deltas, percentages, and trendlines across multi dimensional datasets.*  
* *UI/UX Design: Ability to build clean, intuitive interfaces that do not overwhelm the user with too much data at once.*

### Project Summary (for matching)

*A data visualization and strategic analysis project to quantify the impact of redistricting. Fellows will build the interface that translates harmonized election data into actionable insights, allowing users to see exactly how power and demographics shifted across Texas between map cycles.*

[image1]: <data:image/png;base64,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>