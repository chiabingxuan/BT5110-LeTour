"""SQL tests for the analytics layer. They need the LeTour database built by src/init_db.py."""
import os
from pathlib import Path

import psycopg2
import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@pytest.fixture(scope="module")
def cur():
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.environ["DB_PORT"], dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    )
    yield connection.cursor()
    connection.close()


def one(cur, query, params=None):
    cur.execute(query, params)
    return cur.fetchone()[0]


def rows(cur, query, params=None):
    cur.execute(query, params)
    return cur.fetchall()


# ---------- quality checks required for Task 3 ----------

def test_gc_totals_equal_sum_of_adjusted_times(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM v_gc_final g
        JOIN (SELECT rider_bib, SUM(finish_time - time_bonus + time_penalty)::float8 AS total
              FROM stage_results GROUP BY rider_bib) s USING (rider_bib)
        WHERE g.cum_time <> s.total
    """) == 0


def test_no_results_at_or_after_exit_stage(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM stage_results r
        JOIN rider_exits e USING (rider_bib)
        JOIN stages sr ON sr.id = r.stage_id
        JOIN stages sx ON sx.id = e.stage_id
        WHERE sr.date >= sx.date
    """) == 0


def test_team_classification_uses_exactly_top_three_per_stage(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM (
            SELECT team, stage_id FROM v_team_stage_riders WHERE counted
            GROUP BY team, stage_id HAVING COUNT(*) <> 3
        ) x
    """) == 0
    # Recompute the winner's total independently of the view
    team, total = rows(cur, "SELECT team, total_time FROM v_team_classification WHERE team_rank = 1")[0]
    expected = one(cur, """
        SELECT SUM(a)::float8 FROM (
            SELECT sr.adjusted_time AS a,
                   ROW_NUMBER() OVER (PARTITION BY sr.stage_id ORDER BY sr.adjusted_time, sr.rank) AS rn
            FROM v_stage_results sr JOIN riders r ON r.bib_num = sr.rider_bib
            WHERE r.team = %s
        ) x WHERE rn <= 3
    """, (team,))
    assert total == expected


def test_country_counts_match_base_tables(cur):
    assert one(cur, "SELECT COUNT(*) FROM v_country_participation WHERE dimension = 'rider' AND is_total = 0") \
        == one(cur, "SELECT COUNT(DISTINCT country) FROM riders")
    assert one(cur, "SELECT COUNT(*) FROM v_country_participation WHERE dimension = 'team' AND is_total = 0") \
        == one(cur, "SELECT COUNT(DISTINCT country) FROM teams")
    assert one(cur, "SELECT n FROM v_country_participation WHERE dimension = 'rider' AND is_total <> 0") \
        == one(cur, "SELECT COUNT(*) FROM riders")
    assert one(cur, "SELECT n FROM v_country_participation WHERE dimension = 'team' AND is_total <> 0") \
        == one(cur, "SELECT COUNT(*) FROM teams")


# ---------- official 2025 results ----------

def test_gc_matches_official_top_five(cur):
    top = rows(cur, """
        SELECT r.rider_name, g.gap FROM v_gc_final g JOIN v_riders r USING (rider_bib)
        ORDER BY g.gc_rank LIMIT 5
    """)
    assert top == [
        ("Tadej Pogacar", 0), ("Jonas Vingegaard", 264), ("Florian Lipowitz", 660),
        ("Oscar Onley", 732), ("Félix Gall", 1032),
    ]


def test_best_team_matches_official_winner(cur):
    assert one(cur, "SELECT team FROM v_team_classification WHERE team_rank = 1") == "TEAM VISMA | LEASE A BIKE"


def test_official_young_rule_gives_official_podium(cur):
    podium = rows(cur, """
        SELECT r.rider_name FROM fn_young_gc(1, 21, NULL, NULL, 'official', 26) y JOIN v_riders r USING (rider_bib)
        ORDER BY y.young_rank LIMIT 3
    """)
    assert [p[0] for p in podium] == ["Florian Lipowitz", "Oscar Onley", "Kévin Vauquelin"]


def test_default_young_rule_anchors_age_at_race_start(cur):
    # Born 23 Aug 1999, so 25 on 5 Jul 2025: young under the age rule, not under the official one
    third = rows(cur, """
        SELECT r.rider_name, r.age_at_start FROM v_young_rider y JOIN v_riders r USING (rider_bib)
        WHERE y.young_rank = 3
    """)
    assert third == [("Tobias Johannessen", 25)]


# ---------- behaviour of the slices the filters rely on ----------

def test_counterfactuals_keep_top_ten_membership(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM v_gc_final
        WHERE (gc_rank <= 10) <> (no_bonus_rank <= 10) OR (gc_rank <= 10) <> (no_penalty_rank <= 10)
    """) == 0


def test_stage_type_slice_recomputes_gc(cur):
    mountain = rows(cur, """
        SELECT g.rider_bib, g.cum_time FROM fn_gc_final(1, 21, ARRAY['mountain']) g WHERE g.gc_rank = 1
    """)
    proxy = rows(cur, "SELECT rider_bib, mountain_time FROM fn_mountain_proxy() WHERE mountain_rank = 1")
    assert mountain == proxy


def test_gc_after_stage_matches_stage_row(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM fn_gc_final(1, 21, NULL, 12) f
        JOIN v_gc_by_stage g ON g.rider_bib = f.rider_bib AND g.stage_no = 12
        WHERE f.gc_rank <> g.gc_rank OR f.cum_time <> g.cum_time
    """) == 0


def test_yellow_changes_count(cur):
    assert one(cur, "SELECT COUNT(*) FROM fn_yellow_changes() WHERE is_change") == 7
    # Level on time after stage 4; the sum of stage placings keeps yellow on Van Der Poel
    assert rows(cur, "SELECT holder_name, is_tie FROM fn_yellow_changes() WHERE stage_no = 4") == [("Mathieu Van Der Poel", True)]


def test_pivotal_stage_for_top_five_is_hautacam(cur):
    stages = rows(cur, """
        SELECT p.stage_no FROM fn_pivotal() p
        JOIN v_gc_final g USING (rider_bib) WHERE g.gc_rank <= 5
    """)
    assert [s[0] for s in stages] == [12] * 5


def test_top10_counts_every_rider(cur):
    finishes, stages, riders = rows(cur, """
        SELECT finishes, stages, riders FROM fn_top10_by_team() WHERE team = 'TEAM VISMA | LEASE A BIKE'
    """)[0]
    assert (finishes, stages, riders) == (27, 18, 7)
    assert one(cur, "SELECT SUM(finishes) FROM fn_top10_by_team()") == 210


def test_no_rider_missing_results_without_exit(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM riders r CROSS JOIN stages s
        LEFT JOIN rider_exits e ON e.rider_bib = r.bib_num
        LEFT JOIN stages sx ON sx.id = e.stage_id
        LEFT JOIN stage_results sr ON sr.rider_bib = r.bib_num AND sr.stage_id = s.id
        WHERE (sx.date IS NULL OR s.date < sx.date) AND sr.rider_bib IS NULL
    """) == 0


def test_kpis(cur):
    assert rows(cur, "SELECT stages, itt_stages, starters, finishers, exits, nations, margin FROM fn_race_kpis()") \
        == [(21, 2, 184, 160, 24, 27, 264)]


# ---------- E7 combined replay ----------

def test_no_both_replay_ranks_on_finish_time_alone(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM v_gc_final g
        JOIN (SELECT rider_bib, SUM(finish_time)::float8 AS total FROM stage_results GROUP BY rider_bib) s USING (rider_bib)
        WHERE g.no_both_time <> s.total
    """) == 0


def test_top10_movement_matches_final_ranks(cur):
    moved = one(cur, """
        SELECT COUNT(*) FROM fn_top10_movement('no_both') WHERE stage_no = 21
    """)
    assert moved == one(cur, "SELECT COUNT(*) FROM v_gc_final WHERE (gc_rank <= 10) <> (no_both_rank <= 10)")


def test_exited_rider_has_gc_rows_until_exit(cur):
    last = one(cur, "SELECT MAX(stage_no) FROM fn_gc_by_stage() WHERE rider_bib = 106")
    assert last == 15  # Van Der Poel: DNS at stage 16


# ---------- GC tie-break ----------

def test_stage_4_tie_is_broken_on_stage_placings(cur):
    assert rows(cur, """
        SELECT r.name, g.gc_rank, g.gap FROM fn_gc_by_stage() g JOIN riders r ON r.bib_num = g.rider_bib
        WHERE g.stage_no = 4 AND g.gc_rank <= 2 ORDER BY g.gc_rank
    """) == [("Mathieu Van Der Poel", 1, 0), ("Tadej Pogacar", 2, 0)]
    assert one(cur, "SELECT gc_rank FROM fn_gc_by_stage() WHERE stage_no = 5 AND rider_bib = 1") == 1


def test_no_two_riders_share_a_gc_rank(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM (SELECT seq, gc_rank FROM fn_gc_by_stage() GROUP BY seq, gc_rank HAVING COUNT(*) > 1) x
    """) == 0
    for column in ("gc_rank", "no_bonus_rank", "no_penalty_rank", "no_both_rank"):
        assert one(cur, f"SELECT COUNT(*) - COUNT(DISTINCT {column}) FROM v_gc_final") == 0


def test_top_ten_is_exactly_ten_riders_after_every_stage(cur):
    assert one(cur, """
        SELECT COUNT(*) FROM (SELECT seq FROM fn_gc_by_stage() WHERE gc_rank <= 10 GROUP BY seq HAVING COUNT(*) <> 10) x
    """) == 0


def test_top10_movement_finds_the_stage_10_swap(cur):
    # From stage 7 on, removing bonuses swaps Roglic into the top 10 and Arensman out at stage 10
    assert rows(cur, """
        SELECT m.stage_no, m.movement, r.name FROM fn_top10_movement('no_bonus', 7, 21) m
        JOIN riders r ON r.bib_num = m.rider_bib WHERE m.stage_no = 10 ORDER BY m.movement
    """) == [(10, "enters", "Primoz Roglic"), (10, "leaves", "Thymen Arensman")]
