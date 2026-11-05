-- Young rider, mountain proxy and the derived Points / KOM classifications (req b, E4).

-- E4: GC restricted to young riders. p_rule: 'age' (age at race start < p_cutoff) | 'official' (born >= 1 Jan 2000).
CREATE OR REPLACE FUNCTION fn_young_gc(
    p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL, p_after int DEFAULT NULL,
    p_rule text DEFAULT 'age', p_cutoff int DEFAULT 26
)
RETURNS TABLE (rider_bib int, young_rank int, cum_time float8, gc_rank int, gap_to_gc_leader float8)
LANGUAGE sql STABLE AS $$
    SELECT g.rider_bib, (RANK() OVER (ORDER BY g.gc_rank))::int, g.cum_time, g.gc_rank, g.gap
    FROM fn_gc_final(p_from, p_to, p_types, p_after) g
    JOIN v_riders r ON r.rider_bib = g.rider_bib
    WHERE (p_rule = 'official' AND r.born_2000_plus)
       OR (p_rule <> 'official' AND r.age_at_start < p_cutoff)
$$;

-- E4: adjusted time summed over the selected mountain stages only; riders must have finished all of them.
CREATE OR REPLACE FUNCTION fn_mountain_proxy(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (rider_bib int, mountain_rank int, mountain_time float8, mountain_stages int)
LANGUAGE sql STABLE AS $$
    WITH mtn AS (
        SELECT sel.stage_id FROM fn_stage_selection(p_from, p_to, p_types) sel WHERE sel.type = 'mountain'
    ),
    totals AS (
        SELECT sr.rider_bib, SUM(sr.adjusted_time)::float8 AS mountain_time, COUNT(*)::int AS stages
        FROM v_stage_results sr
        JOIN mtn ON mtn.stage_id = sr.stage_id
        GROUP BY sr.rider_bib
        HAVING COUNT(*) = (SELECT COUNT(*) FROM mtn)
    )
    SELECT t.rider_bib, (RANK() OVER (ORDER BY t.mountain_time))::int, t.mountain_time, t.stages
    FROM totals t
$$;

-- ASSUMPTION: the schema stores no points, so Points and KOM are DERIVED from stage finishing positions.
-- This is not the official scoring: intermediate sprints and categorised climbs are not in the data.
-- Change a scale here and every classification view follows.
CREATE OR REPLACE VIEW v_points_scale AS
SELECT 'points' AS classification, t.type, s.ord::int AS rank, s.points
FROM (VALUES
    ('flat', ARRAY[50,30,20,18,16,14,12,10,8,7,6,5,4,3,2]),
    ('hilly', ARRAY[30,25,22,19,17,15,13,11,9,7,6,5,4,3,2]),
    ('mountain', ARRAY[20,17,15,13,11,10,9,8,7,6,5,4,3,2,1]),
    ('individual time-trial', ARRAY[20,17,15,13,11,10,9,8,7,6,5,4,3,2,1])
) AS t(type, scale)
CROSS JOIN LATERAL UNNEST(t.scale) WITH ORDINALITY AS s(points, ord)
UNION ALL
SELECT 'kom', t.type, s.ord::int, s.points
FROM (VALUES
    ('mountain', ARRAY[20,15,12,10,8,6,4,2]),
    ('hilly', ARRAY[5,3,2,1])
) AS t(type, scale)
CROSS JOIN LATERAL UNNEST(t.scale) WITH ORDINALITY AS s(points, ord);

-- Derived classification over the selection, ranked among riders who finished every selected stage.
-- p_classification: 'points' | 'kom'. Riders with no points are not ranked.
CREATE OR REPLACE FUNCTION fn_derived_classification(
    p_classification text, p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL, p_after int DEFAULT NULL
)
RETURNS TABLE (rider_bib int, points int, class_rank int)
LANGUAGE sql STABLE AS $$
    WITH bound AS (SELECT LEAST(p_to, COALESCE(p_after, p_to)) AS last_stage),
    earned AS (
        SELECT sr.rider_bib, SUM(ps.points)::int AS points
        FROM bound, stage_results sr
        JOIN fn_stage_selection(p_from, (SELECT last_stage FROM bound), p_types) sel ON sel.stage_id = sr.stage_id
        JOIN v_points_scale ps ON ps.classification = p_classification AND ps.type = sel.type AND ps.rank = sr.rank
        GROUP BY sr.rider_bib
    )
    SELECT e.rider_bib, e.points, (RANK() OVER (ORDER BY e.points DESC))::int
    FROM earned e
    JOIN fn_gc_final(p_from, p_to, p_types, p_after) g ON g.rider_bib = e.rider_bib
$$;

-- Req b, E4: every ranking side by side for the riders ranked in GC.
CREATE OR REPLACE FUNCTION fn_classification_compare(
    p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL, p_after int DEFAULT NULL,
    p_rule text DEFAULT 'age', p_cutoff int DEFAULT 26
)
RETURNS TABLE (
    rider_bib int, gc_rank int, points_rank int, points int, kom_rank int, kom_points int,
    young_rank int, mountain_rank int, proxy_vs_gc int
)
LANGUAGE sql STABLE AS $$
    SELECT g.rider_bib, g.gc_rank, p.class_rank, p.points, k.class_rank, k.points, y.young_rank, m.mountain_rank,
        g.gc_rank - m.mountain_rank
    FROM fn_gc_final(p_from, p_to, p_types, p_after) g
    LEFT JOIN fn_derived_classification('points', p_from, p_to, p_types, p_after) p ON p.rider_bib = g.rider_bib
    LEFT JOIN fn_derived_classification('kom', p_from, p_to, p_types, p_after) k ON k.rider_bib = g.rider_bib
    LEFT JOIN fn_young_gc(p_from, p_to, p_types, p_after, p_rule, p_cutoff) y ON y.rider_bib = g.rider_bib
    LEFT JOIN fn_mountain_proxy(p_from, LEAST(p_to, COALESCE(p_after, p_to)), p_types) m ON m.rider_bib = g.rider_bib
$$;

CREATE OR REPLACE VIEW v_young_rider AS SELECT * FROM fn_young_gc();
CREATE OR REPLACE VIEW v_points_proxy AS SELECT * FROM fn_derived_classification('points');
CREATE OR REPLACE VIEW v_kom_proxy AS SELECT * FROM fn_derived_classification('kom');
