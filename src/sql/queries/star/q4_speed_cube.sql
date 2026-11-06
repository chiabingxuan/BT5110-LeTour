-- Q4 OLAP roll-up: average speed by stage type and rider nationality, with subtotals; star schema
SELECT ds.stage_type AS type, dc.country_name AS nationality,
       COUNT(*) AS results,
       ROUND(AVG(ds.dist_km / (f.adjusted_time / 3600.0)), 2) AS avg_speed_kmh
FROM star.fact_results f
JOIN star.dim_stage ds ON ds.stage_key = f.stage_key
JOIN star.dim_country dc ON dc.country_key = f.nationality_key
GROUP BY ROLLUP (ds.stage_type, dc.country_name)
ORDER BY ds.stage_type NULLS LAST, nationality NULLS LAST;
