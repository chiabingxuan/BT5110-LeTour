-- Q4 OLAP roll-up: average speed by stage type and rider nationality, with subtotals; normalised schema
SELECT s.type, c.name AS nationality,
       COUNT(*) AS results,
       ROUND(AVG(s.dist_covered / ((sr.finish_time - sr.time_bonus + sr.time_penalty) / 3600.0)), 2) AS avg_speed_kmh
FROM stage_results sr
JOIN stages s ON s.id = sr.stage_id
JOIN riders r ON r.bib_num = sr.rider_bib
JOIN countries c ON c.iso = r.country
GROUP BY ROLLUP (s.type, c.name)
ORDER BY s.type NULLS LAST, nationality NULLS LAST;
