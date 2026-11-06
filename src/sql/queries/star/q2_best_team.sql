-- Q2 Best team classification (3 fastest riders per team per stage), star schema
WITH ranked AS (
    SELECT f.team_key, f.adjusted_time AS adj,
           ROW_NUMBER() OVER (PARTITION BY f.stage_key, f.team_key ORDER BY f.adjusted_time, f.stage_rank) AS rn
    FROM star.fact_results f
)
SELECT dt.team_name AS team, dt.team_country_name AS team_country, SUM(ranked.adj) AS total_time,
       RANK() OVER (ORDER BY SUM(ranked.adj)) AS team_rank
FROM ranked
JOIN star.dim_team dt ON dt.team_key = ranked.team_key
WHERE ranked.rn <= 3
GROUP BY dt.team_name, dt.team_country_name
ORDER BY total_time, team;
