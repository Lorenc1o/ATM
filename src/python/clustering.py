import psycopg2
import geopandas as gpd
from scipy.spatial.distance import cdist, pdist
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
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

# Load the grid data from the database
grid = gpd.read_postgis("SELECT * FROM grid_intersections", conn)

# Reproject to UTM Zone 30N
grid2 = grid.to_crs(utm_crs)

# Calculate the number of intersections per unit area
grid2["intersections_per_area"] = grid["intersection_count"]

# Prepare the data for clustering
X = np.column_stack([
    grid2.geometry.centroid.x,
    grid2.geometry.centroid.y,
    1+grid2["intersections_per_area"]/grid2["intersections_per_area"].max()
])

# 1. Get the min and max values
min_x, min_y = X[:, 0].min(), X[:, 1].min()
max_x, max_y = X[:, 0].max(), X[:, 1].max()

# 2. Compute the ranges
range_x = max_x - min_x
range_y = max_y - min_y

# 3. Determine the larger range
max_range = max(range_x, range_y)

# 4. Scale x and y
X[:, 0] = (X[:, 0] - min_x) / max_range
X[:, 1] = (X[:, 1] - min_y) / max_range

# Perform clustering with KMeans
n_clusters = 5
clustering = KMeans(n_clusters=10).fit(X)
grid["cluster_id_kmeans"] = clustering.labels_

# Perform clustering with DBSCAN
epss = [0.01, 0.02, 0.03, 0.04, 0.05]
min_samples = [3, 4, 5, 6, 7, 8, 9, 10]
for eps in epss:
    for min_sample in min_samples:
        clustering = DBSCAN(eps=eps, min_samples=min_sample).fit(X)
        grid[f"cluster_id_dbscan_{eps}_{min_sample}"] = clustering.labels_

# Perform clustering with AgglomerativeClustering
def custom_distance(X):
    # Extract the spatial and non-spatial features
    spatial_features = X[:, :2]
    non_spatial_features = X[:, 2]

    # Compute the Euclidean distances between all pairs of spatial features
    euclidean_distances = cdist(spatial_features, spatial_features)
    
    # Normalize the distances
    #euclidean_distances = euclidean_distances/euclidean_distances.max()

    # Divide the distances by the minimum sector size
    euclidean_distances = euclidean_distances/min_sector_size

    # Compute the final distance matrix
    # If the distance between two sectors is 0, the distance between them is 0
    # Otherwise, raise the distance to the power of the sum of the non-spatial features
    distances = np.where(
        euclidean_distances == 0,
        0,
        euclidean_distances ** (non_spatial_features[:, None] + non_spatial_features)
    )

    return distances

# Perform clustering with AgglomerativeClustering using average linkage
clustering = AgglomerativeClustering(
    n_clusters=10, 
    metric=custom_distance, 
    linkage='average',
    compute_full_tree=True
).fit(X)

# Assign the cluster labels back to the grid dataframe
grid["cluster_id_agg_avg"] = clustering.labels_

# Perform clustering with AgglomerativeClustering using complete linkage
clustering = AgglomerativeClustering(
    n_clusters=10,
    metric=custom_distance,
    linkage='complete',
    compute_full_tree=True
).fit(X)

# Assign the cluster labels back to the grid dataframe
grid["cluster_id_agg_complete"] = clustering.labels_

# Perform clustering with AgglomerativeClustering using single linkage
clustering = AgglomerativeClustering(
    n_clusters=10,
    metric=custom_distance,
    linkage='single',
    compute_full_tree=True
).fit(X)

# Assign the cluster labels back to the grid dataframe
grid["cluster_id_agg_single"] = clustering.labels_

# Let's test what happens when changing the min_sector_size
# We do it with the avg agglomerative clustering, which has given the best results so far
for min_sector_size in [0.07,0.08,0.09,0.1,0.11,0.12,0.15,0.2,0.25,0.4,0.5,1]:
    # Perform clustering with AgglomerativeClustering using average linkage
    clustering = AgglomerativeClustering(
        n_clusters=10, 
        metric=custom_distance, 
        linkage='average',
        compute_full_tree=True
    ).fit(X)

    # Assign the cluster labels back to the grid dataframe
    key = f'cluster_id_agg_avg_{min_sector_size}'
    grid[key] = clustering.labels_


# Create an SQLAlchemy engine
engine = create_engine("postgresql://atm:atm@localhost:5432/flights_test")

# Write the grid dataframe back to the database as a new table
grid.to_postgis("grid_clusters_py", engine, if_exists="replace")