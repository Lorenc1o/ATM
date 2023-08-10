-- Create input table from data
DROP TABLE IF EXISTS flightsINPUT;

CREATE TABLE flightsINPUT(
	ECTRL integer,
	seq integer,
	timeover timestamp,
	FL integer,
	lat float,
	long float,
	Geom geometry(Point, 4326)
);

COPY flightsINPUT(ECTRL, seq, timeover, FL, lat, long) 
FROM '/home/jose/Desktop/MyFolder/22-23/ULB_Internship/research/data/eurocontrol/data_01-06-2015.csv' DELIMITER ',' CSV HEADER;

UPDATE flightsINPUT SET
	Geom = ST_SetSRID(ST_MakePoint(long, lat), 4326);

-- Remove duplicates
WITH numbered_rows AS (
  SELECT ECTRL, timeover, ROW_NUMBER() OVER(PARTITION BY ECTRL, timeover ORDER BY ECTRL) AS rn
  FROM flightsINPUT
)
DELETE FROM flightsINPUT
WHERE (ECTRL, timeover) IN (
  SELECT ECTRL, timeover
  FROM numbered_rows
  WHERE rn > 1
);


-- Create flights table
-- TODO: what to do with the FL?
DROP TABLE IF EXISTS flights;

CREATE TABLE flights(ECTRL, Trip) AS
SELECT ECTRL,
	tgeompoint_seqset_gaps(
		array_agg(
			tgeompoint_inst(Geom, timeover) ORDER BY timeover
		)
	)
FROM flightsINPUT
WHERE Geom IS NOT NULL AND timeover IS NOT NULL
GROUP BY ECTRL;

ALTER TABLE flights ADD COLUMN Traj geometry;
UPDATE flights SET Traj = trajectory(Trip);

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

GRANT ALL PRIVILEGES ON SCHEMA public TO atm;

