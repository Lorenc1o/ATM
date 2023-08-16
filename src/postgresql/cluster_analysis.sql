-- To compute the STD per hour
WITH TMP AS (
    SELECT start_time, 
           SUM(intersection_count) as total_sum, 
           COUNT(*) as total
    FROM grid_hourly_clusters_py
    GROUP BY start_time
)
SELECT start_time, 
       SUM((intersection_count - t.total_sum/t.total)^2)/t.total as std
FROM grid_hourly_clusters_py as g
JOIN TMP as t ON g.start_time = t.start_time
GROUP BY g.start_time, t.total_sum, t.total
ORDER BY g.start_time;