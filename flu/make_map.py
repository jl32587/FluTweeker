import time
import numpy as np
import pandas as pd
import MySQLdb
import os
import pickle
from datetime import datetime, timedelta

curr_path = os.path.dirname(os.path.realpath(__file__))

def cluster_geo(points, eps=0.05, min_samples=5,
                max_cluster_size=float('inf')):


    print 'Clustering %i points: ' % len(points)

    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler

    standardized = StandardScaler().fit_transform(points)
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(standardized)
    cluster_labels = db.labels_

    # Number of clusters in labels, ignoring noise if present.
    n_clust = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    print('Estimated number of clusters: %d' % n_clust)

    return cluster_labels, n_clust

def make_map(points, cluster_labels, n_clust, cluster_ranks, rank_labels, map_center = 'usa', zipcode = 'usa' ):

    import folium
    import seaborn as sns
    # From color brewer

    cols_hex = sns.color_palette("Reds_r", n_colors = n_clust)
    # generate color bar
    
    marker_col = cols_hex.as_hex()

    x = [p[0] for p in points]
    y = [p[1] for p in points]
    
    if map_center == 'usa':
        map_center = [sum(x) / len(points), sum(y) / len(points)]
        zoom_start = 4
        map_name = "usa.html"
        
    else:
        zoom_start = 12
        map_name = zipcode+".html"
    print map_name  
        
    map = folium.Map(location = map_center, zoom_start = zoom_start, width = '100%', height = 800, tiles='Stamen Toner')
    
    # markers
    for i in range(len(points)):
        label = cluster_labels[i]
        if label == -1:
            map.circle_marker([points[i][0], points[i][1]],
                              radius=8,
                              line_color='#bdbdbd',
                              fill_color='#bdbdbd',
                              popup = "Sporadic"
                              )        
        else:
            map.circle_marker([points[i][0], points[i][1]],
                               radius=200,
                               line_color=marker_col[cluster_ranks[label]-1],
                               fill_color=marker_col[cluster_ranks[label]-1],
                               popup = rank_labels[label]
                               )
  
    
    path = os.path.abspath(curr_path+'/templates/flu/includes/'+map_name)
    print path
    map.create_map(path = path)
   
    return cols_hex


def get_data_from_mysql():
   usa_box = [-125, -65, 25, 48]   # the range of usa
   recent_data = (datetime.now() - timedelta(weeks=4)).strftime("%Y-%m-%d")
   print recent_data
   db = MySQLdb.connect(host='localhost', user='root', passwd='root', db='test')
   curr = db.cursor() 
   
   sql_query = '''SELECT X,Y FROM twitter3 
                  WHERE X BETWEEN %s AND %s 
                  AND Y BETWEEN %s AND %s 
                  AND Date > %s''' % (usa_box[0], usa_box[1], usa_box[2], usa_box[3], recent_data)
   
   curr.execute(sql_query)
   rows = curr.fetchall()
   points = []
  
   for row in rows:
       points.append([row[1], row[0]])
   return points    


def rank_clusters(points, cluster_labels, n_clust):
    points_df = pd.DataFrame(points)
    incidents = [0] * n_clust 
    for i in set(cluster_labels):
        if i != -1:
            incident = points_df[cluster_labels == i].shape[0]
            incidents[i] += incident

    incidents = pd.DataFrame(incidents)
    cluster_ranks = incidents.rank(0, ascending=False)
    cluster_ranks = cluster_ranks.applymap(int)
    cluster_ranks = list(cluster_ranks.values.flatten())
    rank_labels = pd.cut(np.array(cluster_ranks), 3, labels=["Severe","Moderate","Mild"])                                                             
    return cluster_ranks, rank_labels                                                                                                                                                            
                                                                                                                                                                                                                                                
def main(t):
    '''Update usa map every t hour'''
    starttime=time.time()
    update_time = 3600 * t
    
    while True:   #update the map every 24 hours
        last_update = datetime.now()
        points = get_data_from_mysql()
        cluster_labels, n_clust = cluster_geo(points)
        cluster_ranks, rank_labels = rank_clusters(points, cluster_labels, n_clust)
        try:
            make_map(points, cluster_labels, n_clust, cluster_ranks, rank_labels) 
        except:
            print "something wrong with making map..."
            pass
        
        data = [points, cluster_labels, n_clust, cluster_ranks, rank_labels, last_update]
        filename = os.path.abspath(curr_path +"/cached_data")
        print filename
        with open(filename, "wb") as f:
            pickle.dump(data, f)
            
        updatetimefile = os.path.abspath(curr_path + "/updatetime")
        with open(updatetimefile, "wb") as f:
            pickle.dump([n_clust, last_update],f)
        print "now sleeping..."
        time.sleep(update_time - ((time.time() - starttime) % 60.0))

if __name__ == '__main__':
    main(1)