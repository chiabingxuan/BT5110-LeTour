-- ETL: loads the star schema from the normalised tables. Run after 01_schema.sql (it starts empty).

INSERT INTO star.dim_country (iso, country_name)
SELECT iso, name FROM countries ORDER BY iso;

INSERT INTO star.dim_team (team_name, team_country_iso, team_country_name)
SELECT t.name, t.country, c.name
FROM teams t JOIN countries c ON c.iso = t.country
ORDER BY t.name;

INSERT INTO star.dim_rider (bib_num, rider_name, dob, age_at_start, nationality_iso, nationality_name,
                            team_name, team_country_iso, status, exit_stage_no, exit_reason)
SELECT r.bib_num, r.name, r.dob,
       date_part('year', age((SELECT MIN(date) FROM stages), r.dob))::int,
       r.country, c.name, r.team, t.country,
       CASE WHEN e.rider_bib IS NULL THEN 'Finished' WHEN e.reason = 'DNS' THEN 'DNS' ELSE 'Withdrawal' END,
       e.stage_id::int, e.reason
FROM riders r
JOIN countries c ON c.iso = r.country
JOIN teams t ON t.name = r.team
LEFT JOIN rider_exits e ON e.rider_bib = r.bib_num
ORDER BY r.bib_num;

INSERT INTO star.dim_stage (stage_id, stage_no, stage_date, stage_type, type_label, start_location,
                            start_country_iso, start_country_name, end_location, end_country_iso, end_country_name, dist_km)
SELECT s.id, s.id::int, s.date, s.type,
       CASE s.type WHEN 'flat' THEN 'Flat' WHEN 'hilly' THEN 'Hilly' WHEN 'mountain' THEN 'Mountain' ELSE 'ITT' END,
       s.start_location, ls.country, cs.name, s.end_location, le.country, ce.name, s.dist_covered
FROM stages s
JOIN locations ls ON ls.name = s.start_location
JOIN countries cs ON cs.iso = ls.country
JOIN locations le ON le.name = s.end_location
JOIN countries ce ON ce.iso = le.country
ORDER BY s.date;

INSERT INTO star.dim_date (date_key, full_date, day_of_week, race_day, is_weekend)
SELECT to_char(d, 'YYYYMMDD')::int, d, trim(to_char(d, 'Day')),
       d - (SELECT MIN(date) FROM stages) + 1,
       extract(isodow FROM d) >= 6
FROM generate_series((SELECT MIN(date) FROM stages), (SELECT MAX(date) FROM stages), interval '1 day') AS g(ts),
     LATERAL (SELECT g.ts::date AS d) AS day;

INSERT INTO star.fact_results (rider_key, stage_key, team_key, nationality_key, date_key, stage_rank,
                               finish_time, time_bonus, time_penalty, adjusted_time)
SELECT dr.rider_key, ds.stage_key, dt.team_key, dc.country_key, to_char(ds.stage_date, 'YYYYMMDD')::int,
       sr.rank, sr.finish_time, sr.time_bonus, sr.time_penalty,
       sr.finish_time - sr.time_bonus + sr.time_penalty
FROM stage_results sr
JOIN star.dim_rider dr ON dr.bib_num = sr.rider_bib
JOIN star.dim_stage ds ON ds.stage_id = sr.stage_id
JOIN star.dim_team dt ON dt.team_name = dr.team_name
JOIN star.dim_country dc ON dc.iso = dr.nationality_iso;

ANALYZE star.dim_country, star.dim_team, star.dim_rider, star.dim_stage, star.dim_date, star.fact_results;
