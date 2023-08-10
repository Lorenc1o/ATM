-- 1. Create grid
DROP TABLE IF EXISTS grid;

CREATE TABLE grid AS 
SELECT ST_MakeEnvelope(x, y, x + 0.2, y + 0.2, 4326) as geom 
FROM generate_series(-10.1, 4.9, 0.2) AS x, 
     generate_series(35.9, 43.9, 0.2) AS y;

-- 2. Count intersections in each cell
DROP TABLE IF EXISTS grid_intersections;

CREATE TABLE grid_intersections AS 
SELECT g.geom, COUNT(f.ECTRL) as intersection_count 
FROM grid g 
LEFT JOIN flights f 
ON ST_Intersects(g.geom, f.Traj::geometry) 
GROUP BY g.geom;

-- 3. Cluster
DROP TABLE IF EXISTS grid_clusters;

CREATE TABLE grid_clusters AS 
SELECT g.geom, ST_ClusterKMeans(g.geom, 5) over () as cluster_id 
FROM grid_intersections g;

SELECT cluster_id, COUNT(cluster_id) FROM grid_clusters GROUP BY cluster_id;

------------------------------------------------------------------
-- Let's also compute intersections taking into account the time--
------------------------------------------------------------------

-- 1. Create grid with time
DROP TABLE IF EXISTS grid_time;

CREATE TABLE grid_time AS
WITH min_max AS (
    SELECT MIN(traj) as min_time, MAX(TrajTime) as max_time FROM flights
)
SELECT ST_MakeEnvelope(x, y, x + 0.2, y + 0.2, 4326) as geom,
           generate_series(min_time, max_time, '30 minutes'::interval) as time
FROM generate_series(-10.1, 4.9, 0.2) AS x,
     generate_series(35.9, 43.9, 0.2) AS y,
     min_max;

-- 2. Count intersections in each cell
DROP TABLE IF EXISTS grid_time_intersections;

CREATE TABLE grid_time_intersections AS
SELECT g.geom, g.time, COUNT(f.ECTRL) as intersection_count
FROM grid_time g
LEFT JOIN flights f
ON ST_Intersects(g.geom, f.Traj::geometry) AND f.TrajTime = g.time
GROUP BY g.geom, g.time;

-- 3. Clustering is done in Python

------------------------------------------------------------------
-- Take into account the FL --------------------------------------
------------------------------------------------------------------
-- Create 3D grid
DROP TABLE IF EXISTS grid3D;

CREATE TABLE grid3D AS 
SELECT ST_SetSRID(ST_3DMakeBox(
    ST_MakePoint(x, y, z),
    ST_MakePoint(x + 0.2, y + 0.2, z + 304.8) -- 304.8 meters is equivalent to 1000 feet (or one FL)
), 4326) as geom 
FROM generate_series(-10.1, 4.9, 0.2) AS x, 
     generate_series(35.9, 43.9, 0.2) AS y,
     generate_series(0, 12000, 304.8) AS z; -- Assuming max FL is 400 (i.e., 40,000 feet)
ALTER TABLE grid3D ADD COLUMN strrep text;
UPDATE grid3D SET strrep = ST_AsText(geom);

-- Count intersections in each 3D cell
DROP TABLE IF EXISTS grid3D_intersections;

CREATE TABLE grid3D_intersections AS 
SELECT 
    g.strrep, 
    COUNT(DISTINCT f1.ECTRL) as trajectories,
    COUNT(*) as intersection_count 
FROM grid3D g 
JOIN flights f1 ON ST_3DIntersects(g.geom, f1.Traj::geometry) 
JOIN flights f2 ON ST_3DIntersects(g.geom, f2.Traj::geometry) 
WHERE f1.ECTRL > f2.ECTRL AND ST_3DDistance(ProjectTrajectory(f1.Traj::geometry), ProjectTrajectory(f2.Traj::geometry)) < 10000
GROUP BY g.strrep;

-- Cluster in 3D
DROP TABLE IF EXISTS grid3D_clusters;

CREATE TABLE grid3D_clusters AS 
SELECT g.geom, ST_ClusterKMeans(g.geom, 5) over () as cluster_id 
FROM grid_intersections g;

SELECT cluster_id, COUNT(cluster_id) FROM grid3D_clusters GROUP BY cluster_id;