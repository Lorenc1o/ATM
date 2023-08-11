DROP TABLE IF EXISTS hourly_intervals;

CREATE TABLE hourly_intervals AS 
SELECT 
    generate_series(
        '2015-06-01 00:00:00'::timestamp, 
        '2015-06-01 23:00:00'::timestamp, 
        '1 hour'::interval
    ) as start_time, 
    generate_series(
        '2015-06-01 01:00:00'::timestamp, 
        '2015-06-02 00:00:00'::timestamp, 
        '1 hour'::interval
    ) as end_time;
	
DROP TABLE IF EXISTS hourly_flights;

CREATE TABLE hourly_flights AS 
SELECT 
    f.ECTRL as ECTRL, 
    i.start_time as start_time, 
    i.end_time as end_time,
    atTime(f.trip, ('[' || i.start_time::text || ', ' || i.end_time::text || ']')::tstzspan) as Trip
FROM 
    flights f, hourly_intervals i
WHERE
	atTime(f.trip, ('[' || i.start_time::text || ', ' || i.end_time::text || ']')::tstzspan) IS NOT NULL;

ALTER TABLE hourly_flights ADD COLUMN Traj geometry;
UPDATE hourly_flights SET Traj = trajectory(Trip);

DROP TABLE IF EXISTS grid_hourly_intersections;

CREATE TABLE grid_hourly_intersections AS 
SELECT 
    g.geom, 
    i.start_time, 
    i.end_time, 
    COUNT(f.ectrl) as intersection_count
FROM grid g
CROSS JOIN hourly_intervals i 
LEFT JOIN (
    SELECT f.ectrl, f.start_time, f.end_time, f.Traj
    FROM hourly_flights f
) AS f ON i.start_time = f.start_time AND i.end_time = f.end_time AND ST_Intersects(g.geom, f.Traj::geometry)
GROUP BY g.geom, i.start_time, i.end_time;

SELECT COUNT(DISTINCT geom) FROM grid_hourly_intersections GROUP BY start_time;
SELECT COUNT(DISTINCT geom) FROM grid;

DO
$$
DECLARE
    table_name text;
BEGIN
    FOR table_name IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public')
    LOOP
        EXECUTE format('GRANT ALL PRIVILEGES ON TABLE %I TO atm', table_name);
    END LOOP;
END;
$$;