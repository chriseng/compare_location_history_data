# compare_location_history_data

This project attempts to determine whether two Google Timeline location history data sets overlap temporally and geographically, i.e. were these two people ever nearby each other at roughly the same time.

## Prerequisites

* Python 3.6, with the `haversine` library (for calculating GPS distances)

## Usage

* Download a .zip of each person's Google location history. This can be done via [Google Takeout](https://takeout.google.com/settings/takeout/custom/location_history).
* Run `pip3 install -r requirements.txt` to verify libraries are present
* (optional) Run `python3 analyze_history.py [zip]` to dump the contents of a single exported .zip file, just to make sure everything is parsing correctly
* Run `python3 analyze_history.py [zip1] [zip2]` to find the overlaps (the name of the .zip files doesn't matter)

## Data Set

The .zip includes two different types of timeline objects: `placeVisit` and `activitySegment`.

A `placeVisit` contains a start and end timestamp plus a GPS location and sometimes a location name and address. 

An `activitySegment` contains a start and end point, each of which has a timestamp and a GPS location. Sometimes there is also a `waypointPath` or a `simplifiedRawPath` which is a set of GPS waypoints between the start and end points. The `simplifiedRawPath` waypoints have timestamps whereas the `waypointPath` waypoints do not, for whatever reason. Therefore the `waypointPath` data is a little less reliable because we have to re-use the timestamp from the start point.

Both `placeVisit` and `activitySegment` objects contain a number of other fields that we preserve but do not use for this analysis.

## Algorithm

The algorithm for detecting overlaps is fairly naive and could certainly be improved. Currently, we combine all of the data points for both people into a single list, and sort by timestamp. Then we iterate over all points comparing the current data point to the other person's last known location. We calculate a delta between the GPS locations and the timestamps, and if both fall within a certain threshold (currently 120 mins and 1 km), we flag it as a potential overlap and print the data points along with a Google Maps URL containing the two locations.


