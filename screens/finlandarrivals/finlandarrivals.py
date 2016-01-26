"""This script demonstrates how to retrieve bus countdown information
from the digitransit.fi  website and turn it into a structure that can then
be used by other python codes.
"""

# Simple way of submitting web requests (easier to use than urllib2)
import requests

# We need json to turn the JSON response into a python dict/list
import json

# We need datetime to calculate the amount of time until the bus is departure
from datetime import datetime

# We need time to get the local time
import time

# This is the address used for the bus stop information.
# We'll need the bus stop ID but we'll set this when calling
# out lookup function so, for now, we leave a placeholder for it.
BASE_URL = ("http://digitransit.fi/otp/routers/finland/index/graphql")
data = \
"{" \
"  stop(id: \"%s\") {" \
"    name code" \
"    stoptimesWithoutPatterns(numberOfDepartures:20) {" \
"      trip{" \
"        tripHeadsign" \
"        route{" \
"          shortName longName type" \
"        }" \
"        alerts{" \
"          alertDescriptionTextTranslations {" \
"            text" \
"            language" \
"          }" \
"        }" \
"      }" \
"      scheduledDeparture departureDelay serviceDay" \
"    }" \
"  }" \
"}"

def __getBusData(stopcode):
    # Add the stop code to the web address and get the page
    r = requests.post(BASE_URL, data=data%stopcode, headers={"Content-type": "application/graphql"})

    # If the request was ok
    if r.status_code == 200:

            # try and load the response into JSON
            j = json.loads(r.content)
            return j['data']['stop']['stoptimesWithoutPatterns']

    else:
        return None

def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset

def __getBusTime(epoch, departuretime):
    """Function to convert the arrival time into something a bit more
    meaningful.

    Takes a UTC epoch time argument and returns the number of minutes until
    that time.
    """
    # Convert the epoch time number into a datetime object
    bustime = datetime.utcfromtimestamp(epoch+departuretime)
    localtime = datetime_from_utc_to_local(bustime)
    # Calculate the difference between now and the arrival time
    # The difference is a timedelta object.
    diff = bustime - datetime.utcnow()
    # return both the formatted string and delay
    return "{:%H:%M}".format(localtime), diff


def BusLookup(stopcode, filterbuses=None):
    """Method to look up bus arrival times at a given bus stop.

    Takes two parameters:

      stopcode:    ID code of desired stop
      filterbuses: list of bus routes to filter by. If omitted, all bus routes
                   at the stop will be shown.

    If filterbuses receives anything other than a list then a TypeError will
    be raised.

    Returns a list of dictionaries representing a bus:

      route: String representing the bus route number
      time:  String representing the due time of the bus
      delta: Timedelta object representing the time until arrival

    The list is sorted in order of arrival time with the nearest bus first.
    """
    # filterbuses should be a list, if it's not then we need to alert the
    # user.
    if filterbuses is not None and type(filterbuses) != list:
        raise TypeError("filterbuses parameter must be a list.")

    buslist = __getBusData(stopcode)

    buses = []

    # Loop through the buses in our response
    for bus in buslist:
        # Create an empty dictionary for the details
        b = {}
        # Set the route number of the bus
        b["route"] = bus['trip']['route']['shortName']
        # Set the transport type
        b["type"] = bus['trip']['route']['type']
        # Set the destination of the bus
        #b["destination"] = bus['trip']['tripHeadsign']
        b["destination"] = bus['trip']['route']['longName']
        # Get the string time and timedelta object of the bus
        b["time"], b["delta"] = __getBusTime(bus['serviceDay'], bus['scheduledDeparture'])
        # Unpack this into minutes and seconds (but we will discard the seconds)
        minutes, _ = divmod(b["delta"].total_seconds(), 60)
        delay = bus['departureDelay'] / 60
        if delay <= -60:
            b["delay"] = "Running ahead {m:.0f} minutes".format(m=minutes)
        elif delay < 180:
            b["delay"] = "{m:.0f} minutes".format(m=minutes)
        else:
            b["delay"] = "Delayed {m:.0f} minutes".format(m=minutes)
        alerts = bus['trip']['alerts']
        for alert in alerts:
            if "alert" in(b):
                b["alert"] += bus['trip']['alerts']['alertDescriptionTextTranslations']['text']
            else:
                b["alert"] = bus['trip']['alerts']['alertDescriptionTextTranslations']['text']
        # Add the bus to our list
        buses.append(b)

    # We sort the buses in order of their arrival time (the raw response is
    # not always provided in time order)
    # To do this we sort by the timedelta object as this is the most accurate
    # information we have on the buses
    buses = sorted(buses, key=lambda x: x["delta"])

    # If the user has provided a list of buses then we filter our list so that
    # our result only includes the desired routes.
    if filterbuses:
        # Let's be nice to users, if they provide a list of integers (not
        # unreasonable for a bus route number) then we'll convert it into a
        # string to match what's stored in the dictionary
        # NB string is more appropriate here is as the number represents the
        # name of the route.
        filterbuses = [str(x) for x in filterbuses]
        # Just include buses that our in our list of requested routes
        buses = [x for x in buses if x["route"] in filterbuses]

    return buses
