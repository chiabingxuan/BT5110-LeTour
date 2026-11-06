-- Q3 Stage-by-stage performance: route, countries, finishers, winner, winning time, field speed; normalised schema
SELECT s.id::int AS stage_no, s.type, s.start_location || ' → ' || s.end_location AS route,
       cs.name AS start_country, ce.name AS end_country,
       COUNT(*) AS finishers,
       MAX(r.name) FILTER (WHERE sr.rank = 1) AS winner,
       MIN(sr.finish_time - sr.time_bonus + sr.time_penalty) AS winner_time,
       ROUND(AVG(s.dist_covered / ((sr.finish_time - sr.time_bonus + sr.time_penalty) / 3600.0)), 2) AS avg_speed_kmh
FROM stages s
JOIN locations ls ON ls.name = s.start_location
JOIN countries cs ON cs.iso = ls.country
JOIN locations le ON le.name = s.end_location
JOIN countries ce ON ce.iso = le.country
JOIN stage_results sr ON sr.stage_id = s.id
JOIN riders r ON r.bib_num = sr.rider_bib
GROUP BY s.id, s.date, s.type, s.start_location, s.end_location, cs.name, ce.name, s.dist_covered
ORDER BY s.date;
