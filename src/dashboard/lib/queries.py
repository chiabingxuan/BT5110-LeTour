"""Every query the app runs. All analytics live in src/sql/views; these only SELECT from them.

f is the Filters object from lib/filters.py; its stage range and types define the selected stages.
"""
from lib.db import query

SEL = ":f, :t, CAST(:ty AS text[])"


def _sel(f):
    return {"f": f.stage_from, "t": f.stage_to, "ty": f.types}


RIDER_COLS = "r.rider_name, r.team, r.rider_country, r.team_country, r.age_at_start, r.dob, r.status, r.exit_stage"


def stages():
    return query("SELECT * FROM v_stages ORDER BY date")


def selected_stages(f):
    return query(f"""
        SELECT s.*, x.seq FROM fn_stage_selection({SEL}) x
        JOIN v_stages s ON s.stage_id = x.stage_id ORDER BY x.seq
    """, **_sel(f))


def riders():
    return query("SELECT * FROM v_riders ORDER BY rider_bib")


def team_names():
    return query("SELECT name, country FROM teams ORDER BY name")


def rider_nations():
    return query("SELECT iso, country_name, n FROM v_country_participation WHERE dimension = 'rider' AND is_total = 0 ORDER BY country_name")


def kpis(f):
    return query(f"SELECT * FROM fn_race_kpis({SEL})", **_sel(f)).iloc[0]


def gc_by_stage(f, bibs=None):
    return query(f"""
        SELECT g.*, r.rider_name FROM fn_gc_by_stage({SEL}) g
        JOIN v_riders r ON r.rider_bib = g.rider_bib
        WHERE CAST(:b AS int[]) IS NULL OR g.rider_bib = ANY (CAST(:b AS int[]))
        ORDER BY g.seq, g.gc_rank
    """, b=bibs, **_sel(f))


def gc_final(f, after=None):
    return query(f"""
        SELECT g.*, {RIDER_COLS} FROM fn_gc_final({SEL}, :a) g
        JOIN v_riders r ON r.rider_bib = g.rider_bib
        ORDER BY g.gc_rank, g.rider_bib
    """, a=after, **_sel(f))


def pivotal(f, after=None):
    return query(f"SELECT * FROM fn_pivotal({SEL}, :a)", a=after, **_sel(f))


def yellow(f):
    return query(f"SELECT * FROM fn_yellow_changes({SEL}) ORDER BY seq", **_sel(f))


def inflections(f, bibs):
    return query(f"""
        SELECT i.*, r.rider_name FROM fn_gc_inflections(CAST(:b AS int[]), {SEL}) i
        JOIN v_riders r ON r.rider_bib = i.rider_bib
        ORDER BY i.stage_no, i.gc_rank
    """, b=bibs, **_sel(f))


def compare(f, after, rule, cutoff):
    return query(f"""
        SELECT c.*, {RIDER_COLS} FROM fn_classification_compare({SEL}, :a, :rule, :cut) c
        JOIN v_riders r ON r.rider_bib = c.rider_bib
        ORDER BY c.gc_rank, c.rider_bib
    """, a=after, rule=rule, cut=cutoff, **_sel(f))


def young(f, rule, cutoff):
    return query(f"""
        SELECT y.*, r.rider_name, r.team FROM fn_young_gc({SEL}, NULL, :rule, :cut) y
        JOIN v_riders r ON r.rider_bib = y.rider_bib ORDER BY y.young_rank
    """, rule=rule, cut=cutoff, **_sel(f))


def derived(f, classification):
    return query(f"""
        SELECT d.*, r.rider_name, r.team FROM fn_derived_classification(:c, {SEL}) d
        JOIN v_riders r ON r.rider_bib = d.rider_bib ORDER BY d.class_rank, r.rider_name
    """, c=classification, **_sel(f))


def type_mix(f):
    return query(f"""
        SELECT s.type, s.type_label, COUNT(*)::int AS stages, SUM(s.dist_km) AS km
        FROM fn_stage_selection({SEL}) x JOIN v_stages s ON s.stage_id = x.stage_id
        GROUP BY s.type, s.type_label ORDER BY MIN(s.stage_no)
    """, **_sel(f))


def exits(f=None):
    return query("SELECT * FROM v_exits ORDER BY stage_no, rider_name")


def stage_results(stage_no, limit=None):
    return query("""
        SELECT * FROM v_results_enriched WHERE stage_no = :s ORDER BY rank LIMIT :n
    """, s=int(stage_no), n=limit)


def rider_results(f, bib):
    return query(f"""
        SELECT r.* FROM v_results_enriched r
        JOIN fn_stage_selection({SEL}) x ON x.stage_id = r.stage_id
        WHERE r.rider_bib = :b ORDER BY x.seq
    """, b=int(bib), **_sel(f))


def speed_by_type(f):
    return query(f"SELECT * FROM fn_speed_by_type({SEL})", **_sel(f))


def gainers_riders(f):
    return query(f"SELECT * FROM fn_speed_gainers_riders({SEL}) ORDER BY gain_pct DESC", **_sel(f))


def gainers_teams(f):
    return query(f"SELECT * FROM fn_speed_gainers_teams({SEL}) ORDER BY gain_pct DESC", **_sel(f))


def contours(f):
    return query(f"""
        SELECT c.*, r.rider_country FROM fn_mountain_contours({SEL}) c
        JOIN v_riders r ON r.rider_bib = c.rider_bib
        ORDER BY c.podiums DESC, c.mean_gap
    """, **_sel(f))


def top10_riders(f):
    return query(f"SELECT * FROM fn_top10_by_rider({SEL}) ORDER BY finishes DESC, rider_name", **_sel(f))


def top10_rows(f, bibs=None, team=None, stage_type=None):
    return query(f"""
        SELECT r.* FROM v_results_enriched r
        JOIN fn_stage_selection({SEL}) x ON x.stage_id = r.stage_id
        WHERE r.rank <= 10
          AND (CAST(:b AS int[]) IS NULL OR r.rider_bib = ANY (CAST(:b AS int[])))
          AND (CAST(:team AS text) IS NULL OR r.team = :team)
          AND (CAST(:st AS text) IS NULL OR r.type = :st)
        ORDER BY x.seq, r.rank
    """, b=bibs, team=team, st=stage_type, **_sel(f))


def best_team(f):
    return query(f"SELECT * FROM fn_best_team({SEL}) ORDER BY team_rank", **_sel(f))


def team_contribution(f, team):
    return query(f"""
        SELECT * FROM fn_team_contribution(:team, {SEL}) ORDER BY stages_counted DESC, rider_name
    """, team=team, **_sel(f))


def team_stage_rows(f, team):
    return query(f"""
        SELECT v.rider_bib, v.stage_no, v.counted FROM v_team_stage_riders v
        JOIN fn_stage_selection({SEL}) x ON x.stage_id = v.stage_id
        WHERE v.team = :team
    """, team=team, **_sel(f))


def top10_by_team(f):
    return query(f"SELECT * FROM fn_top10_by_team({SEL}) ORDER BY finishes DESC, team", **_sel(f))


def squad_depth():
    return query("SELECT * FROM v_squad_depth ORDER BY distinct_riders DESC, finished DESC, team")


def roster(team):
    return query("SELECT * FROM v_riders WHERE team = :team ORDER BY rider_bib", team=team)


def participation(dimension):
    return query("""
        SELECT iso, country_name, n FROM v_country_participation
        WHERE dimension = :d AND is_total = 0 ORDER BY n DESC, iso
    """, d=dimension)


def country_kpis():
    return query("SELECT * FROM v_country_kpis").iloc[0]


def national_outcomes(f):
    return query(f"""
        SELECT * FROM fn_national_outcomes({SEL}) ORDER BY best_gc NULLS LAST, stage_wins DESC, iso
    """, **_sel(f))


def national_results(f, iso, max_rank):
    return query(f"""
        SELECT r.* FROM v_results_enriched r
        JOIN fn_stage_selection({SEL}) x ON x.stage_id = r.stage_id
        WHERE r.rider_country = :iso AND r.rank <= :m ORDER BY x.seq, r.rank
    """, iso=iso, m=max_rank, **_sel(f))


def derived_scale(classification):
    return query("""
        SELECT classification AS "Classification",
            CASE type WHEN 'individual time-trial' THEN 'ITT' ELSE INITCAP(type) END AS "Stage type",
            STRING_AGG(points::text, ', ' ORDER BY rank) AS "Points by finishing rank"
        FROM v_points_scale WHERE classification = :c
        GROUP BY classification, type ORDER BY MIN(rank), MAX(points) DESC
    """, c=classification)


def derived_leaders(classification):
    rows = query("""
        SELECT r.rider_name, d.points FROM fn_derived_classification(:c) d
        JOIN v_riders r ON r.rider_bib = d.rider_bib WHERE d.class_rank = 1
    """, c=classification)
    return ", ".join(f"{row.rider_name} ({row.points} pts)" for row in rows.itertuples())
