-- Q1 Cumulative time per rider (final GC), star schema
SELECT dr.rider_name AS rider, dr.team_name AS team, dr.nationality_name AS nationality,
       SUM(f.adjusted_time) AS total_time,
       RANK() OVER (ORDER BY SUM(f.adjusted_time)) AS gc_rank
FROM star.fact_results f
JOIN star.dim_rider dr ON dr.rider_key = f.rider_key
GROUP BY dr.rider_key, dr.rider_name, dr.team_name, dr.nationality_name
HAVING COUNT(*) = (SELECT COUNT(*) FROM star.dim_stage)
ORDER BY total_time, rider;
