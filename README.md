# BT5110 LeTour
## Project Structure

```text
BT5110-LeTour/
├── data/                        (git-ignored; add the three CSVs)
├── docs/task3/                  UI spec, OLAP narratives, design mockups
├── src/
│   ├── data_loading.ipynb       Original loader, with its checks shown step by step
│   ├── loading.py               The same loading logic for the command line
│   ├── init_db.py               Rebuilds the database with one command
│   ├── sql/
│   │   ├── schema.sql           Normalised tables
│   │   ├── drop_tables.sql, truncate_tables.sql, drop_analytics.sql
│   │   └── views/*.sql          All analytics: views and fn_* functions
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

This creates the database if needed, then rebuilds the tables, loads the CSVs and creates every view. It deletes what is in the `LeTour` tables first. After changing only the SQL views, use `python src/init_db.py --views-only`, which keeps the data.

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

## Where each requirement lives

| Requirement | Page and visual |
|---|---|
| a. Drill-down | E1 GC standing, E2 Stage in focus, E3 Teams, E5 Riders, E8 and E9 Nations, E14 Teams cell drill |
| b. Classification comparison | GC & Classifications › Parallel classifications |
| c. Aggregate performance | E1 GC leaderboard, E3 Best team, E7 counterfactuals, E10 GC storyline |
| d. Country participation | Nations › Riders per country, Teams per country |
| e. Design and presentation | Design system in `docs/task3/ui_spec.md`; one colour per stage type everywhere |
| E1, E4, E7 | GC & Classifications |
| E2, E15 | Stages |
| E3, E13, E14 | Teams |
| E5, E6, E12 | Riders |
| E8, E9 | Nations |
| E10 | Overview |
| E11 | Time Trials |

## Assumptions

- **Points and King of the Mountains are derived.** The schema stores no points, so both come from stage finishing positions, using the scales in `v_points_scale` (`src/sql/views/03_classifications.sql`). This is not the official scoring: the data has no intermediate sprints or categorised climbs. The derived KOM leader matches the official winner (Pogačar). The derived Points leader (Pogačar) does not match the official winner (Milan).
- **Young rider** defaults to age at race start (5 Jul 2025) under 26, with the cutoff adjustable. The official rule, born on or after 1 Jan 2000, is a switch on the GC page. Only the official rule gives the official podium; the age rule also admits Tobias Johannessen, who places 3rd.
- **Pivotal moment** is the stage with the largest swing in a rider's gap to the GC leader; ties go to the bigger rank change, then the later stage.
- **Yellow jersey ties** are broken by the lowest sum of stage placings.
- **Top-10 finishes** count every rider, so two riders from one team on one stage count 2.
- **After changing SQL views**, every group member must run `python src/init_db.py --views-only`, or the app will not find new columns and functions.

## Known data notes

- Total times run about 1h02 above the official figures for every rider, so all gaps are exact and match the official top 10.
- Total distance in the data is 3,302 km, against the official 3,338.8 km.
- `countries.iso` holds the race's codes (SLO, GER, NED…), not strict ISO 3166-1 alpha-3. The dashboard's map translates them.

## Resetting the Database

`python src/init_db.py` rebuilds everything. To do it by hand, run `src/sql/drop_analytics.sql` first, because the views depend on the tables, then `src/sql/drop_tables.sql` and `src/sql/schema.sql`. `src/sql/truncate_tables.sql` clears the records and keeps the tables.
