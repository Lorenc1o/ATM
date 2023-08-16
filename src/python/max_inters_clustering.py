import numpy as np

def custom_distance(A, B):
    euclidean_dist = np.sqrt((A[0] - B[0])**2 + (A[1] - B[1])**2)
    return euclidean_dist ** (1 + A[2] + B[2])

def cluster_distance(cluster1, cluster2):
    distances = [custom_distance(point1, point2) for point1 in cluster1 for point2 in cluster2]
    return sum(distances) / len(distances)

def fast_cluster_distance(cluster1, cluster2, distance_matrix):
    distances = [distance_matrix[point1][point2] for point1 in cluster1 for point2 in cluster2]
    return sum(distances) / len(distances)

def hierarchical_clustering(points, P):
    n = len(points)
    clusters = [[i] for i in range(n)]
    distance_matrix = np.zeros((n, n))

    # Compute initial pairwise distances
    for i in range(n):
        for j in range(n):
            if i != j:
                distance_matrix[i][j] = custom_distance(points[i], points[j])
            else:
                distance_matrix[i][j] = float('inf')

    copy_distance_matrix = np.copy(distance_matrix)
    while True and len(clusters) > 1:

        if len(clusters) % 100 == 0:
            print("--------------------")
            print("Number of clusters: ", len(clusters))
            print("--------------------")

        # Find the pair of clusters with the smallest distance
        i, j = np.unravel_index(distance_matrix.argmin(), distance_matrix.shape)
        if distance_matrix[i][j] == float('inf'):
            break

        # Merge the clusters
        merged_cluster = clusters[i] + clusters[j]
        if sum(points[k][2] for k in merged_cluster) <= P:
            # Add the merged cluster to the list of clusters
            clusters.append(merged_cluster)
            # Remove the old clusters from the list of clusters
            min_index = min(i, j)
            max_index = max(i, j)

            clusters = [clusters[k] for k in range(len(clusters)) if k != min_index and k != max_index]
            distance_matrix = np.delete(distance_matrix, max_index, 0)
            distance_matrix = np.delete(distance_matrix, min_index, 0)
            distance_matrix = np.delete(distance_matrix, max_index, 1)
            distance_matrix = np.delete(distance_matrix, min_index, 1)
            
            # Update the distance matrix
            n = len(clusters)
            distance_matrix = np.hstack((distance_matrix, np.zeros((n-1, 1))))
            new_row = np.zeros((1, n))
            for k in range(n):
                if k != n - 1:
                    #new_row[0][k] = cluster_distance(clusters[n - 1], clusters[k])
                    new_row[0][k] = fast_cluster_distance(clusters[n - 1], clusters[k], copy_distance_matrix)
                else:
                    new_row[0][k] = float('inf')
            distance_matrix = np.vstack((distance_matrix, new_row))
            new_col = np.zeros((n, 1))
            for k in range(n):
                if k != n - 1:
                    #new_col[k][0] = cluster_distance(clusters[k], clusters[n - 1])
                    new_col[k][0] = fast_cluster_distance(clusters[k], clusters[n - 1], copy_distance_matrix)
                else:
                    new_col[k][0] = float('inf')
            distance_matrix[:, n - 1] = new_col[:, 0]

            
        else:
            # Mark the pair as unmergeable
            distance_matrix[i][j] = float('inf')
            distance_matrix[j][i] = float('inf')

    return clusters

def labelling(points, P):
    clusters = hierarchical_clustering(points, P)
    labels = []
    for i in range(len(points)):
        for j in range(len(clusters)):
            if i in clusters[j]:
                labels.append(j)
                break
    return labels

def example():
    # Example usage
    points = [(1, 1, 0.1), (2, 2, 0.2), (10, 10, 0.1), (11, 11, 0.2), (20, 20, 0.1), (21, 21, 0.2)]
    P = 0.7
    clusters = hierarchical_clustering(points, P)
    print(clusters)

    labels = labelling(points, P)
    print(labels)

if __name__ == "__main__":
    example()