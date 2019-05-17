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
BASE_URL = ("http://api.digitransit.fi/routing/v1/routers/finland/index/graphql")
data = \
"{" \
"  stop(id: \"%s\") {" \
"    stoptimesWithoutPatterns(numberOfDepartures:20) {" \
"      trip{" \
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

def __getBusTime(epoch, departuretime, delaytime):
    """Function to convert the arrival time into something a bit more
    meaningful.

    Takes a UTC epoch time argument and returns the number of minutes until
    that time.
    """
    # Convert the epoch time number into a datetime object
    bustime = datetime.utcfromtimestamp(epoch+departuretime)
    realbustime = datetime.utcfromtimestamp(epoch+departuretime+delaytime)
    localtime = datetime_from_utc_to_local(bustime)
    estimatedtime = datetime_from_utc_to_local(realbustime)
    # Calculate the difference between now and the arrival time
    # The difference is a timedelta object.
    diff = bustime - datetime.utcnow()
    # return both the formatted string and delay
    return "{:%H:%M}".format(localtime), diff, "{:%H:%M}".format(estimatedtime)


def BusLookup(stopcode):
    """Method to look up bus arrival times at a given bus stop.

    Takes two parameters:

      stopcode:    ID code of desired stop

    Returns a list of dictionaries representing a bus:

      route: String representing the bus route number
      time:  String representing the due time of the bus
      delta: Timedelta object representing the time until arrival

    The list is sorted in order of arrival time with the nearest bus first.
    """

    buslist = __getBusData(stopcode)

    buses = []

    # Loop through the buses in our response
    for bus in buslist:
        # Create an empty dictionary for the details
        b = {}
        # Set the route number of the bus
        b["route"] = bus['trip']['route']['shortName']
        if not b["route"]:
            b["route"] = u"0"
        # Set the transport type
        b["type"] = str(bus['trip']['route']['type'])
        # Set the destination of the bus
        b["destination"] = bus['trip']['route']['longName']
        # Get the string time and timedelta object of the bus
        b["time"], b["delta"], b["estimated"] = __getBusTime(bus['serviceDay'], bus['scheduledDeparture'], bus['departureDelay'])
        # Unpack this into minutes and seconds (but we will discard the seconds)
        minutes, _ = divmod(b["delta"].total_seconds(), 60)
        delay = bus['departureDelay']
        if delay <= -60:
            b["delay"] = "Running ahead {m:.0f} minutes".format(m=minutes)
        elif delay < 180:
            b["delay"] = ""
        else:
            b["delay"] = "Estimated "+b["estimated"]
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
    return sorted(buses, key=lambda x: x["delta"])
