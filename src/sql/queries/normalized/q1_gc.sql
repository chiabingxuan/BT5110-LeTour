-- Q1 Cumulative time per rider (final GC), normalised schema
SELECT r.name AS rider, r.team, c.name AS nationality,
       SUM(sr.finish_time - sr.time_bonus + sr.time_penalty) AS total_time,
       RANK() OVER (ORDER BY SUM(sr.finish_time - sr.time_bonus + sr.time_penalty)) AS gc_rank
FROM stage_results sr
JOIN riders r ON r.bib_num = sr.rider_bib
JOIN countries c ON c.iso = r.country
GROUP BY r.bib_num, r.name, r.team, c.name
HAVING COUNT(*) = (SELECT COUNT(*) FROM stages)
ORDER BY total_time, rider;
