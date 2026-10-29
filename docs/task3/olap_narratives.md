# Task 3: OLAP narratives E1–E15 (acceptance criteria)

From the instructor's "Analytical Dashboard: OLAP Demonstration Prompts". Each narrative must be demonstrable live in a few clicks. Tag visuals with the E-number in code comments and in `docs/demo_script.md`.

Conventions: `adjusted_time = finish_time - time_bonus + time_penalty` (view `v_stage_results`). Stage order is `stages.date`, never `stages.id` (it is VARCHAR: '10' < '2'). Race start = `MIN(stages.date)`.

Status column = coverage in the approved design, after the agreed fixes in `ui_spec.md`.

| # | Page | Status |
|---|---|---|
| E1 | GC & Classifications | Full |
| E2 | Stages | Full |
| E3 | Teams | Fix: per-stage profiles in team drill |
| E4 | GC & Classifications | Fix: age at race start label + column |
| E5 | Riders | Full (+ mountain-only trace) |
| E6 | Riders | Fix: team view + gainers ranking |
| E7 | GC & Classifications | Fix: no-penalty rank, computed callout, all-riders table |
| E8 | Nations | Full |
| E9 | Nations | Fix: drill links |
| E10 | Overview | Fix: computed inflection points, picker, bump view |
| E11 | Time Trials (own page, update 2) | Full |
| E12 | Riders | Fix: ranks per stage |
| E13 | Teams | Fix: distinct count + roster drill |
| E14 | Teams | Full |
| E15 | Stages | Fix: longest-stage spotlight with finishers |

---

### E1 · GC leaderboard with contextual descent
**Ask:** Overall GC ordered by lowest cumulative adjusted time; follow a contender down to stage grain; surface the single stage that most altered their GC standing (the "pivotal moment").
**SQL:** cumulative time `SUM(adjusted_time) OVER (PARTITION BY rider_bib ORDER BY date)`; GC rank per stage `RANK() OVER (PARTITION BY stage_id ORDER BY cum_time)`; pivotal stage = max `|gc_rank - LAG(gc_rank)|` (tie-break: largest time lost to the leader that day).
**Accept:** select any rider → per-stage chart + highlighted pivotal stage with route, type and time lost.

### E2 · A stage in focus
**Ask:** For one stage: leading finishers with adjusted times, riders, teams, origin/destination, distance, type; then reframe to a team view of who populated the top 10.
**Accept:** stage picker → banner (start/end + countries, distance, type, date) + top-10 table + by-team toggle/bars.

### E3 · Team burden and contribution
**Ask:** Roll up each team's aggregate adjusted time; open it to show which riders carried the time load and how their per-stage profiles shaped the outcome.
**SQL:** per stage, top 3 riders per team by adjusted time (`ROW_NUMBER() OVER (PARTITION BY stage_id, team ORDER BY adjusted_time) <= 3`), summed over stages. Contribution = stages counted and share of team time per rider.
**Accept:** team ranking → drill panel with per-rider counts and a per-stage strip per rider.

### E4 · Parallel classifications
**Ask:** Side-by-side GC rank and Young Rider GC rank (age filter **anchored at race start**); add a mountain-stage GC proxy (adjusted time summed only over mountain stages) and narrate where it diverges from GC.
**SQL:** age = `date_part('year', age((SELECT MIN(date) FROM stages), dob))`; young GC = GC ranked over riders with age < :cutoff; proxy = `SUM(adjusted_time) FILTER (WHERE type='mountain')` ranked; divergence = gc_rank − proxy_rank.
**Accept:** cutoff filter labelled "age at race start (date)"; table shows Age at start, GC, Young, Mountain proxy, ▲▼ difference. Only riders who finished all mountain stages are ranked in the proxy (state the rule).

### E5 · Mountain contours
**Ask:** Per rider, podium frequency on mountain stages and mean time gap to the stage winner on that terrain; allow return to the daily traces.
**SQL:** on mountain stages: `COUNT(*) FILTER (WHERE rank <= 3)`; gap = adjusted_time − `MIN(adjusted_time) OVER (PARTITION BY stage_id)`, then `AVG` per rider.
**Accept:** table → click rider → mountain-only daily trace with rank and gap per stage.

### E6 · Speed as a simple ratio
**Ask:** For riders and teams, a stage-type profile of speed = length/time across Flat, Hilly, Mountain, ITT; emphasise who gains when terrain shifts to Mountain.
**SQL:** speed = `dist_covered / (adjusted_time/3600)`, averaged per rider (and per team) per type; compare with the peloton median per type; gain = (mountain speed / median) − (flat-hilly speed / median).
**Accept:** grouped bars for the selected rider or team vs median + ranked "biggest gainers" list for riders and teams.

### E7 · Bonuses, penalties and counterfactuals
**Ask:** Cumulative bonuses and penalties per rider; replay GC with bonuses removed, then penalties removed; show movement into/out of the top 10.
**SQL:** three cumulative totals: actual; `finish_time + time_penalty` (no bonus); `finish_time - time_bonus` (no penalty); rank each; diff vs actual.
**Accept:** counterfactual toggle re-ranks the board; columns for no-bonus and no-penalty rank with ▲▼; a computed callout naming riders entering/leaving the top 10; a full per-rider bonus/penalty table.

### E8 · Participation by nation
**Ask:** Count of teams and count of riders per nation; open the roll-up to list riders and their teams for a chosen country.
**SQL:** `COUNT(*) FROM riders GROUP BY country`; `COUNT(*) FROM teams GROUP BY country`. These are separate dimensions.
**Accept:** two bar charts + country drill list (rider, team, team country).

### E9 · National outcomes
**Ask:** For each nation, best GC rank achieved by its riders and tally of wins/podiums; keep a clear path back to the underlying stages and athletes.
**Accept:** table Nation · Riders · Best GC · Stage wins · Podiums; each value clickable → the rider(s)/stage(s) behind it.

### E10 · Temporal GC storyline
**Ask:** Cumulative adjusted time after each stage for the principal GC riders as lines; mark mountain stages; annotate inflection points where standings reshuffle; rider/team filters guide the view.
**SQL:** as E1; inflection = rows where `gc_rank <> LAG(gc_rank)` (compute the LAG in a CTE, then filter); yellow change = rank-1 rider differs from the previous stage.
**Accept:** line chart (gap to leader, or cumulative time) with shaded mountain stages; markers + numbered, data-driven annotations; rider/team picker; optional bump-chart toggle. Say in the demo that the gap view is cumulative time minus the leader's.

### E11 · Against the clock
**Ask:** Inventory of ITT stages with date, distance and winner as a compact catalogue.
**SQL:** `stages WHERE type = 'individual time-trial'` joined to the rank-1 result.
**Accept:** catalogue cards; click → stage in focus; the ITT stage-type chip filters the Stages page consistently.

### E12 · Consistency near the front
**Ask:** Riders who most often appear in the top ten; with the list of contributing stages, their ranks and stage types.
**Accept:** leaderboard of top-10 counts + per-rider strip showing the rank on each qualifying stage + expandable list (stage, rank, type).

### E13 · Depth of squads
**Ask:** At rider grain, team depth via distinct rider counts; highlight the broadest rosters; a doorway to full rider lists and countries.
**SQL:** `COUNT(DISTINCT bib_num) GROUP BY team` (plus finished vs exited from `rider_exits`).
**Accept:** sorted by distinct count with the broadest highlighted (if all are 8, say so and sort by finishers); click → roster with nationality and status.

### E14 · Top-ten intensity by team
**Ask:** Team-level top-10 presences, optionally broken down by stage type; links back to the specific stages and riders.
**Accept:** team × stage-type heat table with totals; cell click → list of stages and riders.

### E15 · The long day
**Ask:** Sort stages by distance; spotlight the longest route (name/date, type, start/finish); complement it with the leading finishers and their adjusted times.
**Accept:** sorted distance bars + spotlight card for the longest stage with date, type, route and top-5 finishers' adjusted times.

---

## Mandatory requirements a–e (assignment brief)
| Req | Covered by |
|---|---|
| a. Drill-down (stage / rider / team) | E1, E2, E3, E5, E8, E9, E14; breadcrumbs |
| b. Classification comparison (GC, Points, KOM, Young) | GC page "Parallel classifications" table; Overview leaders |
| c. Aggregate performance (cumulative time by rider, team, classification) | E1, E3, E7, E10; Best Team |
| d. Country participation (teams/riders per country) | Nations page, E8 |
| e. Design and presentation | `ui_spec.md` design system; consistent stage-type colours; tagged cards |

**Points & KOM:** the schema has no points data. Default = derive from finishing positions using a documented points scale per stage type (KOM on hilly/mountain only), clearly labelled as "derived". Confirm with the user before implementing.
