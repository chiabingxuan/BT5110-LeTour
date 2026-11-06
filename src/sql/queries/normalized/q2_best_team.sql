-- Q2 Best team classification (3 fastest riders per team per stage), normalised schema
WITH ranked AS (
    SELECT r.team, sr.finish_time - sr.time_bonus + sr.time_penalty AS adj,
           ROW_NUMBER() OVER (PARTITION BY sr.stage_id, r.team
                              ORDER BY sr.finish_time - sr.time_bonus + sr.time_penalty, sr.rank) AS rn
    FROM stage_results sr
    JOIN riders r ON r.bib_num = sr.rider_bib
)
SELECT t.name AS team, c.name AS team_country, SUM(ranked.adj) AS total_time,
       RANK() OVER (ORDER BY SUM(ranked.adj)) AS team_rank
FROM ranked
JOIN teams t ON t.name = ranked.team
JOIN countries c ON c.iso = t.country
WHERE ranked.rn <= 3
GROUP BY t.name, c.name
ORDER BY total_time, team;
