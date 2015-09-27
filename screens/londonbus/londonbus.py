"""This script demonstrates how to retrieve bus countdown information
from the TfL website and turn it into a structure that can then be used by
other python codes.

Unfortunately, the bus countdown information is not true JSON so, as you'll
see from the code below, we need to play with it a bit first in order to
parse it successfully.

Please note, if you use TfL data in your application you should
acknowledge the source of your data as appropriate.
"""

# Simple way of submitting web requests (easier to use than urllib2)
import requests

# We need json to turn the JSON response into a python dict/list
import json

# We need datetime to calculate the amount of time until the bus is departure
from datetime import datetime

# This is the address used for the bus stop information.
# We'll need the bus stop ID (5 number code) but we'll set this when calling
# out lookup function so, for now, we leave a placeholder for it.
BASE_URL = ("http://countdown.api.tfl.gov.uk/interfaces/"
            "ura/instant_V1?StopCode1={stopcode}"
            "&ReturnList=LineName,DestinationText,EstimatedTime")


def __getBusData(stopcode):
    # Add the stop code to the web address and get the page
    r = requests.get(BASE_URL.format(stopcode=stopcode))

    # If the request was ok
    if r.status_code == 200:

            # try and load the response into JSON
            # However, the TFL data is not true JSON so we need a bit of
            # hackery first. The response is a string representing a list
            # on each line.
            # So first, we split the response into a list of lines
            rawdata = r.content.split("\r\n")
            # Then we turn this into a single line of list strings separated
            # by commas
            rawdata = ",".join(rawdata)
            # Lastly we wrap the string in list symbols so we have a string
            # representing a single list
            rawdata = "[{data}]".format(data=rawdata)
            # And now we can load into JSON to give us an actual list of lists
            return json.loads(rawdata)

    else:
        return None


def __getBusTime(epoch):
    """Function to convert the arrival time into something a bit more
    meaningful.

    Takes a UTC epoch time argument and returns the number of minutes until
    that time.
    """
    # The bus arrival time is in milliseconds but we want seconds.
    epoch = epoch / 1000
    # Convert the epoch time number into a datetime object
    bustime = datetime.utcfromtimestamp(epoch)
    # Calculate the difference between now and the arrival time
    # The difference is a timedelta object.
    diff = bustime - datetime.utcnow()
    # Unpack this into minutes and seconds (but we will discard the seconds)
    minutes, _ = divmod(diff.total_seconds(), 60)
    if minutes == 0:
        arrival = "Due"
    elif minutes == 1:
        arrival = "1 minute"
    else:
        arrival = "{m:.0f} minutes".format(m=minutes)

    # return both the formatted string and the timedelta object
    return arrival, diff


def BusLookup(stopcode, filterbuses=None):
    """Method to look up bus arrival times at a given bus stop.

    Takes two parameters:

      stopcode:    5 digit ID code of desired stop
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

    # Remove the first item from the list as it doesn't represent a bus
    buslist.pop(0)

    buses = []

    # Loop through the buses in our response
    for bus in buslist:
        # Create an empty dictionary for the details
        b = {}
        # Set the route number of the bus
        b["route"] = bus[1]
        # Set the destination of the bus
        b["destination"] = bus[2]
        # Get the string time and timedelta object of the bus
        b["time"], b["delta"] = __getBusTime(bus[3])
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
