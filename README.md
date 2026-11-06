# BT5110 LeTour
## Project Structure

```text
BT5110-LeTour/
├── data/                        (git-ignored; add the three CSVs)
├── docs/task3/                  UI spec, OLAP narratives, design mockups, app_screenshots/
├── docs/task4/                  Benchmark results (normalised vs star schema)
├── src/
│   ├── data_loading.ipynb       Original loader, with its checks shown step by step
│   ├── loading.py               The same loading logic for the command line
│   ├── init_db.py               Rebuilds the database with one command
│   ├── benchmark.py             Task 4: times the paired queries on both schemas
│   ├── screenshots.py           Saves a screenshot of every dashboard page
│   ├── sql/
│   │   ├── schema.sql           Normalised tables
│   │   ├── drop_tables.sql, truncate_tables.sql, drop_analytics.sql
│   │   ├── views/*.sql          All analytics: views and fn_* functions
│   │   ├── star/*.sql           Task 4 star schema (schema "star") and its ETL
│   │   └── queries/{normalized,star}/  The same four queries on each schema
│   └── dashboard/
│       ├── app.py               Streamlit entry point
│       ├── pages/*.py           One file per page
│       └── lib/                 Database access, queries, filters, charts, formats
├── tests/                       SQL tests and a smoke test of every page
├── .env.example
└── requirements.txt
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/chiabingxuan/BT5110-LeTour.git
cd BT5110-LeTour
```

### 2. Set up the Python environment

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows (PowerShell):

```powershell
.\venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies (Python 3.11 or newer, because of the pinned pandas):

```bash
pip install -r requirements.txt
```

### 3. Set up PostgreSQL

Make sure PostgreSQL is installed and running.

Nothing else is needed here: step 6 creates the `LeTour` database and its tables.

### 4. Configure environment variables

Copy `.env.example` to `.env` in the project root and fill it in:

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=LeTour
DB_USER=postgres
DB_PASSWORD=your_password
```

Replace the values with your local PostgreSQL configuration. In particular, your PostgreSQL port may be `5432` instead of `5433`.

### 5. Add the datasets

Create a `data/` folder in the project root if it does not exist, and place the following files inside:

```text
riders.csv
individual_results.csv
exits.csv
```

### 6. Build the database

```bash
python src/init_db.py
```

This creates the database if needed, then rebuilds the tables, loads the CSVs, creates every view and loads the star schema. It deletes what is in the `LeTour` tables first. To recreate only the views and keep the data, use `python src/init_db.py --views-only`.

You don't normally need `--views-only` after a `git pull`: when the dashboard starts, it checks whether the SQL view files changed since they were installed and rebuilds the views itself, without touching the race data.

`src/data_loading.ipynb` still works if you want to walk through the cleaning and checks. Run it from `src/`, on empty tables.

### 7. Run the dashboard

```bash
streamlit run src/dashboard/app.py
```

Run it from the repository root, so that the theme in `.streamlit/config.toml` applies.

### 8. Run the tests

```bash
python -m pytest tests
```

## Task 4: star schema and benchmark

`python src/init_db.py` also builds a star schema in its own PostgreSQL schema, `star`: `fact_results` (one row per rider per stage, with `adjusted_time` stored) and the dimensions `dim_rider`, `dim_team`, `dim_stage`, `dim_country` and `dim_date`. The dashboard does not read it.

```bash
python src/benchmark.py --runs 200
```

This checks that each query pair in `src/sql/queries/` returns identical rows, then writes the median planning and execution times from `EXPLAIN (ANALYZE)` to `docs/task4/benchmark.csv` and `docs/task4/benchmark.md`.

To refresh the screenshots in `docs/task3/app_screenshots/`, start the dashboard, then run:

```bash
playwright install chromium
python src/screenshots.py
```

## Where each requirement lives

The dashboard tells one story, from a team manager's point of view: pick **My team** (default UAE Team Emirates XRG) and its **Rivals** (default: the three best other teams in Best Team) in the sidebar, and every chart colours them (ours in a bold accent, rivals in teal, the rest grey). Each section opens with a chart and a one-line takeaway computed from the data; tables sit behind **Show data** or in drill-downs.

| Chapter (page) | Visuals | Requirements and narratives |
|---|---|---|
| 1 · Where do we stand (Overview) | Team KPI tiles with change since the previous stage, GC storyline with our riders highlighted, route strip, leaders | E10, c |
| 2 · Our leader vs the rivals (GC) | Our leader against the rival leaders by stage with the pivotal stage, slope chart of top-10 movement, classification dot plot | E1, E7, E4, a, b, c |
| 3 · Team strength (Teams) | Best Team gap to the leading team after every stage, top-10 heatmap of team × stage type with drill-down | c (Best team), E14, a |
| 4 · Where we win and lose (Stages) | Mountain podiums vs mean gap scatter with rider drill-down, stage top 10 as a lollipop and squads bar, time-trial dot strip | E5, E2, E11, a |
| 5 · Scouting (Nations) | Rider map, riders and teams per country, country drill-down, young prospects outside our team | E8, d, a |
| Rider profile, Time trials | Detail pages reached from the chapters | a |

Requirement e (design and presentation) is the storyline itself, the team colours and one colour per stage type everywhere.

The group presents E1, E2, E4, E5, E7, E8, E10, E11 and E14, plus E3's Best team table for requirement (c). E3's drill-down, E6, E9, E12, E13 and E15 are built but hidden: set one to `True` in `src/dashboard/lib/features.py` to show it again.

## Assumptions

- **Points and King of the Mountains are derived.** The schema stores no points, so both come from stage finishing positions, using the scales in `v_points_scale` (`src/sql/views/03_classifications.sql`). This is not the official scoring: the data has no intermediate sprints or categorised climbs. The derived KOM leader matches the official winner (Pogačar). The derived Points leader (Pogačar) does not match the official winner (Milan).
- **Young rider** defaults to age at race start (5 Jul 2025) under 26, with the cutoff adjustable. The official rule, born on or after 1 Jan 2000, is a switch on chapter 2, Our leader vs the rivals. Only the official rule gives the official podium; the age rule also admits Tobias Johannessen, who places 3rd.
- **Pivotal moment** is the stage with the largest swing in a rider's gap to the GC leader; ties go to the bigger rank change, then the later stage.
- **GC ties** are broken by the lower sum of stage placings so far, then the better placing on the latest stage, in every replay as well.
- **Top-10 finishes** count every rider, so two riders from one team on one stage count 2.
- **The views keep themselves current.** The app compares a fingerprint of `src/sql/views/` with the one stored in the database and rebuilds the views when they differ.

## Known data notes

- Total times run about 1h02 above the official figures for every rider, so all gaps are exact and match the official top 10.
- Total distance in the data is 3,302 km, against the official 3,338.8 km.
- `countries.iso` holds the race's codes (SLO, GER, NED…), not strict ISO 3166-1 alpha-3. The dashboard's map translates them.

## Resetting the Database

`python src/init_db.py` rebuilds everything. To do it by hand, run `src/sql/drop_analytics.sql` first, because the views depend on the tables, then `src/sql/drop_tables.sql` and `src/sql/schema.sql`. `src/sql/truncate_tables.sql` clears the records and keeps the tables.
