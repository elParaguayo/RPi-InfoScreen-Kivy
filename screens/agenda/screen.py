import os
import sys
import httplib2
import json
import struct
from datetime import timedelta, datetime
from datetime import time as dt_time
from itertools import groupby

from kivy.properties import (StringProperty,
                             ListProperty,
                             ObjectProperty)
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from apiclient import discovery
from authorise import get_credentials
import pytz
import dateutil.parser


# Quick function to round numbers to nearest n
def rounding(x, base=5):
    return int(base * round(float(x)/base))


class CalendarHeader(GridLayout):
    """Custom widget class to show header for date."""
    header = StringProperty("")

    def __init__(self, **kwargs):
        super(CalendarHeader, self).__init__(**kwargs)

        # Format the date e.g. "Sunday 31 November 2015"
        self.header = kwargs["dt"].strftime("%A %d %B %Y")


class CalendarItem(GridLayout):
    """Custom widget for calendar event."""
    bgcolour = ListProperty([])
    textcolour = ListProperty([])
    evdetail = StringProperty("")
    evtime = StringProperty("")

    def __init__(self, **kwargs):
        super(CalendarItem, self).__init__(**kwargs)
        self.formatEvent(kwargs["event"])

    def formatEvent(self, event):
        """Converts the event object into the relevant variables needed to
           display the item.
        """

        # Check if it's an all day event
        all_day = (event["end"] - event["start"]).days > 0

        if all_day:

            # If so, say so
            evtime = "All Day"
        else:

            # If not, format start and end times
            st = event["start"].strftime("%H:%M")
            en = event["end"].strftime("%H:%M")
            evtime = "{} - {}".format(st, en)

        # Check if there's a location set
        if event["location"]:
            evtime = "{} - {}".format(evtime, event["location"])

        # Display the event time and location
        self.evtime = evtime

        # Set the event text
        self.evdetail = event["summary"]

        # Set the calendar colour
        self.bgcolour = event["bg"]

        # Set the text colour
        # self.textcolour = event["fg"]


class AgendaScreen(Screen):
    """Base screen widget for Agenda"""

    # Need a reference to the Grid Layout
    calendar_grid = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(AgendaScreen, self).__init__(**kwargs)

        # Set the number of days we want included in our agenda
        self.max_days = kwargs.get("params", dict()).get("max_days", 90)

        # Intialise some variables
        self.running = False
        self.credentials = None
        self.calendar = None
        self.calendarlist = []
        self.timer = None

    def on_enter(self):
        # Script isn't running yet, so do a first run
        if not self.running:
            self.update()
            self.running = True

        # Set a clock schedule
        self.timer = Clock.schedule_interval(self.update, 15 * 60)

    def update(self, *args):

        # Try and authorise the machine
        if not self.credentials:
            self.credentials = get_credentials()

        # If we authorised successfully we can show a calendar
        if self.credentials:

            # Connect to the Google API
            http = self.credentials.authorize(httplib2.Http())
            self.calendar = discovery.build('calendar', 'v3', http=http)

            # Get the calendars
            self.calendarlist = self.getCalendars()

            # If we've got calendars, display them
            if self.calendarlist:
                self.drawCalendars()

    def getCalendars(self):
        """Method to retrieve list of available calendars on Google account.
        """
        if self.calendar:
            try:

                # Get the calendars
                raw_cals = self.calendar.calendarList().list().execute()
                callist = []

                # Loop over the calendars
                for cal in raw_cals.get("items", []):

                    # Build a dict of the important bits
                    c = {}
                    c["name"] = cal["summary"]
                    c["bg"] = cal["backgroundColor"]
                    c["fg"] = cal["foregroundColor"]
                    c["id"] = cal["id"]
                    callist.append(c)

                return callist

        # Any errors, return an empty list
            except:
                return []
        else:
            return []

    def parseEvent(self, event, fg, bg):
        """Method to turn google event into a format that we can use more
           easily.
        """
        # Set up a reference to UTC (all events need a timezone so we can
        # sort them)
        utc = pytz.UTC

        # Have we got a "date" or "dateTime" event?
        # Parse the start end end times as appropriate
        if event["start"].get("date", False):
            start = dateutil.parser.parse(event["start"]["date"])
            end = dateutil.parser.parse(event["end"]["date"])
        else:
            start = dateutil.parser.parse(event["start"]["dateTime"])
            end = dateutil.parser.parse(event["end"]["dateTime"])

        # Change the end time to one second earlier (useful to check number
        # of days of event)
        false_end = end - timedelta(0, 1)
        duration = false_end - start

        # Empty list for our events
        ev_list = []

        # Split long events into daily events
        for i in range(duration.days + 1):

            # Create a new start time if the daily event start time isn't the
            # same as the overall start time
            new_date = start + timedelta(i)
            if new_date.date() != start.date():
                st = datetime.combine(new_date.date(),
                                      dt_time(0, 0, tzinfo=start.tzinfo))
            else:
                st = start

            # Create a new end time if the daily event end time isn't the same
            # as the overall end time
            if new_date.date() != false_end.date():
                add_day = new_date.date() + timedelta(1)
                en = datetime.combine(add_day,
                                      dt_time(0, 0, tzinfo=start.tzinfo))
            else:
                en = end

            # If there's no timezone set, then let's set one
            if st.tzinfo is None:
                st = utc.localize(st)

            if en.tzinfo is None:
                en = utc.localize(en)

            # Create a dict of the info we need
            ev = {"fg": fg,
                  "bg": bg,
                  "summary": event.get("summary", ""),
                  "location": event.get("location", ""),
                  "start": st,
                  "end": en,
                  "stdate": st.date()}

            # Add to our list
            ev_list.append(ev)

        return ev_list

    def orderEvents(self, all_events):
        """Method to tidy up the raw event info into an ordered
           and grouped list.
        """
        ordered_events = []

        # Sort the events by start date
        all_events.sort(key=lambda z: z["stdate"])

        # Group the events by day
        for k, g in groupby(all_events, lambda x: x["stdate"]):
            ordered_events.append([k, list(g)])

        # Sort the events in each day
        for x in ordered_events:
            x[1].sort(key=lambda ev: ev["start"])

        return ordered_events

    def drawCalendars(self):
        """Method to draw the Calendar on the screen."""
        all_events = []

        time_now = datetime.utcnow()
        end_time = time_now + timedelta(self.max_days)

        # Get the time now so we can filter results.
        utc_now = time_now.strftime("%Y-%m-%dT%H:%M:00Z")

        # Set an end time 90 day's ahead
        utc_end = end_time.strftime("%Y-%m-%dT%H:%M:00Z")

        # Loop over available calendars
        for cal in self.calendarlist:

            # Create kivy-compatible versions of the calendar colours
            fg_raw = list(struct.unpack("BBB",
                                        cal["fg"][-6:].decode("hex")))
            bg_raw = list(struct.unpack("BBB",
                                        cal["bg"][-6:].decode("hex")))

            # Normalise the values and darken slightly
            fg = [rounding(x/25.5, 2)/12.0 for x in fg_raw] + [1]
            bg = [rounding(x/25.5, 2)/12.0 for x in bg_raw] + [1]

            # Get the list of events for the calendar
            raw_event = self.calendar.events().list(calendarId=cal["id"],
                                                    timeMin=utc_now,
                                                    timeMax=utc_end).execute()

            # Loop over the available events
            for cal_event in raw_event.get("items", []):

                # Parse them and add to our list
                all_events += self.parseEvent(cal_event, fg, bg)

        # Sort and group the events
        ordered_events = self.orderEvents(all_events)

        # Loop over the grops
        for day in ordered_events:

            # Exclude anything that's before today or starts more than 90 days
            # away
            if ((day[0] < time_now.date()) or (day[0] > end_time.date())):
                continue

            # Create a header and display it
            hdr = CalendarHeader(dt=day[0])
            self.calendar_grid.add_widget(hdr)

            # Loop over that day's events
            for event in day[1]:

                # Create an agenda item
                ev = CalendarItem(event=event)

                # and display it
                self.calendar_grid.add_widget(ev)
