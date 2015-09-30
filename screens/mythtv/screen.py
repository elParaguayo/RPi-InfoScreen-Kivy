import os
import sys
import datetime as dt
import json
from itertools import groupby

from kivy.properties import (StringProperty,
                             DictProperty,
                             ListProperty,
                             BooleanProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout

from core.bglabel import BGLabel

from MythTV import MythBE

EPOCH = dt.datetime(1970, 1, 1)


class MythRecording(BoxLayout):
    """Widget class for displaying information about upcoming recordings."""
    rec = DictProperty({})
    bg = ListProperty([0.1, 0.15, 0.15, 1])

    def __init__(self, **kwargs):
        super(MythRecording, self).__init__(**kwargs)
        self.rec = kwargs["rec"]


class MythRecordingHeader(BGLabel):
    """Widget class for grouping recordings by day."""
    rec_date = StringProperty("")

    def __init__(self, **kwargs):
        super(MythRecordingHeader, self).__init__(**kwargs)
        self.bgcolour = [0.1, 0.1, 0.4, 1]
        self.rec_date = kwargs["rec_date"]


class MythTVScreen(Screen):
    """Main screen class for MythTV schedule.

       Screen attempts to connect to MythTV backend and retrieve list of
       upcoming recordings and display this.

       Data is cached so that information can still be viewed even if backend
       is offline (e.g. for power saving purposes).
    """
    backendonline = BooleanProperty(False)
    isrecording = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(MythTVScreen, self).__init__(**kwargs)

        # Get the path for the folder
        scr = sys.modules[self.__class__.__module__].__file__

        # Create variable to retain path to our cache fie
        self.screendir = os.path.dirname(scr)
        self.cacheFile = os.path.join(self.screendir, "cache", "cache.json")

        # Some other useful variable
        self.running = False
        self.rec_timer = None
        self.status_timer = None
        self.be = None
        self.recs = None

    def on_enter(self):
        # We only update when we enter the screen. No need for regular updates.
        self.getRecordings()
        self.drawScreen()
        self.checkRecordingStatus()

    def on_leave(self):
        pass

    def cacheRecs(self, recs):
        """Method to save local copy of recordings. Backend may not be online
           all the time so a cache enables us to display recordings if if we
           can't poll the server for an update.
        """
        with open(self.cacheFile, 'w') as outfile:
            json.dump(recs, outfile)

    def loadCache(self):
        """Retrieves cached recorings and returns as a python list object."""
        try:
            raw = open(self.cacheFile, 'r')
            recs = json.load(raw)
        except:
            recs = []

        return recs

    def recs_to_dict(self, uprecs):
        """Converts the MythTV upcoming recording iterator into a list of
           dict objects.
        """
        raw_recs = []
        recs = []

        # Turn the response into a dict object and add to our list of recorings
        for r in uprecs:
            rec = {}
            st = r.starttime
            et = r.endtime
            rec["title"] = r.title
            rec["subtitle"] = r.subtitle
            day = dt.datetime(st.year, st.month, st.day)
            rec["day"] = (day - EPOCH).total_seconds()
            rec["time"] = "{} - {}".format(st.strftime("%H:%M"),
                                           et.strftime("%H:%M"))
            rec["timestamp"] = (st - EPOCH).total_seconds()
            rec["desc"] = r.description
            raw_recs.append(rec)

        # Group the recordings by day (so we can print a header)
        for k, g in groupby(raw_recs, lambda x: x["day"]):
            recs.append((k, list(g)))

        return recs

    def getRecordings(self):
        """Attempts to connect to MythTV backend and retrieve recordings."""
        try:
            # If we can connect then get recordings and save a local cache.
            self.be = MythBE()
            uprecs = self.be.getUpcomingRecordings()
            self.recs = self.recs_to_dict(uprecs)
            self.cacheRecs(self.recs)
            self.backendonline = True
        except:
            # Can't connect so we need to set variables accordinly and try
            # to load data from the cache.
            self.be = None
            self.recs = self.loadCache()
            self.backendonline = False

    def checkRecordingStatus(self):
        """Checks whether the backend is currently recording."""
        try:
            recbe = MythBE()
            for recorder in recbe.getRecorderList():
                if recbe.isRecording(recorder):
                    self.isrecording = True
                    break
        except:
            # If we can't connect to it then it can't be recording.
            print "OOPS"
            self.isrecording = False

    def drawScreen(self):
        """Main method for rendering screen.

        If there is recording data (live or cached) then is laid out in a
        scroll view.

        If not, the user is notified that the backend is unreachable.
        """
        sv = self.ids.myth_scroll
        sv.clear_widgets()

        if self.recs:
            # Create a child widget to hold the recordings.
            self.sl = GridLayout(cols=1, size_hint=(1, None), spacing=2)
            self.sl.bind(minimum_height=self.sl.setter('height'))

            # Loop over the list of recordings.
            for rec in self.recs:

                # These are grouped by day so we need a header
                day = dt.timedelta(0, rec[0]) + EPOCH
                mrh = MythRecordingHeader(rec_date=day.strftime("%A %d %B"))
                self.sl.add_widget(mrh)

                # Then we loop over the recordings scheduled for that day
                for r in rec[1]:
                    # and add them to the display.
                    mr = MythRecording(rec=r)
                    self.sl.add_widget(mr)

            sv.add_widget(self.sl)

        else:
            lb = Label(text="Backend is unreachable and there is no cached"
                            " information")
            sv.add_widget(lb)
