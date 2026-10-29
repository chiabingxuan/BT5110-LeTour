# CLAUDE.md – BT5110 Group 16 · Task 3 OLAP Dashboard

Project instructions for Claude Code working in this repo.

## Read first
1. This file (project context, rules, technical approach).
2. `docs/task3/ui_spec.md`: the approved dashboard UI, page by page. Build to this.
3. `docs/task3/olap_narratives.md`: E1–E15 from the instructor's brief, mapped to pages, with SQL approach and acceptance criteria.
4. `docs/task3/screenshots/1_overview.png` … `6_nations.png`: images of the six designed screens. Note:
   - They show the design **before** the [fix] items in `ui_spec.md`; where they differ, `ui_spec.md` wins.
   - All numbers in them are illustrative placeholders. Never copy values; compute everything in SQL.
   - Headings render in a fallback serif; the intended font is Barlow Condensed.
5. `docs/task3/design_source/*.dc.html`: the original design markup (inline styles plus sample data in `renderVals()`). Use it as a reference for exact colours, spacing and layout; it is not runnable Streamlit code.

## Hard rules (non-negotiable)
- **Never `git push`, never commit to `main`, never open a PR, never force-push without explicit approval from the user in the current conversation.** Work on a local branch `feat/task3-dashboard`, and ask before every push.
- Never commit `data/`, `.env` or any credentials.
- Do not alter base tables in `src/sql/schema.sql`. Add views/new files instead.
- Never fabricate race data. The dataset is real (Tour de France 2025) and lives in git-ignored `data/`.
- Ask before: choosing the Points/KOM method, populating award tables, changing the BI tool, or adding dependencies beyond those listed here.
- Start by inspecting the repo and reporting a plan; wait for approval before writing code.


## Handoff status (from the planning session, 29 Oct 2026)
**Done**
- Tasks 1 and 2 submitted. Schema in `src/sql/schema.sql`; data loader `src/data_loading.ipynb` works.
- Dashboard UI designed and reviewed (6 screens). Review found gaps in E3, E4, E6, E7, E9, E10, E12, E13 and E15; the fixes are written into `ui_spec.md` as **[fix]** items and are part of the scope.
- Nothing has been built yet: no views, no app code, no star schema.

**Decisions already made**
- Streamlit + Plotly on PostgreSQL; analytics in SQL views; app mostly `SELECT`s from views.
- Young Rider = age at race start (first stage date) < cutoff (default 26), adjustable.
- Best Team = sum of each stage's 3 fastest riders' adjusted times.
- E10 inflection point = a stage where a plotted rider's GC rank differs from the previous stage; yellow-jersey change = new rank-1 rider.
- E10 chart shows gap to leader (cumulative time − leader's), with an optional bump-chart view.

**Open, ask the user before implementing**
1. Points / KOM method (default proposal: derived from finishing positions; state the points scale you plan to use).
2. Whether to populate `rider_awards` / `team_awards` from the derived views.
3. Converting `requirements.txt` from UTF-16 to UTF-8 and the new packages to add.
4. Adding `.DS_Store` to `.gitignore` (macOS clutter; the user is on a Mac).
5. Any rider with missing stage results but no exit row: how to treat them in GC.

**Suggested build order** (check in with the user after each milestone)
1. `src/sql/views/v_stage_results.sql` + `init_db.py`; load data; report row counts and sanity checks.
2. Core views: cumulative GC per stage, final GC, young rider, mountain proxy, best team, counterfactuals, country counts.
3. Tests in `tests/test_views.py`.
4. App shell (sidebar, filters, theme) → pages in order: Overview, GC & Classifications, Stages, Riders, Teams, Nations, About.
5. Star schema + benchmark (Task 4).
6. App screenshots, `docs/demo_script.md`, README update.

**Git state at handoff:** branch `main` at `615b101`, clean except for untracked handoff files (`CLAUDE.md`, `docs/task3/`). The user has push access as GitHub user `ttawmo`, but pushes only after the user explicitly approves.

## Role and goal
You are working in our GitHub repo for the BT5110 group project "Tour de France Database and Analytics System" (NUS, AY26/27 Sem 1, Group 16). Tasks 1 (ER diagram) and 2 (relational schema, BCNF) are done. Build **Task 3: an interactive OLAP-style analytical dashboard** on top of our existing PostgreSQL schema. It is worth 15%, it is due **Wed 11 Nov 2026**, and we will demo it live. The same work feeds Task 4 (final report, due Fri 13 Nov 2026). That report needs dashboard screenshots plus a star-schema vs normalized-schema comparison, so build the SQL layer with that in mind.

Repo: https://github.com/chiabingxuan/BT5110-LeTour. Work on a feature branch (`feat/task3-dashboard`), commit locally in small logical steps; push/PR only when the user approves. Do not push anything without the user's explicit approval (see Hard rules).

### What the repo already contains (keep and build on it)
- `src/sql/schema.sql`, `drop_tables.sql`, `truncate_tables.sql`: the normalized schema from Task 2.
- `src/data_loading.ipynb`: reads `data/riders.csv`, `data/individual_results.csv` and `data/exits.csv`, cleans them (imputes RUS for neutral rider Vlasov; fixes a duplicate rank on 18 Jul 2025), validates every constraint, and inserts into PostgreSQL.
- `data/` and `.env` are **git-ignored**. Each member adds them locally. The DB is `LeTour`; `.env` holds `DB_HOST`, `DB_PORT` (often 5433), `DB_NAME`, `DB_USER` and `DB_PASSWORD`.
- `requirements.txt` is a `pip freeze` saved in **UTF-16**. Convert it to UTF-8 before appending new packages (streamlit, plotly, sqlalchemy, pytest), and mention the conversion in the PR.
- The dataset is the **real Tour de France 2025**, so no synthetic data is needed.

## 2. Before you write code (inspect, then report back)
1. Explore the repo and list what already exists: `schema.sql`, seed/data files (CSV/SQL), any notebooks, scripts or README.
2. Read the notebook and README, then load the data locally (if `data/` is missing, ask us for the CSVs; never fabricate data). Report the row counts per table and a quick sanity check: 21 stages, about 184 starters, number of exits.
3. Report a short plan covering the tool choice, page layout, and how each requirement in Section 5 and each narrative E1–E15 in Section 6 will be served. Then wait for our go-ahead.

## 3. Existing schema (from Task 2; do NOT change base tables)
PostgreSQL. Tables:
- `countries(iso CHAR(3) PK, name)`
- `teams(name PK, country → countries.iso)`
- `riders(bib_num PK, name, dob, team → teams.name, country → countries.iso)`. The rider's country can differ from the team's country.
- `locations(name PK, country → countries.iso)`
- `stages(id PK, date, start_location → locations, end_location → locations, dist_covered DECIMAL km, type IN ('flat','hilly','mountain','individual time-trial'))`
- `stage_results(rider_bib, stage_id, rank, finish_time, time_bonus, time_penalty; PK(rider_bib, stage_id); UNIQUE(stage_id, rank))`. Times are in seconds.
- `rider_exits(rider_bib PK, stage_id, reason)`
- `awards(name PK)`, `rider_awards(award PK, rider_bib)`, `team_awards(award PK, team)`
- Derived `adjusted_time = finish_time - time_bonus + time_penalty` is never stored. The Task 2 report defines a view `v_stage_results` for it, but **that view is not in the repo yet**. Create it first, in `src/sql/views/`.

**Gotchas from the loader:**
- `stages.id` holds the strings '1'..'21' (VARCHAR), numbered in date order. Never `ORDER BY id`, because '10' sorts before '2'. Order by `date` or by `id::int`.
- `stages` has no stage name column. Label stages as "Stage N: Start → Finish".
- `awards` is populated, but **`rider_awards` and `team_awards` are empty**. Derive the classification winners in views. Optionally add a script that populates the award tables from those views, but ask us first.
- Some riders may lack a result for a stage without having an exit row. Check for this and report it rather than silently dropping them.

Stage order is by `stages.date`. Stage type strings are lowercase; map them to display labels Flat / Hilly / Mountain / ITT.

## 4. Business rules and definitions the dashboard must respect
- **General Classification (GC):** lowest cumulative adjusted_time across completed stages. Only riders who finished every stage are ranked in the final GC. Riders in `rider_exits` are shown as "DNF – stage X (reason)", not ranked.
- **Best Team:** sum of the three fastest riders' adjusted times per stage, accumulated over all stages (the official TdF method). State this method in the UI.
- **Young Rider:** GC restricted to riders whose **age at race start** (race start = `MIN(stages.date)`, i.e. 5 Jul 2025) is below a user-adjustable cutoff (default 26). Compute with `date_part('year', age((SELECT MIN(date) FROM stages), dob))`. Optionally offer the official calendar-year rule (born on or after 1 Jan 2000) as a toggle, and label which rule is active.
- **Points and King of the Mountains:** the schema has **no points or KOM columns**. Propose an option and flag it to us before implementing:
  (a) **Rank-based proxy (default):** award points by stage-finish rank using a documented points scale per stage type (e.g. a larger scale on flat stages), and KOM points from finishing rank on mountain/hilly stages only. Label it clearly in the UI as "derived from finishing positions".
  (b) Add a separate, normalized `classification_points(rider_bib, stage_id, classification, points)` table, only if we have real data for it.
  Whichever we choose, document the assumption in the README and on the dashboard.
- Sanity-check the derived GC, Young Rider and Best Team winners against the official 2025 results (GC: Tadej Pogačar). Report any mismatch to us; don't hide it.
- Times display as `h:mm:ss`. GC gaps display as `+m′ss″` relative to the leader (see ui_spec.md).

## 5. Mandatory requirements (assignment brief, Task 3)
The dashboard must support OLAP-style analysis (roll-up, drill-down, slice/dice, pivot):
a. **Drill-down analysis:** explore results at different levels of detail, e.g. Race → Stage type → Stage → Team → Rider, and Team → Rider → Stage.
b. **Classification comparison:** compare rankings across GC, Points, KOM and Young Rider side by side for the same riders.
c. **Aggregate performance:** cumulative race times by rider, by team and by classification.
d. **Country participation:** number of teams per country and number of riders per country. Note that team country and rider country are separate dimensions.
e. **Design and presentation:** clear, intuitive, organised layout, consistent colours (one colour per stage type, used everywhere), appropriate chart types, interactive filters, and readable labels. Go beyond the minimum with extra analyses and insights.

Global filters on every page: stage range or stage type, team, rider country, team country, and the young-rider age cutoff.

## 6. Instructor's suggested OLAP narratives (E1–E15). Cover all of them. Full acceptance criteria: docs/task3/olap_narratives.md
Each one should be reachable in a few clicks during the demo. Tag each visual with its E-number in code comments and in the demo script.
- **E1 GC leaderboard + descent:** GC ordered by cumulative adjusted time; select a contender, drill to stage grain, and highlight the single stage that changed their GC position the most (the "pivotal moment").
- **E2 Stage in focus:** for one stage, show the top finishers with adjusted time, rider, team, start/finish location, distance and type; then pivot to the team view of who filled the top 10 that day.
- **E3 Team burden:** each team's aggregate adjusted time, then drill into which riders carried the time and their per-stage profiles.
- **E4 Parallel classifications:** a rider's GC rank next to their Young Rider rank (age filter anchored at race start), plus a **Mountain-only GC proxy** (adjusted time summed only over mountain stages); highlight where the proxy diverges from overall GC.
- **E5 Mountain contours:** per rider, podium count on mountain stages and mean gap to the stage winner on mountain stages, with drill-back to the daily results.
- **E6 Speed by terrain:** average speed = distance / time per rider and team, broken out by Flat/Hilly/Mountain/ITT; highlight who gains when the terrain moves to mountains.
- **E7 Bonuses, penalties, counterfactuals:** cumulative bonuses and penalties per rider; toggles to replay GC (i) without bonuses and (ii) without penalties; show movements into and out of the top 10.
- **E8 Participation by nation:** count of teams and riders per country; drill into a country to list its riders and their teams.
- **E9 National outcomes:** per nation, best GC rank, stage wins and podiums, with drill-back to stages and riders.
- **E10 Temporal GC storyline:** line chart of cumulative adjusted time (or gap to leader) after each stage for the top GC riders; shade or mark mountain stages and annotate where the standings reshuffle; filter by rider or team.
- **E11 Against the clock:** catalogue of ITT stages with date, distance and winner.
- **E12 Consistency near the front:** riders with the most top-10 finishes, plus the list of contributing stages, ranks and types.
- **E13 Squad depth:** distinct riders per team (highlight the broadest rosters), drilling into full rider lists and countries; also show riders remaining vs exited.
- **E14 Top-10 intensity by team:** team top-10 appearances, optionally split by stage type, linking to the specific stages and riders.
- **E15 The long day:** stages sorted by distance; spotlight the longest stage (id/date, type, start → finish) with its leading finishers and adjusted times.

## 7. Technical approach
- **Tool:** a web-based BI dashboard in Python, **Streamlit + Plotly** (or Dash), connected to PostgreSQL via SQLAlchemy/psycopg. Everything stays in git and can be reproduced by any group member. If you think Tableau or Power BI is clearly better for us, say so in the plan, but do not switch without asking.
- **SQL layer first:** put all analytics in versioned SQL files under `src/sql/views/` (e.g. `v_gc_cumulative`, `v_gc_by_stage`, `v_team_classification`, `v_young_rider`, `v_points_proxy`, `v_kom_proxy`, `v_country_participation`). The Python app should mostly `SELECT` from these views. Use window functions (`SUM() OVER (PARTITION BY rider ORDER BY date)`, `RANK()`) and `GROUPING SETS` / `ROLLUP` where they show OLAP roll-ups.
- **Task 4 readiness:** put the star schema in `src/sql/star/` (`fact_results` plus `dim_rider`, `dim_team`, `dim_stage`, `dim_country`, optionally `dim_date`), with an ETL script that loads it from the normalized tables. Write the same representative queries (cumulative time per rider, best team, stage-by-stage performance) against both schemas, plus a small `EXPLAIN ANALYZE` timing script. The dashboard must still run on the normalized views. A toggle to use the star schema is a nice extra.
- **Config:** reuse the existing `.env` keys and `python-dotenv` (commit a `.env.example`, never real secrets). Add a script (`src/init_db.py` or similar) that runs schema → the notebook's loading logic → views, so that everyone can rebuild the DB with one command. Keep the notebook working; you may factor its logic into a `.py` module the notebook calls.
- **Performance:** cache query results (`st.cache_data`); every page should load in under 2 s on our dataset.

## 8. Page layout (detail: docs/task3/ui_spec.md)
1. **Overview:** KPI tiles (stages, total km, riders started/finished, teams, nations, GC winner and margin), the E10 storyline, and the awards summary.
2. **GC & Classifications:** E1, E4, E7, with the side-by-side classification table (req b).
3. **Stages:** E2, E11, E15, plus a stage profile table (distance, type, winner, average speed).
4. **Riders:** rider profile with drill-down (E5, E6, E12), and the exit list with reasons.
5. **Teams:** E3, E13, E14, and the Best Team classification.
6. **Nations:** E8, E9, with a choropleth map of riders per country (ISO-3 codes map directly into Plotly).
7. **About / Method** (not in the mockups; keep it simple): definitions, assumptions (points/KOM proxy, young-rider cutoff), and the data source.

Clicking a bar or row should drill down (Plotly click events or selectboxes synced through session state), and there should be a clear way back up (breadcrumb).

## 9. Repo structure (extend the existing `src/` layout; don't move existing files)
```
data/                          (git-ignored, unchanged)
src/data_loading.ipynb         (existing)
src/sql/schema.sql ...         (existing)
src/sql/views/*.sql            (new: v_stage_results, GC, classifications, country views)
src/sql/star/*.sql             (new: Task 4 star schema + ETL)
src/sql/queries/*.sql          (new: representative queries, normalized vs star)
src/init_db.py  src/benchmark.py
src/dashboard/app.py  src/dashboard/pages/*.py  src/dashboard/lib/{db.py,format.py,charts.py}
tests/test_views.py
docs/demo_script.md  docs/task3/app_screenshots/   (docs/task3/screenshots/ = design mockups; don't overwrite)
README.md (extend the setup section)  requirements.txt  .env.example
```

## 10. Quality checks before you call it done
- Unit/SQL tests: GC totals equal the sum of per-stage adjusted times; no results exist after a rider's exit stage; team classification uses exactly the top 3 per stage; country counts match `COUNT(DISTINCT)` on the base tables.
- Run the app end-to-end and fix any errors or empty charts.
- Take screenshots of every finished page into `docs/task3/app_screenshots/` (Playwright is fine) for the Task 4 report. Do not overwrite `docs/task3/screenshots/` (the design mockups).
- Write `docs/demo_script.md`: a 8–10 minute walkthrough in E1→E15 order, with the click path and the insight to state at each step, covering every requirement a–e.
- README: setup, run (`streamlit run src/dashboard/app.py`), a feature-to-requirement mapping table (a–e, E1–E15 → page/visual), and assumptions.

## 11. Working style
- Keep commits small, with clear messages, on `feat/task3-dashboard`. When the user approves pushing, open a PR summarising what was built, the assumptions made, and any open questions.
- Ask us before: generating any synthetic data, altering base tables, choosing the points/KOM method, or changing the BI tool.
- Prefer readable, well-commented code: four group members need to understand and present it.
