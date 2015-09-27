"""This script demonstrates how to use etreet to parse XMl information
from a website and turn it into a structure that can then be used by other
python codes.

Please note, if you use TfL data in your application you should
acknowledge the source of your data as appropriate.
"""

# Simple way of submitting web requests (easier to use than urllib2)
import requests

# we'll use the basic eTree parser to parse the XML file
import xml.etree.cElementTree as et

# We need regular expressions to strip part of the XML file out
import re

# Web address for tube data
BASE_URL = "http://cloud.tfl.gov.uk/TrackerNet/LineStatus"


def __getTubeData():
    r = requests.get(BASE_URL)
    if r.status_code == 200:
        return r.content
    else:
        return None


def TubeStatus(filterlines=None):
    """Parse the current status of London Underground lines.

    Takes one optional parameter:

    filterlines: List of tube lines to include in results.

    Returns a list of dict objects. Each dict represents an underground line:

      name:   Name of line
      status: Short description of line status
      detail: Extended description. Will be the same as "status" unless there
              is disruption at which point this will contain more detail.

    Where filterlines has been passed then the result will only contain those
    requested lines.
    """
    filtered = True if filterlines else False

    # Get the raw XML data
    rawstatus = __getTubeData()

    if rawstatus:
        # Strip out the xmlns tag (it just makes parsing the XML file more
        # difficult)
        rawstatus = re.sub(' xmlns="[^"]+"', '', rawstatus, count=1)
        # Loa it into eTree
        status = et.XML(rawstatus)
    else:
        return None

    # Create our empty list
    lines = []

    # Loop over the lines
    for line in status.getchildren():

        # Create an empty dict object for the information
        l = {}

        # Get the line name
        l["name"] = line.find("Line").get("Name")

        # Get the short description of the status
        l["status"] = line.find("Status").get("Description")

        # Get the extended definition
        detail = line.get("StatusDetails")
        l["detail"] = detail if detail else l["status"]

        # Add to the list
        lines.append(l)

    # Do we want to filter the results?
    if filtered:
        result = [x for x in lines if x["name"] in filterlines]
    else:
        result = lines

    return result
