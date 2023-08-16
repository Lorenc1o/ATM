import max_inters_clustering as mic
import psycopg2
import geopandas as gpd
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans, AgglomerativeClustering
import numpy as np
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

'''
Here, we are going to analyze the clusters obtained from the previous step.
'''
# 1. Read the data
# Establish a connection to the PostgreSQL database
conn = psycopg2.connect(
    dbname="flights_test",
    user="atm",
    password="atm",
    host="localhost",
    port="5432"
)

clusters = gpd.read_postgis("SELECT * FROM grid_hourly_clusters_py", conn, geom_col='geom')

# For all the columns regarding the agglomerative clustering, we are going to get some metrics
# These columns are: cluster_agglomerative_{p} where p in {0.01, 0.1, 0.2, 0.5, 0.75, 1, 1.25, 2}
# 2. Get the metrics for the agglomerative clustering

p = [0.01, 0.1, 0.2, 0.5, 0.75, 1, 1.25, 2]

# The metric is:
# - The max of the std of the sum of 'intersection_count' per cluster
# - The avg of the std of the sum of 'intersection_count' per cluster
# - The min of the std of the sum of 'intersection_count' per cluster

metrics = np.zeros((len(p), 3))

for i in p:
    column = 'cluster_agglomerative_' + str(i)
    '''
    The equivalent SQL query is:

    WITH TMP AS (
        SELECT start_time, SUM(intersection_count)/10 as aveg
        FROM grid_hourly_clusters_py
        GROUP BY start_time
    ),
    TMP2 AS (
        SELECT start_time, "cluster_agglomerative_{p}" as cluster_id, SUM(intersection_count) as n_inters
        FROM grid_hourly_clusters_py
        GROUP BY start_time, "cluster_agglomerative_{p}"
    )
    SELECT g.start_time, 
        SQRT(SUM((t2.n_inters - t1.aveg)^2)/10) as std
    FROM grid_hourly_clusters_py as g, TMP as t1, TMP2 as t2
    WHERE g.start_time = t1.start_time AND g.start_time = t2.start_time AND g."cluster_agglomerative_{p}" = t2.cluster_id
    GROUP BY g.start_time, t1.aveg
    ORDER BY g.start_time;
    '''

    query = "WITH TMP AS (SELECT start_time, SUM(intersection_count)/10 as aveg FROM grid_hourly_clusters_py GROUP BY start_time), TMP2 AS (SELECT start_time, \"" + column + "\" as cluster_id, SUM(intersection_count) as n_inters FROM grid_hourly_clusters_py GROUP BY start_time, \"" + column + "\") SELECT g.start_time, SQRT(SUM((t2.n_inters - t1.aveg)^2)/10) as std FROM grid_hourly_clusters_py as g, TMP as t1, TMP2 as t2 WHERE g.start_time = t1.start_time AND g.start_time = t2.start_time AND g.\"" + column + "\" = t2.cluster_id GROUP BY g.start_time, t1.aveg ORDER BY g.start_time;"

    # Get the data
    cur = conn.cursor()
    cur.execute(query)
    data = cur.fetchall()
    cur.close()

    # Get the metrics
    metrics[p.index(i), 0] = np.max(np.array(data)[:, 1])
    metrics[p.index(i), 1] = np.mean(np.array(data)[:, 1])
    metrics[p.index(i), 2] = np.min(np.array(data)[:, 1])
    
print("Agglomerative clustering metrics obtained")
print("The results are:")
print(metrics)

# Plot the results
plt.plot(p, metrics[:, 0], label='Max')
plt.plot(p, metrics[:, 1], label='Mean')
plt.plot(p, metrics[:, 2], label='Min')
plt.xlabel('p')
plt.ylabel('std')
plt.title('Agglomerative clustering metrics')
plt.legend()
plt.savefig('agglomerative_clustering_metrics.png')

# Same in log scale
plt.clf()
plt.plot(p, metrics[:, 0], label='Max')
plt.plot(p, metrics[:, 1], label='Mean')
plt.plot(p, metrics[:, 2], label='Min')
plt.xlabel('p')
plt.ylabel('std')
plt.title('Agglomerative clustering metrics')
plt.legend()
plt.yscale('log')
plt.savefig('agglomerative_clustering_metrics_log.png')
