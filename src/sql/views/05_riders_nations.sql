-- Rider profiles (E5, E6, E12) and national analytics (E8, E9).

-- E5: mountain podiums and mean gap to the stage winner, for riders who finished every selected mountain stage.
CREATE OR REPLACE FUNCTION fn_mountain_contours(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (rider_bib int, rider_name varchar, team varchar, podiums int, mean_gap float8, stages int)
LANGUAGE sql STABLE AS $$
    WITH mtn AS (
        SELECT sel.stage_id FROM fn_stage_selection(p_from, p_to, p_types) sel WHERE sel.type = 'mountain'
    )
    SELECT r.rider_bib, r.rider_name, r.team,
        (COUNT(*) FILTER (WHERE r.rank <= 3))::int,
        AVG(r.gap_to_winner),
        COUNT(*)::int
    FROM v_results_enriched r
    JOIN mtn ON mtn.stage_id = r.stage_id
    GROUP BY r.rider_bib, r.rider_name, r.team
    HAVING COUNT(*) = (SELECT COUNT(*) FROM mtn)
$$;

-- E6: each rider's average speed per stage type, with the peloton median for that type.
CREATE OR REPLACE FUNCTION fn_speed_by_type(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (rider_bib int, rider_name varchar, team varchar, type varchar, type_label text, avg_speed float8, median_speed float8)
LANGUAGE sql STABLE AS $$
    WITH by_rider AS (
        SELECT r.rider_bib, r.rider_name, r.team, r.type, r.type_label, AVG(r.speed_kmh) AS avg_speed
        FROM v_results_enriched r
        JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = r.stage_id
        GROUP BY r.rider_bib, r.rider_name, r.team, r.type, r.type_label
    ),
    medians AS (
        SELECT b.type, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.avg_speed) AS median_speed
        FROM by_rider b
        GROUP BY b.type
    )
    SELECT b.rider_bib, b.rider_name, b.team, b.type, b.type_label, b.avg_speed, m.median_speed
    FROM by_rider b
    JOIN medians m ON m.type = b.type
$$;

-- E6: gain % = (mountain speed / median) - (flat and hilly speed / median). Riders must have finished the selection.
CREATE OR REPLACE FUNCTION fn_speed_gainers_riders(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (rider_bib int, rider_name varchar, team varchar, gain_pct float8)
LANGUAGE sql STABLE AS $$
    SELECT s.rider_bib, s.rider_name, s.team,
        100 * (
            AVG(s.avg_speed / s.median_speed) FILTER (WHERE s.type = 'mountain')
            - AVG(s.avg_speed / s.median_speed) FILTER (WHERE s.type IN ('flat', 'hilly'))
        )
    FROM fn_speed_by_type(p_from, p_to, p_types) s
    JOIN fn_gc_final(p_from, p_to, p_types) g ON g.rider_bib = s.rider_bib
    GROUP BY s.rider_bib, s.rider_name, s.team
    HAVING COUNT(*) FILTER (WHERE s.type = 'mountain') > 0
       AND COUNT(*) FILTER (WHERE s.type IN ('flat', 'hilly')) > 0
$$;

-- E6: the same gain at team level, using the mean of the team's rider averages per stage type.
CREATE OR REPLACE FUNCTION fn_speed_gainers_teams(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (team varchar, gain_pct float8)
LANGUAGE sql STABLE AS $$
    WITH by_team AS (
        SELECT s.team, s.type, AVG(s.avg_speed) / MAX(s.median_speed) AS relative
        FROM fn_speed_by_type(p_from, p_to, p_types) s
        GROUP BY s.team, s.type
    )
    SELECT b.team,
        100 * (
            AVG(b.relative) FILTER (WHERE b.type = 'mountain')
            - AVG(b.relative) FILTER (WHERE b.type IN ('flat', 'hilly'))
        )
    FROM by_team b
    GROUP BY b.team
    HAVING COUNT(*) FILTER (WHERE b.type = 'mountain') > 0
       AND COUNT(*) FILTER (WHERE b.type IN ('flat', 'hilly')) > 0
$$;

-- E12: riders by count of top-10 finishes in the selection.
CREATE OR REPLACE FUNCTION fn_top10_by_rider(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (rider_bib int, rider_name varchar, team varchar, rider_country char(3), finishes int)
LANGUAGE sql STABLE AS $$
    SELECT r.rider_bib, r.rider_name, r.team, r.rider_country, COUNT(*)::int
    FROM v_results_enriched r
    JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = r.stage_id
    WHERE r.rank <= 10
    GROUP BY r.rider_bib, r.rider_name, r.team, r.rider_country
$$;

-- Req d, E8: riders per rider country and teams per team country. These are separate dimensions.
-- is_total = 1 marks each dimension's ROLLUP total row.
CREATE OR REPLACE VIEW v_country_participation AS
SELECT 'rider' AS dimension, r.country AS iso, c.name AS country_name, GROUPING(r.country, c.name) AS is_total, COUNT(*)::int AS n
FROM riders r
JOIN countries c ON c.iso = r.country
GROUP BY ROLLUP ((r.country, c.name))
UNION ALL
SELECT 'team', t.country, c.name, GROUPING(t.country, c.name), COUNT(*)::int
FROM teams t
JOIN countries c ON c.iso = t.country
GROUP BY ROLLUP ((t.country, c.name));

CREATE OR REPLACE VIEW v_country_kpis AS
SELECT
    (SELECT COUNT(DISTINCT country) FROM riders)::int AS rider_nations,
    (SELECT COUNT(DISTINCT country) FROM teams)::int AS team_nations,
    (SELECT COUNT(*) FROM countries)::int AS countries_in_db,
    (SELECT COUNT(*) FROM countries c
        WHERE NOT EXISTS (SELECT 1 FROM riders r WHERE r.country = c.iso))::int AS countries_without_riders,
    (SELECT COUNT(*) FROM v_riders WHERE rider_country <> team_country)::int AS riders_abroad,
    (SELECT COUNT(*) FROM riders)::int AS riders;

-- E9: per nation, best GC rank, stage wins and stage podiums over the selection.
CREATE OR REPLACE FUNCTION fn_national_outcomes(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (iso char(3), country_name varchar, riders int, best_gc int, best_gc_bib int, best_gc_rider varchar, stage_wins int, podiums int)
LANGUAGE sql STABLE AS $$
    WITH best AS (
        SELECT DISTINCT ON (r.rider_country) r.rider_country, g.gc_rank, g.rider_bib, r.rider_name
        FROM fn_gc_final(p_from, p_to, p_types) g
        JOIN v_riders r ON r.rider_bib = g.rider_bib
        ORDER BY r.rider_country, g.gc_rank, g.rider_bib
    ),
    results AS (
        SELECT x.rider_country,
            (COUNT(*) FILTER (WHERE x.rank = 1))::int AS stage_wins,
            (COUNT(*) FILTER (WHERE x.rank <= 3))::int AS podiums
        FROM v_results_enriched x
        JOIN fn_stage_selection(p_from, p_to, p_types) sel ON sel.stage_id = x.stage_id
        GROUP BY x.rider_country
    ),
    nation AS (
        SELECT r.rider_country, r.rider_country_name, COUNT(*)::int AS riders
        FROM v_riders r
        GROUP BY r.rider_country, r.rider_country_name
    )
    SELECT n.rider_country, n.rider_country_name, n.riders, b.gc_rank, b.rider_bib, b.rider_name,
        COALESCE(x.stage_wins, 0), COALESCE(x.podiums, 0)
    FROM nation n
    LEFT JOIN best b ON b.rider_country = n.rider_country
    LEFT JOIN results x ON x.rider_country = n.rider_country
$$;
