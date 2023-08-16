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
    g.id, 
	g.geom,
    i.start_time, 
    i.end_time, 
    SUM(CASE WHEN ST_Intersects(f1.Traj::geometry, f2.Traj::geometry) THEN 1 END) as intersection_count
FROM grid g
CROSS JOIN hourly_intervals i 
LEFT JOIN (
    SELECT f1.ectrl, f1.start_time, f1.end_time, f1.Traj
    FROM hourly_flights f1
) AS f1 ON i.start_time = f1.start_time AND i.end_time = f1.end_time AND ST_Intersects(g.geom, f1.Traj::geometry)
JOIN (
	SELECT f2.ectrl, f2.start_time, f2.end_time, f2.Traj
    FROM hourly_flights f2
) AS f2 ON i.start_time = f2.start_time AND i.end_time = f2.end_time AND ST_Intersects(g.geom, f2.Traj::geometry)
GROUP BY g.id, g.geom, i.start_time, i.end_time;

INSERT INTO grid_hourly_intersections (id, geom, start_time, end_time, intersection_count)
SELECT g.id, g.geom, i.start_time, i.end_time, 0 as intersection_count
FROM grid g
CROSS JOIN hourly_intervals i
WHERE NOT EXISTS (
    SELECT 1
    FROM grid_hourly_intersections gi
    WHERE g.id = gi.id AND gi.start_time = i.start_time
);

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