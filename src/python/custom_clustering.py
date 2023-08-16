import max_inters_clustering as mic
import psycopg2
import geopandas as gpd
import numpy as np
from sqlalchemy import create_engine
import pyproj

# Define a function to convert lon/lat to UTM coordinates
def lonlat_to_utm(lon, lat):
    utm_proj = pyproj.Proj(proj='utm', zone=30, ellps='WGS84', south=False)  # Adjust the zone number as needed
    return utm_proj(lon, lat)

# Define the UTM Zone 30N projection
# EPSG:32630 is the EPSG code for UTM Zone 30N, WGS84
utm_crs = "EPSG:32630"

min_sector_size = 0.1

# Establish a connection to the PostgreSQL database
conn = psycopg2.connect(
    dbname="flights_test",
    user="atm",
    password="atm",
    host="localhost",
    port="5432"
)

'''
Now, we are doing the same but with hourly data
'''
grid = gpd.read_postgis("SELECT * FROM grid_hourly_intersections", conn)

# Order the grid by start_time and id
grid = grid.sort_values(by=['start_time', 'id'])

# Reproject to UTM Zone 30N
grid2 = grid.to_crs(utm_crs)

# Calculate the number of intersections per unit area
grid2['id'] = grid['id']
grid2["intersections_per_area"] = grid["intersection_count"]
grid2["start_time"] = grid["start_time"]
grid2["end_time"] = grid["end_time"]

# Prepare the data for clustering
# We are going to cluster each hour separately
# We are going to use the same clustering parameters for all hours
X = np.column_stack([
    grid2.id,
    grid2.start_time.dt.hour,
    grid2.geometry.centroid.x,
    grid2.geometry.centroid.y,
    grid2["intersections_per_area"]/grid2["intersections_per_area"].max()
])

# 1. Get the min and max values
min_x, min_y = X[:, 2].min(), X[:, 3].min()
max_x, max_y = X[:, 2].max(), X[:, 3].max()

# 2. Compute the ranges
range_x = max_x - min_x
range_y = max_y - min_y

# 3. Determine the larger range
max_range = max(range_x, range_y)

# 4. Scale x and y
X[:, 2] = (X[:, 2] - min_x) / max_range
X[:, 3] = (X[:, 3] - min_y) / max_range

# Add to grid the columns for the clusters
grid['cluster_kmeans'] = None
grid['cluster_agglomerative'] = None


for hour in np.unique(X[:,1]):  # Ensure we loop through unique hours only
    
    Y = X[X[:,1]==hour][:,2:]

    print("------------------")
    print(Y.shape)

    labels = mic.labelling(Y, 0.5)

    # Add the labels to the grid
    grid.loc[grid.start_time.dt.hour==hour, 'cluster_custom'] = labels

    print(f'Finished clustering hour {hour}')

# Create an SQLAlchemy engine
engine = create_engine("postgresql://atm:atm@localhost:5432/flights_test")

# Write the grid dataframe back to the database as a new table
grid.to_postgis("grid_hourly_clusters_py", engine, if_exists="replace")