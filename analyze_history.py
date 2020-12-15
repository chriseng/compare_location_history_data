import sys
import pathlib
import zipfile
import json
import csv
import datetime
import haversine

# Creates a list from placeVisit data. Not used but saving in case we need it later.
def placeVisit(placeVisit_dict):
    place_id = placeVisit_dict["location"]["placeId"]
    lat = placeVisit_dict["location"]["latitudeE7"]
    lon = placeVisit_dict["location"]["longitudeE7"]
    address = placeVisit_dict["location"]["address"].replace("\n",", ")
    start_time = placeVisit_dict["duration"]["startTimestampMs"]
    end_time = placeVisit_dict["duration"]["endTimestampMs"]
    confidence = placeVisit_dict["visitConfidence"]
    # Formatting variables
    lat = int(lat)/1e7
    lon = int(lon)/1e7
    start_time = timeStampToDate(int(start_time))
    end_time = timeStampToDate(int(end_time))
    place_visit = [place_id, lat, lon, address, start_time, end_time, confidence]
    return place_visit

# Returns a list of the start and end points of an activity, and optionally the
# waypoints in-between.
def activitySegment(activitySegment_dict, includeWaypoints=True):
    start_point = activityStartPoint(activitySegment_dict)
    end_point = activityEndPoint(activitySegment_dict)
    if (includeWaypoints):
        activity_points = activityRawPoints(activitySegment_dict, start_point)
        activity_points.insert(0, start_point)
        end_point.insert(1, (len(activity_points)) + 1)
        activity_points.append(end_point)
    else:
        # use 2 as the 'order' field for the end point, since we're omitting waypoints
        end_point.insert(1, 2)
        activity_points = [start_point, end_point]
    return activity_points

# Set start point of activity as a list.
def activityStartPoint(activitySegment_dict):
    trip_id = activitySegment_dict["duration"]["startTimestampMs"]
    order = 1
    lat = int(activitySegment_dict["startLocation"]["latitudeE7"])/1e7
    lon = int(activitySegment_dict["startLocation"]["longitudeE7"])/1e7
    orig_time_stamp = int(trip_id)
    time_stamp = timeStampToDate(orig_time_stamp)
    distance = activitySegment_dict.get("distance", 0)
    if "activityType" in activitySegment_dict:
        ac_type = activitySegment_dict["activityType"]
    else:
        ac_type = "UNKNOWN"
    if "confidence" in activitySegment_dict:
        confidence = activitySegment_dict["confidence"]
    else:
        confidence = "N/A"
    time_convention = timeStampToAMPM(int(trip_id))
    start_point = [trip_id, order, lat, lon, orig_time_stamp, time_stamp, distance, ac_type, confidence, time_convention]
    return start_point

# Set end point of activity as a list.
def activityEndPoint(activitySegment_dict):
    trip_id = activitySegment_dict["duration"]["startTimestampMs"]
    lat = int(activitySegment_dict["endLocation"]["latitudeE7"])/1e7
    lon = int(activitySegment_dict["endLocation"]["longitudeE7"])/1e7
    orig_time_stamp = int(activitySegment_dict["duration"]["endTimestampMs"])
    time_stamp = timeStampToDate(orig_time_stamp)
    distance = activitySegment_dict.get("distance", 0)
    if "activityType" in activitySegment_dict:
        ac_type = activitySegment_dict["activityType"]
    else:
        ac_type = "UNKNOWN"
    if "confidence" in activitySegment_dict:
        confidence = activitySegment_dict["confidence"]
    else:
        confidence = "N/A"
    time_convention = timeStampToAMPM(int(trip_id))
    end_point = [trip_id, lat, lon, orig_time_stamp, time_stamp, distance, ac_type, confidence, time_convention]
    return end_point

# Creates a list of list with each waypoint of activity.
def activityRawPoints(activitySegment_dict, start_point):
    points = []
    order = 1
    if "waypointPath" in activitySegment_dict.keys():
        way_points = activitySegment_dict["waypointPath"]["waypoints"]
        for point in way_points:
            trip_id = start_point[0]
            order += 1
            lat = int(point["latE7"])/1e7
            lon = int(point["lngE7"])/1e7
            orig_time_stamp = start_point[4]            
            time_stamp = start_point[5]
            distance = start_point[6]
            ac_type = start_point[7]
            confidence = start_point[8]
            time_convention = timeStampToAMPM(int(trip_id))
            list_point = [trip_id, order, lat, lon, orig_time_stamp, time_stamp, distance, ac_type, confidence, time_convention]
            points.append(list_point)
    elif "simplifiedRawPath" in activitySegment_dict.keys():
        raw_points = activitySegment_dict["simplifiedRawPath"]["points"]
        for point in raw_points:
            trip_id = start_point[0]
            order += 1
            lat = int(point["latE7"])/1e7
            lon = int(point["lngE7"])/1e7
            orig_time_stamp = int(point["timestampMs"])
            time_stamp = timeStampToDate(int(point["timestampMs"]))
            distance = start_point[5]
            ac_type = start_point[6]
            confidence = start_point[7]
            time_convention = timeStampToAMPM(int(trip_id))
            list_point = [trip_id, order, lat, lon, orig_time_stamp, time_stamp, distance, ac_type, confidence, time_convention]
            points.append(list_point)
    return points

# Convert milliseconds timestamp into a readable date.
def timeStampToDate(milliseconds):
    date = datetime.datetime.fromtimestamp(milliseconds/1000.0)
    date = date.strftime('%Y-%m-%d %H:%M:%S')
    return date

# Check time convention.
def timeStampToAMPM(milliseconds):
    date = datetime.datetime.fromtimestamp(milliseconds/1000.0)
    if date.hour < 12:
        time_convention = "AM"
    else:
        time_convention = "PM"
    return time_convention

# Extract activity points to a list.
def extractActivities(data, activity_list):
    for data_unit in data["timelineObjects"]:
        if "activitySegment" in data_unit.keys():
            for point in activitySegment(data_unit["activitySegment"], False):
                activity_list.append(point)

# Extract activity points and place visits to CSV.
def extractData_csv(data):
    for data_unit in data["timelineObjects"]:
        if "activitySegment" in data_unit.keys():
            writeActivityPoints_csv(activitySegment(data_unit["activitySegment"], True))
        elif "placeVisit" in data_unit.keys():
            writePlaces_csv(placeVisit(data_unit["placeVisit"]))
        else:
          print("Error")

# CSV writers. These append to existing files.
def writePlaces_csv(place_data_list):
    with open('FULL_places.csv', 'a', newline='') as file:
      writer = csv.writer(file, delimiter=',')
      writer.writerow(place_data_list)

def writeActivityPoints_csv(point_data_list):
  with open('FULL_activity_points.csv', 'a', newline='') as file:
      writer = csv.writer(file, delimiter=',')
      writer.writerows(point_data_list)

# Parse zip file and return array of location data. Fields:
#    0: user_id
#    1: trip_id
#    2: path order
#    3: latitude
#    4: longitude
#    5: orig_time_stamp (ms)
#    6: time_stamp (human readable)
#    7: distance
#    8: ac_type
#    9: confidence
#   10: time_convention
def parseActivitiesFromZip(zip_fn, user_id=""):
    activity=[]
    with zipfile.ZipFile(zip_fn, 'r') as zip_obj:
        for zip_info in zip_obj.infolist():
            fn = zip_info.filename
            if "Semantic" in fn and fn.endswith('.json'):
#                print(fn)                            
#                zip_info.filename = os.path.basename(zip_info.filename)
#                zip_obj.extract(zip_info, 'temp1')
                with zip_obj.open(fn) as f:
                    data = json.load(f)
                    extractActivities(data, activity)
    for act in activity:
        act.insert(0, user_id)
    return activity

def simplifyDataPoint(point):
    return [point[0], point[6], point[3], point[4]]
    
# Default thresholds are 30 minutes and 0.5 km
def showDelta(pointA, pointB, time_threshold_ms=900000, dist_threshold_km=0.5):
    time_delta = pointB[5] - pointA[5]
    dist_delta = haversine.haversine((pointA[3], pointA[4]),
                                     (pointB[3], pointB[4]))
    if time_delta <= time_threshold_ms and dist_delta <= dist_threshold_km:
        print("Possible overlap!")
        print(simplifyDataPoint(pointA))
        print(simplifyDataPoint(pointB))
        time_delta_secs = int(time_delta/1000) % 60
        time_delta_mins = int(time_delta/1000/60) % 60
#        print("Time delta: " + str(time_delta/1000/60) + " mins")
        print("Time delta: " + str(time_delta_mins) + " mins " + str(time_delta_secs) + " secs")
        print("Dist delta: " + str(round(dist_delta, 4)) + " km")
        print(f"https://www.google.com/maps/dir/{pointA[3]},+{pointA[4]}/{pointB[3]},+{pointB[4]}")
        print()

if len(sys.argv)-1 == 1:
    fn = sys.argv[1]
    name = pathlib.Path(fn).stem
    activity = parseActivitiesFromZip(fn, name)
    activity.sort(key=lambda x: x[5], reverse=False)
    for act in activity:
        print(act)
elif len(sys.argv)-1 == 2:
    # Combine activity lists into a single list sorted by timestamp. First
    # field indicates which user the data point came from.

    user1_fn = sys.argv[1]
    user2_fn = sys.argv[2]
    user1_name = pathlib.Path(user1_fn).stem
    user2_name = pathlib.Path(user2_fn).stem
    user1_activity = parseActivitiesFromZip(user1_fn, user1_name)
    user2_activity = parseActivitiesFromZip(user2_fn, user2_name)
    activity = user1_activity + user2_activity
    activity.sort(key=lambda x: x[5], reverse=False)

    # Naive algorithm: save the data point for when each user was last seen.
    # Iterate over all points comparing current point to the "last seen"
    # point from the previous user. If the distance delta and time delta
    # criteria are met, flag it as a potential overlap.

    lastseen_user1 = []
    lastseen_user2 = []
    time_threshold_ms = 120 * 60 * 1000;
    dist_threshold_km = 1;
    for act in activity:
#        print(act)
        if act[0] == user1_name:
            if len(lastseen_user2) > 0:
                showDelta(lastseen_user2, act, time_threshold_ms, dist_threshold_km)
            lastseen_user1 = act
        elif act[0] == user2_name:
            if len(lastseen_user1) > 0:
                showDelta(lastseen_user1, act, time_threshold_ms, dist_threshold_km)
            lastseen_user2 = act
        else:
            print("Error: Can't figure out which user this data point is for")
else:
    print("USAGE")
    print(f"  Dump single file  :\t{sys.argv[0]} [zipfile]")
    print(f"  Look for overlaps :\t{sys.argv[0]} [zipfile1] [zipfile2]\n")
    print()
    
        
