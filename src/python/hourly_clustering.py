import psycopg2
import geopandas as gpd
from scipy.spatial.distance import cdist, pdist
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
import numpy as np
from sqlalchemy import create_engine
import pyproj
import pandas as pd

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

# Reproject to UTM Zone 30N
grid2 = grid.to_crs(utm_crs)

# Calculate the number of intersections per unit area
grid2["intersections_per_area"] = grid["intersection_count"]
grid2["hour"] = grid["start_time"].dt.hour

# Prepare the data for clustering
# We are going to cluster each hour separately
# We are going to use the same clustering parameters for all hours
X = np.column_stack([
    grid2.hour,
    grid2.geometry.centroid.x,
    grid2.geometry.centroid.y,
    1+grid2["intersections_per_area"]/grid2["intersections_per_area"].max()
])

# 1. Get the min and max values
min_x, min_y = X[:, 1].min(), X[:, 2].min()
max_x, max_y = X[:, 1].max(), X[:, 2].max()

# 2. Compute the ranges
range_x = max_x - min_x
range_y = max_y - min_y

# 3. Determine the larger range
max_range = max(range_x, range_y)

# 4. Scale x and y
X[:, 1] = (X[:, 1] - min_x) / max_range
X[:, 2] = (X[:, 2] - min_y) / max_range

inverse_scale_x = lambda x: x * max_range + min_x
inverse_scale_y = lambda y: y * max_range + min_y

def is_approximately_equal(x1, x2, tolerance=1e-5):
    return abs(x1 - x2) < tolerance

for hour in np.unique(X[:,0]):  # Ensure we loop through unique hours only
    
    Y = X[X[:,0]==hour][:,1:]
    
    clustering = KMeans(n_clusters=10).fit(Y)

    # Convert Y back to its original scale
    Y[:, 0] = inverse_scale_x(Y[:, 0])
    Y[:, 1] = inverse_scale_y(Y[:, 1])
    
    labels = []
    for idx, row in grid.iterrows():
        centroid_x = row['geom'].centroid.x
        centroid_y = row['geom'].centroid.y
        current_hour = row['start_time'].hour  


        if current_hour != hour:
            continue

        # Find the nearest centroid in Y
        distances = cdist([(centroid_x, centroid_y)], Y[:, :2])
        nearest_index = np.argmin(distances)
        labels.append(clustering.labels_[nearest_index])
    
    grid[f'cluster_kmeans_{hour}'] = labels

    print(f'Finished clustering hour {hour}')
    print(f'Number of clusters: {len(np.unique(labels))}')

    break


# Create an SQLAlchemy engine
engine = create_engine("postgresql://atm:atm@localhost:5432/flights_test")

# Write the grid dataframe back to the database as a new table
grid.to_postgis("grid_hourly_clusters_py", engine, if_exists="replace")