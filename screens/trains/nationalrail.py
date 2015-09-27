"""This script demonstrates how to use BeautifulSoup to retrieve information
from a website and turn it into a structure that can then be used by other
python codes.

Please note, scraping data from the National Rail website is against their
terms and conditions. As such, this code should not be incorporated into any
projects.
"""

# We need the datetime module because the timetable lookup requires a time
# We can therefore insert the current time to get details on the next trains
from datetime import datetime

# Simple way of submitting web requests (easier to use than urllib2)
import requests

# BeautifulSoup is the tool we'll use for scraping the pages
from BeautifulSoup import BeautifulSoup

# Regular expressions will be needed to match certain classes and manipulate
# some data we get back.
import re

# Base web address of the data that we want
NR_BASE = "http://ojp.nationalrail.co.uk/service/timesandfares/"
# These are the bits that will change based on what information we want to get
# start:     3 letter code of starting station
# dest:      3 letter code of destination
# dep_day:   day of travel in DDMMYY format, or "today"
# dep_time:  time of travel in HHMM format
# direction: Are we searching by time of departure or arrival?
SUFFIX = "{start}/{dest}/{dep_day}/{dep_time}/{direction}"


# All the methods beginning with "__" are just the "behind the scenes" working
# and are "hidden" from the user.


# Simple method to submit web request
def __getPage(url):
    r = requests.get(url)
    if r.status_code == 200:
        return r.text
    else:
        return None


# Method to parse the page
def __parsePage(page):
    # Stop if we didn't get any info back from the web request
    if page is None:
        return None

    else:
        # Send the web page to BeautifulSoup
        raw = BeautifulSoup(page)
        try:
            # We're using looking for table rows that contain "mtx" in the
            # class tag. We need to use regex here as there may be other
            # strings in the tag too. e.g. '<tr class="first mtx">'
            re_mtx = re.compile(r'\bmtx\b')
            # the findAll method can then be used to find every instance of
            # a match. Returns a list of matching objects.
            mtx = raw.findAll("tr", {"class": re_mtx})
            # to avoid too much indentaton we'll handle the parsing of these
            # objects in a new method
            return __getTrains(mtx)
        except:
            raise


def __getTrains(mtx):

    # Create an empty list to store the trains in
    trains = []

    # Nested function (so it's not available outside of  __getTrains)
    def txt(train, tclass):
        try:
            # This is just be being lazy to avoid repeating the whole
            # find line lots of times!
            return train.find("td", {"class": tclass}).text.strip()
        except:
            return None

    # Another nested function...
    def status(train):

        # The status box is a bit different to we need to parse this
        # differently. Let's look to see if there is an "on-time" status
        if train.find("td",
                      {"class": re.compile(r"\bjourney-status-on-time\b")}):
            return "On Time"
        else:
            return txt(train, "status")

    # Loop over the matching trains
    for train in mtx:

        # Create a blank dictionary instance for the train
        t = {}

        # Get details of departing station
        # Some stations have this format "Long name [CODE] Platoform"
        # We don't need the [CODE] so let's use regex to split the string
        # around any 3 letter code in square brackets
        dep_station = re.split("\[[A-Z]{3}\]", txt(train, "from"))
        # The first bit is the station name
        t["from"] = dep_station[0].strip()
        # Now look for a platform
        try:
            platform = re.sub("\s\s+", " ", dep_station[1])
        # IndexError will be raised if there is not dep_station[1]
        except IndexError:
            platform = ""
        finally:
            t["from_platform"] = platform

        # Get details of destination station
        # See notes above
        arr_station = re.split("\[[A-Z]{3}\]", txt(train, "to"))
        t["to"] = arr_station[0].strip()
        try:
            platform = re.sub("\s\s+", " ", arr_station[1])
        except IndexError:
            platform = ""
        finally:
            t["to_platform"] = platform

        # Get remaining information
        # These should be self explanatory now.
        t["departing"] = txt(train, "dep")
        t["arriving"] = txt(train, "arr")
        t["duration"] = txt(train, "dur")
        t["changes"] = txt(train, "chg")
        t["status"] = status(train)

        # Add the train to our list
        trains.append(t)

    return trains


def __hhmm():
    # The site needs takes a time string in the format HHMM.
    # This function returns the current time in that format
    return datetime.now().strftime("%H%M")


# These are our main functions i.e. the methods that a user may call
# It's good practice to include a docstring to provide useful information as
# to how to use the function and what to expect back.


def lookup(start, dest, dep_time=None, dep_day=None, arriving=False):
    """Timetable lookup. Returns list of trains.

    Params:
        start:     3 letter code of departure station
        dest:      3 letter code of target station
        dep_time:  HHMM formatted time. Leave blank for now.
        dep_day:   DDMMYY formatted date. Leave blank for today.
        arriving:  boolean. Set to True to search by arrival time.

    Each train object is a dictionary with the following keys:
        from:           Name of starting station
        from_platform:  Platform at starting station
        to:             Destination station
        to_platform:    Platform at destination station
        departing:      Scheduled departure time
        arriving:       Scheduled arrival time
        duration:       Journey duration
        changes:        Number of changes required
        status:         Status of train
    """
    # For "Now" searches we need current time...
    if not dep_time:
        dep_time = __hhmm()
    # ...and date as "today"
    if not dep_day:
        dep_day = "today"

    # This is the flag for whether we searching by departure or arrival time
    direction = "ARR" if arriving else "DEP"

    # build the URL with all the relevant bits
    suffix = SUFFIX.format(start=start, dest=dest, dep_day=dep_day,
                           dep_time=dep_time, direction=direction)

    url = "{base}{suffix}".format(base=NR_BASE, suffix=suffix)

    # Get the full web page and send it to the parser
    trains = __parsePage(__getPage(url))

    # If something's gone wrong, return an empty list, otherwise return the
    # details of the trains
    return trains if trains else []


def departures(start, dest=None):
    """Gets live departures. Returns list of trains.

    Params:
    start:   Starting station
    dest:    (Optional) Destination station.
    """
    raise NotImplementedError


def arrivals(dest, start=None):
    """Gets live arrivals. Returns list of trains.

    Params:
    dest:    Destination station.
    start:   (Optional) Starting station
    """
    raise NotImplementedErrors
