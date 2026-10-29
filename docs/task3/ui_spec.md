# Task 3 dashboard: UI spec (approved design)

Source: design canvas "LeTour OLAP Dashboard UI" (6 screens). Values shown in the mockup were illustrative only. **Every number must come from SQL views** (`src/sql/views/`). This spec includes fixes agreed after review (marked **[fix]**) and the second round of design notes from the user on 29 Oct 2026 (marked **[update 2]**). Where they conflict, **[update 2]** wins.

Target implementation: Streamlit multipage app in `src/dashboard/` with Plotly charts. Match the layout, colours and interactions below; exact pixel fidelity is not required.

---

## Global design system

**Typography**: Barlow (body, 400/500/600/700) and Barlow Condensed (titles and big numbers, 600/700) from Google Fonts. Use tabular numerals for all times and ranks.

**Colours**
| Token | Hex | Use |
|---|---|---|
| ink | `#15171C` | text, sidebar background |
| muted | `#5B6170` | secondary text, captions |
| line | `#E3E5EA` | card borders |
| ground | `#F3F4F6` | page background |
| surface | `#FFFFFF` | cards |
| leader yellow | `#F5C400` | GC leader / active nav only (use sparingly) |
| drill blue | `#2E5FA8` | selected item, drill-down panels (2px border) |

Stage types (use the **same colour everywhere**: charts, tiles, legends):
| Type | Hex |
|---|---|
| Flat | `#8FB3D9` |
| Hilly | `#E59A3C` |
| Mountain | `#B5644A` |
| Individual time-trial (ITT) | `#8D7FE0` |

Classifications: GC `#F5C400` · Points `#1E8449` · KOM red outline `#C62F36` · Young grey outline `#5B6170`.
Improvement/decline: ▲ `#1E6B3E`, ▼ `#A1262C` (always paired with the arrow symbol, never colour alone).

**Formatting**: times `h:mm:ss`; gaps `+m′ss″` relative to the leader; distances `180.6 km`; speeds `44.1 km/h`.

**Layout shell (all pages)**
- Left sidebar (dark `#15171C`, ~240px): brand "LeTour Analytics", subtitle "BT5110 · Group 16 · Tour 2025"; nav: Overview, GC & Classifications, Stages, Time Trials **[update 2]**, Riders, Teams, Nations, About (active item yellow); stage-type legend; "Source: PostgreSQL · LeTour".
- Header: breadcrumb (e.g. "Overview › Stages › Stage 12"), page title (Barlow Condensed 40px).
- Schema toggle **Normalized / Star schema** in the header (Task 4; it can be disabled until the star schema exists).
- Global filter bar (card): Stages from–to, Stage-type chips (All/Flat/Hilly/Mountain/ITT), Team, Rider nation, **Young rider: age at race start (5 Jul 2025) under [26]** [fix]. Keep the filters in `st.session_state` across pages.
- Cards: white, 1px border, 12px radius, 20px padding. Each card shows its requirement/E-number tag (e.g. "E7") in the top-right; keep these for the demo.
- Drill-downs: clicking a bar/row sets selection state and opens a blue-bordered panel; breadcrumb shows the path back up.

---

## 1 · Overview
1. **KPI tiles (6)**: Stages · Distance (km) · Starters · Finishers (and exits count) · Nations (rider nationality) · Winning margin (GC 1st→2nd).
2. **Route strip**: 21 tiles, one per stage, coloured by type, height ∝ distance, labelled with the stage number; click → Stages page with that stage selected.
3. **GC storyline (E10)**: line chart of the plotted riders' GC after each stage. Mountain stages shaded `#F6EBE6`. **[fix]**
   - **[update 2]** Rider picker on the Overview page (multi-select, default: final GC top 5), plus a team picker that adds that team's riders. It drives this chart.
   - **[update 2]** Toggle **GC rank / Cumulative time**:
     - GC rank: y = overall GC position after each stage (1 at the top, inverted axis); line crossings are reshuffles.
     - Cumulative time: y = cumulative adjusted time shown as gap to the leader (raw totals of ~77 h would overlap); hover shows the actual cumulative `h:mm:ss`.
   - **[update 2] Inflection points, covered fully** (same markers and list in both toggle views):
     - Every stage where a plotted rider's GC rank differs from the previous stage gets a dot marker; yellow-jersey changes (new rank-1 rider) get a larger marker.
     - Numbered annotations computed from data (not hard-coded), and a full list under the chart, one row per inflection: number · stage (type, route) · rider · GC rank before → after (▲▼) · time gained/lost to the leader that day. Yellow changes read "Stage N: X takes yellow".
     - Also call out the stage with the most rank changes among the plotted riders ("biggest reshuffle").
     - Stage 1 has no previous rank, so it is the baseline, not an inflection.
4. **Classification leaders**: 5 rows (GC, Points*, KOM*, Young, Best Team) with a jersey icon, rider/team and key stat; click → GC page. Footnote: *derived from finishing positions.
5. **Where the kilometres went**: 100% stacked bar of km by stage type, plus a list (type · count · km).
6. **Exits**: bars by exit reason with counts; link → Riders page exit list.

## 2 · GC & Classifications
1. **Filters**: GC after stage N; Team; Nation; Young-rider age at race start; **Counterfactual buttons (E7)**: Actual / Without bonuses / Without penalties.
2. **GC leaderboard (E1, E7)**: # · Rider · Team · Nat. · Time · Gap · Bonus (green) · Penalty (red) · **No-bonus rank ▲▼** · **No-penalty rank ▲▼** [fix]. Leader rank chip yellow; selected row blue tint.
   - **[update 2]** Bonus and Penalty sit directly after Gap as two time columns (cumulative seconds as `−m′ss″` / `+m′ss″`, `—` when zero) and must always be visible; the mockup cut the Penalty column off.
   - **[update 2]** Riders are multi-selectable (row checkboxes); the selection feeds the drill-down chart below. Default selection: final GC top 5.
   - Movement callout under the table, **computed**: riders entering/leaving the top 10 under each counterfactual [fix].
   - "Show all riders" expander with the full per-rider bonus/penalty table, sortable [fix].
3. **Rider drill-down panel (E1)**: name, team, nation, GC rank; the stage with the largest GC swing is highlighted with a "Pivotal moment" card (stage, route, type, time lost); link → Riders page.
   - **[update 2]** Chart = **overall GC standing after each stage** (y = GC position, 1 at the top) across all 21 stages, one line per selected rider (default: final top 5), x-axis ticks coloured by stage type. Replaces the time-lost bars; time lost to the leader that day moves into the hover.
   - Each selected rider's pivotal stage is marked on their line; the card shows the one for the rider in focus (last clicked, default the GC leader).
4. **Parallel classifications (req b, E4)**: Rider · GC · Points* · KOM* · Young · Mountain proxy · Proxy vs GC (▲▼) · **Age at start** [fix].
   - **[update 2]** Age is always **age at race start** (first stage date, 5 Jul 2025), never today's age. Column header "Age at start (5 Jul 2025)"; the active Young rule and cutoff are printed above the table. Rank chips tinted by classification colour. Footnote [fix]: "Age = first stage date − date of birth; Young = age at race start < cutoff. Mountain proxy = Σ adjusted time on mountain stages only. *Points/KOM derived from finishing positions."

## 3 · Stages
1. **Stage picker**: 21 buttons coloured by type; selected one has an ink border.
2. **Stage banner (dark)**: type · date; "Stage N · Start → Finish"; start/finish countries; Distance · Winner · Avg speed tiles.
3. **Top 10 finishers (E2)**: # · Rider · Team · Nat. · Adjusted time · Gap · Bonus; toggle **Riders / By team**.
4. **Squads in the top 10 (E2)**: horizontal bars, count per team.
5. **Against the clock (E11)**: **[update 2] moved to its own page, "Time Trials" (section 3b).** The Stages page keeps a one-line link to it.
6. **The long day (E15)**: all stages sorted by distance, bars in type colour; the longest outlined. **[fix]** Spotlight card for the longest stage: stage no., date, type, start → finish, distance, plus its top 5 finishers with adjusted times.

## 3b · Time Trials (E11) **[update 2]**
Own sidebar page, between Stages and Riders.
1. **ITT catalogue**: one card per ITT stage: stage no. (violet tile), route, date, distance, winner and winning time/speed. Clicking a card selects that ITT below; "Open in Stage in focus" links to the Stages page.
2. **ITT result**: top 10 for the selected ITT (# · Rider · Team · Nat. · Adjusted time · Gap · Speed).
3. **What the clock did to GC**: GC rank before → after each ITT for the GC top 10 (▲▼), and time gained/lost to the GC leader on that ITT.
4. The ITT stage-type chip in the global filter bar filters this page consistently [fix].

## 4 · Riders
1. **Rider selector** with facts: Team · Nation · Age at start · GC · Stage wins · Total bonuses.
2. **Daily trace**: 21 tiles (top border = stage-type colour) showing finishing rank; click → Stages. **[fix]** Option "Mountain stages only", which also shows gap to the stage winner per tile.
3. **Speed by terrain (E6)**: grouped bars, km/h per stage type, selected rider vs peloton median. **[fix]** Toggle Rider/Team; plus a ranked list "Biggest gainers when terrain turns mountainous" (mountain speed relative to median minus flat/hilly speed relative to median), top 10 riders and teams.
4. **Mountain contours (E5)**: Rider · Mountain podiums (rank ≤ 3) · Mean gap to stage winner (mountain) · bar. **[fix]** Clicking a row selects the rider and switches the daily trace to mountain-only.
   - **[update 2] Drill-down**: clicking a row also opens a blue drill panel for that rider with one row per mountain stage: stage (route, date) · rank · adjusted time · gap to the stage winner · podium flag, plus a bar chart of gap per mountain stage. Each stage links to Stage in focus; the breadcrumb ("Riders › Mountain contours › Rider") leads back up.
5. **Consistency near the front (E12)**: riders by count of top-10 finishes; per rider, a 21-square strip (filled in type colour when top 10). **[fix]** Each filled square shows the rank on hover/label; expander lists the contributing stages (stage, rank, type).
6. **Race exits**: Rider · Before stage · Reason (from `rider_exits`).

## 5 · Teams
1. **Best team classification (E3)**: rank · team · gap bar · gap; leader yellow; top 10 of 23 shown with an expander for the rest. Caption: "Sum of each stage's 3 fastest riders (adjusted time)".
2. **Team drill-down (E3)**: team, country, started/finished; per rider, the number of stages counted in the team's top 3 and the share of team time. **[fix]** Add a per-stage heat strip per rider (adjusted-time gap to the team's best that day, or a counted/not-counted marker).
3. **Top-10 intensity (E14)**: table team × stage type with blue sequential shading + total; clicking a cell lists the stages and riders.
   - **[update 2] How it is counted**: a top-10 finish is one `stage_results` row with `rank <= 10` (finishing order, not time). The cell value is the number of **top-10 finishes** (rider-stage pairs), so if two riders from the same team finish in the top 10 of one stage, that stage counts **2** for the team. In 2025 a team never had more than 2 riders in one stage's top 10.
   - Two extra columns, so the double-counting is visible: **Stages with a top-10 rider** (distinct stages) and **Riders** (distinct riders who made a top 10). Caption: "Finishes count every rider; Stages counts each stage once."
4. **Squad depth (E13)**: per team, 8 dots (filled = finished, outlined = exited), plus finished/8. **[fix]** Show the distinct rider count explicitly and sort by it; clicking a team opens its **roster** (rider, nationality, status), not the Nations page.

## 6 · Nations
1. **KPIs**: rider nations · team nations · countries in DB (including countries with no rider/team) · % riders racing for a foreign-registered team.
2. **Riders per country (req d, E8)**: bars by `riders.country`; click → drill.
3. **Teams per country (req d, E8)**: bars by `teams.country`; caption that this is independent of rider nationality.
4. **Country drill-down (E8)**: rider · team · team country (highlight when it differs from the rider's nation).
   - **[update 2]** A **country selector** (selectbox of all rider nations, labelled with name and ISO code) at the top of the panel, kept in sync with clicks on the bars. Default: the nation with the most riders.
5. **National outcomes (E9)**: Nation · Riders · Best GC · Stage wins · Podiums. **[fix]** Each cell links back: Best GC → that rider; Wins/Podiums → list of stages and riders.
6. Optional: choropleth map of riders per country (ISO-3 works directly with Plotly).

## 7 · About / Method (not in the mockups)
A simple text page: data source (Tour de France 2025 CSVs → PostgreSQL), definitions (adjusted time, GC, Best Team top-3 rule, Young Rider age at race start, mountain proxy, E10 inflection points), the Points/KOM method once agreed, and a requirement → page map (a–e, E1–E15). Same shell and styling as the other pages.

---

## Interaction and accessibility checklist
- Every chart has a title, a one-line caption explaining the measure, and readable axis labels.
- Colours that must be told apart also differ in lightness; ▲▼ symbols accompany colour.
- All filters are real form controls with labels; touch targets ≥ 44px.
- Responsive: the sidebar collapses on narrow screens (Streamlit default is fine).
- Cache queries (`st.cache_data`); each page loads in under 2 s.
