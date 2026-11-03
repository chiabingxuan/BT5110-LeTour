-- Core views: the derived adjusted time (Task 2, Appendix B.1) and enriched stage / rider / result grains.
-- Stage order always comes from stages.date; stage_no is the numeric form of the VARCHAR stages.id.

CREATE OR REPLACE VIEW v_stage_results AS
SELECT r.*, (r.finish_time - r.time_bonus + r.time_penalty) AS adjusted_time
FROM stage_results r;

CREATE OR REPLACE VIEW v_stages AS
SELECT
    s.id AS stage_id,
    s.id::int AS stage_no,
    s.date,
    s.start_location,
    ls.country AS start_country,
    s.end_location,
    le.country AS end_country,
    s.dist_covered::float8 AS dist_km,
    s.type,
    CASE s.type
        WHEN 'flat' THEN 'Flat'
        WHEN 'hilly' THEN 'Hilly'
        WHEN 'mountain' THEN 'Mountain'
        WHEN 'individual time-trial' THEN 'ITT'
    END AS type_label,
    s.start_location || ' → ' || s.end_location AS route,
    'Stage ' || s.id || ': ' || s.start_location || ' → ' || s.end_location AS stage_label,
    w.rider_bib AS winner_bib,
    wr.name AS winner_name,
    w.adjusted_time::float8 AS winner_time,
    (s.dist_covered / (w.adjusted_time / 3600.0))::float8 AS winner_speed_kmh
FROM stages s
JOIN locations ls ON ls.name = s.start_location
JOIN locations le ON le.name = s.end_location
LEFT JOIN v_stage_results w ON w.stage_id = s.id AND w.rank = 1
LEFT JOIN riders wr ON wr.bib_num = w.rider_bib;

-- One row per rider. Age is anchored at race start (first stage date), never today.
CREATE OR REPLACE VIEW v_riders AS
SELECT
    r.bib_num AS rider_bib,
    r.name AS rider_name,
    r.dob,
    r.team,
    t.country AS team_country,
    r.country AS rider_country,
    c.name AS rider_country_name,
    date_part('year', age((SELECT MIN(date) FROM stages), r.dob))::int AS age_at_start,
    (r.dob >= DATE '2000-01-01') AS born_2000_plus,
    e.stage_id::int AS exit_stage,
    e.reason AS exit_reason,
    CASE
        WHEN e.rider_bib IS NULL THEN 'Finished'
        WHEN e.reason = 'DNS' THEN 'DNS'
        ELSE 'Withdrawal'
    END AS status
FROM riders r
JOIN teams t ON t.name = r.team
JOIN countries c ON c.iso = r.country
LEFT JOIN rider_exits e ON e.rider_bib = r.bib_num;

-- Rider x stage grain carrying every dimension, so slices can be filtered with a plain WHERE.
CREATE OR REPLACE VIEW v_results_enriched AS
SELECT
    sr.rider_bib,
    r.rider_name,
    r.team,
    r.team_country,
    r.rider_country,
    r.age_at_start,
    s.stage_id,
    s.stage_no,
    s.date,
    s.type,
    s.type_label,
    s.route,
    s.dist_km,
    sr.rank,
    sr.finish_time::float8 AS finish_time,
    sr.time_bonus::float8 AS time_bonus,
    sr.time_penalty::float8 AS time_penalty,
    sr.adjusted_time::float8 AS adjusted_time,
    (sr.adjusted_time - MIN(sr.adjusted_time) OVER (PARTITION BY sr.stage_id))::float8 AS gap_to_winner,
    (s.dist_km / (sr.adjusted_time::float8 / 3600.0)) AS speed_kmh
FROM v_stage_results sr
JOIN v_riders r ON r.rider_bib = sr.rider_bib
JOIN v_stages s ON s.stage_id = sr.stage_id;

CREATE OR REPLACE VIEW v_exits AS
SELECT
    e.rider_bib,
    r.rider_name,
    r.team,
    r.rider_country,
    e.stage_id::int AS stage_no,
    r.status AS reason
FROM rider_exits e
JOIN v_riders r ON r.rider_bib = e.rider_bib;

-- Roll-up of distance by stage type; the total row has is_total = 1.
CREATE OR REPLACE VIEW v_stage_type_rollup AS
SELECT
    type_label,
    GROUPING(type_label) AS is_total,
    COUNT(*)::int AS stages,
    SUM(dist_km) AS km
FROM v_stages
GROUP BY ROLLUP (type_label);

-- The set of selected stages, in date order. seq is the position inside the selection.
-- p_types = NULL means every stage type.
CREATE OR REPLACE FUNCTION fn_stage_selection(p_from int DEFAULT 1, p_to int DEFAULT 21, p_types text[] DEFAULT NULL)
RETURNS TABLE (stage_id varchar, stage_no int, seq int, type varchar)
LANGUAGE sql STABLE AS $$
    SELECT s.id, s.id::int, (ROW_NUMBER() OVER (ORDER BY s.date))::int, s.type
    FROM stages s
    WHERE s.id::int BETWEEN p_from AND p_to
      AND (p_types IS NULL OR s.type = ANY (p_types))
$$;
