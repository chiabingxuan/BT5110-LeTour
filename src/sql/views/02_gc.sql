-- General classification, recomputed over any slice of stages.
-- A rider is ranked after a stage only with a result on every selected stage up to it.

-- E1, E7, E10: GC after each selected stage. p_cf: 'actual' | 'no_bonus' | 'no_penalty' | 'no_both'.
CREATE OR REPLACE FUNCTION fn_gc_by_stage(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL, p_cf text DEFAULT 'actual')
RETURNS TABLE (rider_bib int, stage_no int, seq int, stage_time float8, cum_time float8, gc_rank int, gap float8, prev_rank int, prev_gap float8)
LANGUAGE sql STABLE AS $$
    WITH timed AS (
        SELECT sr.rider_bib, sel.stage_no, sel.seq,
            CASE p_cf
                WHEN 'no_bonus' THEN sr.finish_time + sr.time_penalty
                WHEN 'no_penalty' THEN sr.finish_time - sr.time_bonus
                WHEN 'no_both' THEN sr.finish_time
                ELSE sr.finish_time - sr.time_bonus + sr.time_penalty
            END::float8 AS stage_time
        FROM stage_results sr
        JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = sr.stage_id
    ),
    cumulative AS (
        SELECT t.*,
            SUM(t.stage_time) OVER w AS cum_time,
            COUNT(*) OVER w AS stages_done
        FROM timed t
        WINDOW w AS (PARTITION BY t.rider_bib ORDER BY t.seq)
    ),
    ranked AS (
        SELECT c.*,
            (RANK() OVER (PARTITION BY c.seq ORDER BY c.cum_time))::int AS gc_rank,
            c.cum_time - MIN(c.cum_time) OVER (PARTITION BY c.seq) AS gap
        FROM cumulative c
        WHERE c.stages_done = c.seq
    )
    SELECT r.rider_bib, r.stage_no, r.seq, r.stage_time, r.cum_time, r.gc_rank, r.gap,
        LAG(r.gc_rank) OVER w AS prev_rank,
        LAG(r.gap) OVER w AS prev_gap
    FROM ranked r
    WINDOW w AS (PARTITION BY r.rider_bib ORDER BY r.seq)
$$;

-- E1, E7: GC after the last selected stage (or after p_after), with the counterfactual replays.
-- A rider is ranked only with a result on every selected stage in range.
CREATE OR REPLACE FUNCTION fn_gc_final(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL, p_after int DEFAULT NULL)
RETURNS TABLE (
    rider_bib int, gc_rank int, cum_time float8, gap float8, total_bonus float8, total_penalty float8,
    no_bonus_rank int, no_bonus_time float8, no_bonus_gap float8,
    no_penalty_rank int, no_penalty_time float8, no_penalty_gap float8,
    no_both_rank int, no_both_time float8, no_both_gap float8
)
LANGUAGE sql STABLE AS $$
    WITH sel AS (
        SELECT * FROM fn_stage_selection(p_from, LEAST(p_to, COALESCE(p_after, p_to)), p_types)
    ),
    totals AS (
        SELECT sr.rider_bib,
            SUM(sr.finish_time - sr.time_bonus + sr.time_penalty)::float8 AS actual_time,
            SUM(sr.finish_time + sr.time_penalty)::float8 AS no_bonus_time,
            SUM(sr.finish_time - sr.time_bonus)::float8 AS no_penalty_time,
            SUM(sr.finish_time)::float8 AS no_both_time,
            SUM(sr.time_bonus)::float8 AS total_bonus,
            SUM(sr.time_penalty)::float8 AS total_penalty
        FROM stage_results sr
        JOIN sel ON sel.stage_id = sr.stage_id
        GROUP BY sr.rider_bib
        HAVING COUNT(*) = (SELECT COUNT(*) FROM sel)
    )
    SELECT t.rider_bib,
        (RANK() OVER (ORDER BY t.actual_time))::int, t.actual_time, t.actual_time - MIN(t.actual_time) OVER (),
        t.total_bonus, t.total_penalty,
        (RANK() OVER (ORDER BY t.no_bonus_time))::int, t.no_bonus_time, t.no_bonus_time - MIN(t.no_bonus_time) OVER (),
        (RANK() OVER (ORDER BY t.no_penalty_time))::int, t.no_penalty_time, t.no_penalty_time - MIN(t.no_penalty_time) OVER (),
        (RANK() OVER (ORDER BY t.no_both_time))::int, t.no_both_time, t.no_both_time - MIN(t.no_both_time) OVER ()
    FROM totals t
$$;

-- E1: pivotal moment = the stage with the largest swing in the rider's gap to the GC leader;
-- ties go to the bigger rank change, then to the later stage.
CREATE OR REPLACE FUNCTION fn_pivotal(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL, p_after int DEFAULT NULL)
RETURNS TABLE (rider_bib int, stage_no int, prev_rank int, gc_rank int, delta_gap float8)
LANGUAGE sql STABLE AS $$
    WITH swings AS (
        SELECT g.rider_bib, g.stage_no, g.prev_rank, g.gc_rank, g.gap - g.prev_gap AS delta_gap,
            ROW_NUMBER() OVER (
                PARTITION BY g.rider_bib
                ORDER BY ABS(g.gap - g.prev_gap) DESC, ABS(g.gc_rank - g.prev_rank) DESC, g.seq DESC
            ) AS rn
        FROM fn_gc_by_stage(p_from, LEAST(p_to, COALESCE(p_after, p_to)), p_types, 'actual') g
        WHERE g.prev_rank IS NOT NULL
    )
    SELECT s.rider_bib, s.stage_no, s.prev_rank, s.gc_rank, s.delta_gap
    FROM swings s
    WHERE s.rn = 1
$$;

-- E10: who holds yellow after each stage. Riders level on time are separated by the lowest sum of stage
-- placings, the official tie-break. change_no numbers each stage where the jersey changes hands.
CREATE OR REPLACE FUNCTION fn_yellow_changes(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (stage_no int, seq int, holder_bib int, holder_name varchar, is_tie boolean, tied_with text, is_change boolean, change_no int)
LANGUAGE sql STABLE AS $$
    WITH places AS (
        SELECT sr.rider_bib, sel.seq, SUM(sr.rank) OVER (PARTITION BY sr.rider_bib ORDER BY sel.seq) AS place_sum
        FROM stage_results sr
        JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = sr.stage_id
    ),
    leaders AS (
        SELECT g.stage_no, g.seq, g.rider_bib, r.name,
            COUNT(*) OVER (PARTITION BY g.seq) AS tied,
            STRING_AGG(r.name, ', ') OVER (PARTITION BY g.seq) AS names,
            ROW_NUMBER() OVER (PARTITION BY g.seq ORDER BY p.place_sum, g.rider_bib) AS rn
        FROM fn_gc_by_stage(p_from, p_to, p_types, 'actual') g
        JOIN places p ON p.rider_bib = g.rider_bib AND p.seq = g.seq
        JOIN riders r ON r.bib_num = g.rider_bib
        WHERE g.gc_rank = 1
    ),
    flagged AS (
        SELECT l.*, COALESCE(LAG(l.rider_bib) OVER (ORDER BY l.seq) <> l.rider_bib, TRUE) AS is_change
        FROM leaders l
        WHERE l.rn = 1
    )
    SELECT f.stage_no, f.seq, f.rider_bib, f.name, f.tied > 1, CASE WHEN f.tied > 1 THEN f.names END, f.is_change,
        (SUM(f.is_change::int) OVER (ORDER BY f.seq))::int
    FROM flagged f
$$;

-- E10: every stage where a plotted rider's GC rank differs from the previous selected stage.
CREATE OR REPLACE FUNCTION fn_gc_inflections(p_bibs int[], p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (stage_no int, rider_bib int, prev_rank int, gc_rank int, delta_gap float8, takes_yellow boolean)
LANGUAGE sql STABLE AS $$
    SELECT g.stage_no, g.rider_bib, g.prev_rank, g.gc_rank, g.gap - g.prev_gap,
        (y.is_change AND g.rider_bib = y.holder_bib)
    FROM fn_gc_by_stage(p_from, p_to, p_types, 'actual') g
    JOIN fn_yellow_changes(p_from, p_to, p_types) y ON y.seq = g.seq
    WHERE g.rider_bib = ANY (p_bibs)
      AND g.prev_rank IS NOT NULL
      AND g.prev_rank <> g.gc_rank
$$;

-- E7: riders whose top-10 membership differs from the actual GC, after each stage, in a counterfactual replay.
CREATE OR REPLACE FUNCTION fn_top10_movement(p_cf text, p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (stage_no int, rider_bib int, actual_rank int, replay_rank int, movement text)
LANGUAGE sql STABLE AS $$
    SELECT a.stage_no, a.rider_bib, a.gc_rank, r.gc_rank,
        CASE WHEN r.gc_rank <= 10 THEN 'enters' ELSE 'leaves' END
    FROM fn_gc_by_stage(p_from, p_to, p_types, 'actual') a
    JOIN fn_gc_by_stage(p_from, p_to, p_types, p_cf) r ON r.rider_bib = a.rider_bib AND r.seq = a.seq
    WHERE (a.gc_rank <= 10) <> (r.gc_rank <= 10)
$$;

-- Race-level KPIs for the selection (Overview tiles).
CREATE OR REPLACE FUNCTION fn_race_kpis(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (stages int, itt_stages int, km float8, starters int, finishers int, exits int, nations int, margin float8)
LANGUAGE sql STABLE AS $$
    WITH sel AS (
        SELECT s.* FROM fn_stage_selection(p_from, p_to, p_types) x JOIN v_stages s ON s.stage_id = x.stage_id
    ),
    span AS (SELECT MIN(stage_no) AS first_stage, MAX(stage_no) AS last_stage FROM sel),
    gc AS (SELECT * FROM fn_gc_final(p_from, p_to, p_types))
    SELECT
        (SELECT COUNT(*) FROM sel)::int,
        (SELECT COUNT(*) FROM sel WHERE type = 'individual time-trial')::int,
        (SELECT SUM(dist_km) FROM sel),
        (SELECT COUNT(*) FROM v_riders, span WHERE exit_stage IS NULL OR exit_stage >= span.first_stage)::int,
        (SELECT COUNT(*) FROM gc)::int,
        (SELECT COUNT(*) FROM v_exits, span WHERE v_exits.stage_no BETWEEN span.first_stage AND span.last_stage)::int,
        (SELECT COUNT(DISTINCT rider_country) FROM v_riders)::int,
        (SELECT gap FROM gc ORDER BY gc_rank, rider_bib OFFSET 1 LIMIT 1)
$$;

-- Full-race shortcuts for ad-hoc queries and the Task 4 comparison.
CREATE OR REPLACE VIEW v_gc_by_stage AS SELECT * FROM fn_gc_by_stage();
CREATE OR REPLACE VIEW v_gc_final AS SELECT * FROM fn_gc_final();
