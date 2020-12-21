import sys
import pathlib
import zipfile
import json
import csv
import datetime
import haversine

# Returns a list of the start and end points of a placeVisit. The location stays
# the same, but we have two timestamps.
def placeVisit(placeVisit_dict):
    # Sometimes the latitude and longitude are just missing. In that case, just
    # return an empty list.
    place_id = placeVisit_dict["location"]["placeId"]
    try:
        lat = int(placeVisit_dict["location"]["latitudeE7"])/1e7
        lon = int(placeVisit_dict["location"]["longitudeE7"])/1e7
    except:
        lat = False
        lon = False
    if "name" in placeVisit_dict["location"]:
        name = placeVisit_dict["location"]["name"]
    elif "address" in placeVisit_dict["location"]:
        name = placeVisit_dict["location"]["address"].replace("\n",", ")
    else:
        name = "PLACE"
    orig_start_timestamp = int(placeVisit_dict["duration"]["startTimestampMs"])
    start_timestamp = timeStampToDate(orig_start_timestamp)
    orig_end_timestamp = int(placeVisit_dict["duration"]["endTimestampMs"])
    end_timestamp = timeStampToDate(orig_end_timestamp)    
    confidence = placeVisit_dict["visitConfidence"]
    time_convention = timeStampToAMPM(orig_start_timestamp)
    if (lat and lon):
        place_start = [place_id, 0, lat, lon, orig_start_timestamp, start_timestamp, 0, name, confidence, time_convention]
        place_end = [place_id, 1, lat, lon, orig_end_timestamp, end_timestamp, 0, name, confidence, time_convention]
        place_points = [place_start, place_end]
    else:
        place_points = []
    return place_points

# Returns a list of the start and end points of an activitySegment, and
# optionally the waypoints in-between.
def activitySegment(activitySegment_dict, includeWaypoints=True):
    # Some older JSONs have empty startLocation and/or endLocation in
    # the activitySegment object
    try:
        start_point = activityStartPoint(activitySegment_dict)
    except:
        start_point = False
    try:
        end_point = activityEndPoint(activitySegment_dict)
    except:
        end_point = False

    # Sometimes the activitySegment object will have waypoints even 
    # with an empty startLocation, but I'm choosing to ignore those
    if (start_point and includeWaypoints):
        activity_points = activityRawPoints(activitySegment_dict, start_point)
        activity_points.insert(0, start_point)
        end_point.insert(1, (len(activity_points)) + 1)
        activity_points.append(end_point)
    else:
        if (start_point and end_point):
            # Use 2 as the 'order' field for the end point, since we're omitting waypoints
            end_point.insert(1, 2)
            activity_points = [start_point, end_point]
        else:
            activity_points = []
    return activity_points

# Set start point of activity as a list.
def activityStartPoint(activitySegment_dict):
    trip_id = activitySegment_dict["duration"]["startTimestampMs"]
    order = 1
    lat = int(activitySegment_dict["startLocation"]["latitudeE7"])/1e7
    lon = int(activitySegment_dict["startLocation"]["longitudeE7"])/1e7
    orig_timestamp = int(trip_id)
    timestamp = timeStampToDate(orig_timestamp)
    distance = activitySegment_dict.get("distance", 0)
    if "activityType" in activitySegment_dict:
        ac_type = activitySegment_dict["activityType"]
    else:
        ac_type = "UNKNOWN"
    if "confidence" in activitySegment_dict:
        confidence = activitySegment_dict["confidence"]
    else:
        confidence = "N/A"
    time_convention = timeStampToAMPM(orig_timestamp)
    start_point = [trip_id, order, lat, lon, orig_timestamp, timestamp, distance, ac_type, confidence, time_convention]
    return start_point

# Set end point of activity as a list.
def activityEndPoint(activitySegment_dict):
    trip_id = activitySegment_dict["duration"]["startTimestampMs"]
    lat = int(activitySegment_dict["endLocation"]["latitudeE7"])/1e7
    lon = int(activitySegment_dict["endLocation"]["longitudeE7"])/1e7
    orig_timestamp = int(activitySegment_dict["duration"]["endTimestampMs"])
    timestamp = timeStampToDate(orig_timestamp)
    distance = activitySegment_dict.get("distance", 0)
    if "activityType" in activitySegment_dict:
        ac_type = activitySegment_dict["activityType"]
    else:
        ac_type = "UNKNOWN"
    if "confidence" in activitySegment_dict:
        confidence = activitySegment_dict["confidence"]
    else:
        confidence = "N/A"
    time_convention = timeStampToAMPM(orig_timestamp)        
    end_point = [trip_id, lat, lon, orig_timestamp, timestamp, distance, ac_type, confidence, time_convention]
    return end_point

# Creates a list of list with each waypoint of activity.
def activityRawPoints(activitySegment_dict, start_point):
    points = []
    order = 1

    # There are no timestamps on waypointPath objects
    if "waypointPath" in activitySegment_dict.keys():
        way_points = activitySegment_dict["waypointPath"]["waypoints"]
        for point in way_points:
            trip_id = start_point[0]
            order += 1
            lat = int(point["latE7"])/1e7
            lon = int(point["lngE7"])/1e7
            orig_timestamp = start_point[4]            
            timestamp = start_point[5]
            distance = start_point[6]
            ac_type = start_point[7]
            confidence = start_point[8]
            time_convention = start_point[9]
            list_point = [trip_id, order, lat, lon, orig_timestamp, timestamp, distance, ac_type, confidence, time_convention]
            points.append(list_point)
    # However, simplifiedRawPath waypoints do have timestamps
    elif "simplifiedRawPath" in activitySegment_dict.keys():
        raw_points = activitySegment_dict["simplifiedRawPath"]["points"]
        for point in raw_points:
            trip_id = start_point[0]
            order += 1
            lat = int(point["latE7"])/1e7
            lon = int(point["lngE7"])/1e7
            orig_timestamp = int(point["timestampMs"])
            timestamp = timeStampToDate(orig_timestamp)
            distance = start_point[6]
            ac_type = start_point[7]
            confidence = start_point[8]
            time_convention = timeStampToAMPM(orig_timestamp)
            list_point = [trip_id, order, lat, lon, orig_timestamp, timestamp, distance, ac_type, confidence, time_convention]
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
def extractData(data, points_list):
    for data_unit in data["timelineObjects"]:
        if "activitySegment" in data_unit.keys():
            for point in activitySegment(data_unit["activitySegment"], True):
                points_list.append(point)
        elif "placeVisit" in data_unit.keys():
            for point in placeVisit(data_unit["placeVisit"]):
                points_list.append(point)                

# Extract activity points and place visits to CSV. Not currently used.
def extractData_csv(data):
    for data_unit in data["timelineObjects"]:
        if "activitySegment" in data_unit.keys():
            writeActivityPoints_csv(activitySegment(data_unit["activitySegment"], True))
        elif "placeVisit" in data_unit.keys():
            writePlaces_csv(placeVisit(data_unit["placeVisit"]))
        else:
          print("Error")

# CSV writers. These append to existing files. Not currently used.
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
#    5: orig_timestamp (ms)
#    6: timestamp (human readable)
#    7: distance
#    8: ac_type
#    9: confidence
#   10: time_convention
def parseActivityFromZip(zip_fn, user_id=""):
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
                    extractData(data, activity)
    for act in activity:
        act.insert(0, user_id)
    return activity

def simplifyDataPoint(point):
    return [point[0], point[6], point[3], point[4], point[8]]
    
def showDelta(pointA, pointB, time_threshold_mins, dist_threshold_km):
    time_delta = abs(pointB[5] - pointA[5])
    dist_delta = haversine.haversine((pointA[3], pointA[4]),
                                     (pointB[3], pointB[4]))
    time_threshold_ms = time_threshold_mins * 60 * 1000
    if time_delta <= time_threshold_ms and dist_delta <= dist_threshold_km:
        print("Possible overlap!")
        print(simplifyDataPoint(pointA))
        print(simplifyDataPoint(pointB))
        time_delta_secs = int(time_delta/1000) % 60
        time_delta_mins = int(time_delta/1000/60) % 60
        print("Time delta: " + str(time_delta_mins) + " mins " + str(time_delta_secs) + " secs")
        print("Dist delta: " + str(round(dist_delta, 4)) + " km")
        # The "data" parameters for walking instructions is documented here:
        # https://support.google.com/maps/forum/AAAAQuUrST84CiQTcarJHk/?hl=en&msgid=freuulMVFH0J&gpf=d/msg/maps/4CiQTcarJHk/freuulMVFH0J
        print(f"https://www.google.com/maps/dir/{pointA[3]},+{pointA[4]}/{pointB[3]},+{pointB[4]}/data=!4m2!4m1!3e2")
        print()

if len(sys.argv)-1 == 1:
    fn = sys.argv[1]
    name = pathlib.Path(fn).stem
    activity = parseActivityFromZip(fn, name)
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
    user1_activity = parseActivityFromZip(user1_fn, user1_name)
    user2_activity = parseActivityFromZip(user2_fn, user2_name)
    activity = user1_activity + user2_activity
    activity.sort(key=lambda x: x[5], reverse=False)

    # Naive algorithm: save the data point for when each user was last seen.
    # Iterate over all points comparing current point to the "last seen"
    # point from the previous user. If the distance delta and time delta
    # criteria are met, flag it as a potential overlap.

    lastseen_user1 = []
    lastseen_user2 = []

    # Change delta thresholds here, if you want
    time_threshold_mins = 120
    dist_threshold_km = 1
    
    for act in activity:
#        print(act)
        if act[0] == user1_name:
            if len(lastseen_user2) > 0:
                showDelta(act, lastseen_user2, time_threshold_mins, dist_threshold_km)
            lastseen_user1 = act
        elif act[0] == user2_name:
            if len(lastseen_user1) > 0:
                showDelta(lastseen_user1, act, time_threshold_mins, dist_threshold_km)
            lastseen_user2 = act
        else:
            print("Error: Can't figure out which user this data point is for")
else:
    print("USAGE")
    print(f"  Dump single file  :\t{sys.argv[0]} [zipfile]")
    print(f"  Look for overlaps :\t{sys.argv[0]} [zipfile1] [zipfile2]\n")
    print()
    
        
