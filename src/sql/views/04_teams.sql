-- Team analytics: Best Team (E3), top-10 intensity (E14), squad depth (E13).

-- Rider x stage with the rider's position inside their team that day. counted = in the team's 3 fastest.
CREATE OR REPLACE VIEW v_team_stage_riders AS
SELECT
    r.team,
    r.rider_bib,
    r.rider_name,
    r.stage_no,
    r.stage_id,
    r.type,
    r.adjusted_time,
    (ROW_NUMBER() OVER w)::int AS team_stage_position,
    (ROW_NUMBER() OVER w) <= 3 AS counted,
    (COUNT(*) OVER (PARTITION BY r.team, r.stage_id))::int AS team_finishers
FROM v_results_enriched r
WINDOW w AS (PARTITION BY r.team, r.stage_id ORDER BY r.adjusted_time, r.rank);

-- E3: sum of each stage's 3 fastest riders. A team needs 3 finishers on every selected stage to be ranked.
CREATE OR REPLACE FUNCTION fn_best_team(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (team varchar, team_country char(3), team_rank int, total_time float8, gap float8, stages int)
LANGUAGE sql STABLE AS $$
    WITH sel AS (SELECT * FROM fn_stage_selection(p_from, p_to, p_types)),
    totals AS (
        SELECT v.team, SUM(v.adjusted_time) AS total_time, COUNT(DISTINCT v.stage_id)::int AS stages
        FROM v_team_stage_riders v
        JOIN sel ON sel.stage_id = v.stage_id
        WHERE v.counted AND v.team_finishers >= 3
        GROUP BY v.team
        HAVING COUNT(DISTINCT v.stage_id) = (SELECT COUNT(*) FROM sel)
    )
    SELECT x.team, t.country, (RANK() OVER (ORDER BY x.total_time))::int, x.total_time,
        x.total_time - MIN(x.total_time) OVER (), x.stages
    FROM totals x
    JOIN teams t ON t.name = x.team
$$;

-- Best Team after each selected stage: cumulative time of each stage's 3 fastest riders, with the rank
-- and gap to the leading team at that point. A team drops out from the first stage it had under 3 finishers.
-- Its last stage equals fn_best_team.
CREATE OR REPLACE FUNCTION fn_best_team_by_stage(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (team varchar, stage_no int, seq int, cum_time float8, team_rank int, gap float8)
LANGUAGE sql STABLE AS $$
    WITH sel AS (SELECT * FROM fn_stage_selection(p_from, p_to, p_types)),
    daily AS (
        SELECT v.team, sel.seq, sel.stage_no, SUM(v.adjusted_time) AS t
        FROM v_team_stage_riders v
        JOIN sel ON sel.stage_id = v.stage_id
        WHERE v.counted AND v.team_finishers >= 3
        GROUP BY v.team, sel.seq, sel.stage_no
    ),
    cum AS (
        SELECT d.team, d.seq, d.stage_no,
            SUM(d.t) OVER (PARTITION BY d.team ORDER BY d.seq) AS cum_time,
            COUNT(*) OVER (PARTITION BY d.team ORDER BY d.seq) AS n
        FROM daily d
    )
    SELECT c.team, c.stage_no, c.seq, c.cum_time,
        (RANK() OVER (PARTITION BY c.seq ORDER BY c.cum_time))::int,
        c.cum_time - MIN(c.cum_time) OVER (PARTITION BY c.seq)
    FROM cum c
    WHERE c.n = c.seq
$$;

-- E3 drill: which riders carried the team's counted time.
CREATE OR REPLACE FUNCTION fn_team_contribution(p_team text, p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (rider_bib int, rider_name varchar, stages_counted int, stages_finished int, counted_time float8, share_pct float8)
LANGUAGE sql STABLE AS $$
    SELECT v.rider_bib, v.rider_name,
        (COUNT(*) FILTER (WHERE v.counted))::int,
        COUNT(*)::int,
        COALESCE(SUM(v.adjusted_time) FILTER (WHERE v.counted), 0),
        100 * COALESCE(SUM(v.adjusted_time) FILTER (WHERE v.counted), 0)
            / NULLIF(SUM(SUM(v.adjusted_time) FILTER (WHERE v.counted)) OVER (), 0)
    FROM v_team_stage_riders v
    JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = v.stage_id
    WHERE v.team = p_team
    GROUP BY v.rider_bib, v.rider_name
$$;

-- E14: a top-10 finish is one result with rank <= 10, so two riders from one team on one stage count 2.
-- stages and riders count distinct values, which keeps that double-counting visible.
CREATE OR REPLACE FUNCTION fn_top10_by_team(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (team varchar, flat int, hilly int, mountain int, itt int, finishes int, stages int, riders int)
LANGUAGE sql STABLE AS $$
    SELECT t.name,
        (COUNT(*) FILTER (WHERE x.type = 'flat'))::int,
        (COUNT(*) FILTER (WHERE x.type = 'hilly'))::int,
        (COUNT(*) FILTER (WHERE x.type = 'mountain'))::int,
        (COUNT(*) FILTER (WHERE x.type = 'individual time-trial'))::int,
        COUNT(x.rider_bib)::int,
        COUNT(DISTINCT x.stage_id)::int,
        COUNT(DISTINCT x.rider_bib)::int
    FROM teams t
    LEFT JOIN (
        SELECT r.team, r.rider_bib, r.stage_id, r.type
        FROM v_results_enriched r
        JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = r.stage_id
        WHERE r.rank <= 10
    ) x ON x.team = t.name
    GROUP BY t.name
$$;

-- E13: distinct riders per team, split by whether they finished the race.
CREATE OR REPLACE VIEW v_squad_depth AS
SELECT
    r.team,
    r.team_country,
    COUNT(DISTINCT r.rider_bib)::int AS distinct_riders,
    (COUNT(*) FILTER (WHERE r.exit_stage IS NULL))::int AS finished,
    (COUNT(*) FILTER (WHERE r.exit_stage IS NOT NULL))::int AS exited
FROM v_riders r
GROUP BY r.team, r.team_country;

CREATE OR REPLACE VIEW v_team_classification AS SELECT * FROM fn_best_team();
