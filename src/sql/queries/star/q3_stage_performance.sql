-- Q3 Stage-by-stage performance: route, countries, finishers, winner, winning time, field speed; star schema
SELECT ds.stage_no, ds.stage_type AS type, ds.start_location || ' → ' || ds.end_location AS route,
       ds.start_country_name AS start_country, ds.end_country_name AS end_country,
       COUNT(*) AS finishers,
       MAX(dr.rider_name) FILTER (WHERE f.stage_rank = 1) AS winner,
       MIN(f.adjusted_time) AS winner_time,
       ROUND(AVG(ds.dist_km / (f.adjusted_time / 3600.0)), 2) AS avg_speed_kmh
FROM star.fact_results f
JOIN star.dim_stage ds ON ds.stage_key = f.stage_key
JOIN star.dim_rider dr ON dr.rider_key = f.rider_key
GROUP BY ds.stage_key, ds.stage_no, ds.stage_date, ds.stage_type, ds.start_location, ds.end_location,
         ds.start_country_name, ds.end_country_name
ORDER BY ds.stage_date;
