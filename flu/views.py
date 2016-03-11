from django.shortcuts import render
from django.shortcuts import HttpResponse
import numpy as np
import pickle
from make_map import make_map
import os

curr_path = os.path.dirname(os.path.realpath(__file__))

def ContainPoints(poly, points):
    import matplotlib.path as mplPath
    bbPath = mplPath.Path(np.array([[poly[0], poly[2]],
                     [poly[1], poly[2]],
                     [poly[1], poly[3]],
                     [poly[0], poly[3]]]))

    return bbPath.contains_points(points)    

def geo_bounds(origin, distance):
    ''' get lat,lng bounding box of 'distance' km around a geo point
        geo_box = geo_bounds(origin, distance)
    :param origin: [lat,lng] list
    :param distance: radius in km
    :return: geo_box: (min lat, max lat, min lng, max lng)
    '''
    import geopy
    from geopy.distance import vincenty
    north = vincenty(kilometers=distance).destination(geopy.Point(origin), 0)
    east = vincenty(kilometers=distance).destination(geopy.Point(origin), 90)
    south = vincenty(kilometers=distance).destination(geopy.Point(origin), 180)
    west = vincenty(kilometers=distance).destination(geopy.Point(origin), 270)

    # get bounding box: (min lat, max lat, min lng, max lng)
    geo_box = (south.latitude, north.latitude, west.longitude, east.longitude)

    return geo_box
                                                                                                                                                                                                                                                                                                                                                                                                                                                   

def about(request):
    return render(request, 'flu/about.html')


def index(request):

    filename = os.path.abspath(curr_path+"/updatetime")
    print filename
    with open(filename, "rb") as f:
        [n_clust, update] = pickle.load(f)
    return render(request, 'flu/flu.html', {"map_name" : 'flu/includes/usa.html',
                                             "location": "USA",
                                             "flu_outbreak": "in "+ str(n_clust) + " regions",
                                             "severity": "Click on the marks to see",
                                             "update_time": update
                                             })

def search(request):
    flu_distance = 10
    plot_distance = 50
    if request.method == "GET":
        zipcode = request.GET.get('textfield', None)

        print zipcode
        #return HttpResponse(location)
        from geopy.geocoders import Nominatim
        try:
            geolocator = Nominatim()
            print 'locating...'
            location = geolocator.geocode(zipcode)
            map_center = [location.latitude, location.longitude]
            print "map center is: %f, %f" % (location.latitude, location.longitude)  
            filename = os.path.abspath(curr_path+"/cached_data")
            print 'now loading pickle...'
            with open(filename, "rb") as f:
                [points, cluster_labels, n_clust, cluster_ranks, rank_labels, last_update] \
                    = pickle.load(f)
            poly = geo_bounds(map_center, flu_distance)
            containPoints = ContainPoints(poly, points)
            outbreak = "NOT DETECTED"
            severity = "None"
            
            for i in range(len(points)):
                if containPoints[i] == True:
                    outbreak = "YES"
                    if cluster_labels[i] == -1:
                        severity = "Sporadic"
                    else:
                        severity = "Click on the marks to see"
                        
                    break
                    
            print 'now making map...'
            poly = geo_bounds(map_center, plot_distance)
            containPoints = ContainPoints(poly, points)
            points_in_region = []
            labels_in_region = []
            for i in range(len(points)):
                if containPoints[i] == True:
                    
                    points_in_region.append(points[i])
                    labels_in_region.append(cluster_labels[i])
                    
            make_map(points_in_region, labels_in_region, n_clust, cluster_ranks, rank_labels, map_center, zipcode)
            return render(request, 'flu/flu.html', {"map_name" : 'flu/includes/'+zipcode+'.html',
                                                     "location": location.address,
                                                     "flu_outbreak": outbreak,
                                                     "severity": severity,
                                                     "update_time": last_update
                                                     })
        except:
            return HttpResponse('<b>Please enter a valid zipcode/city/address.Thanks!</b>')
