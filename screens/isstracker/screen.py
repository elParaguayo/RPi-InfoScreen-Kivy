from datetime import datetime, timedelta
import os
import json

from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.garden.mapview import MapView, MapMarker, MarkerMapLayer
from kivy.clock import Clock

import requests
import ephem

class ISSScreen(Screen):
    def __init__(self, **kwargs):
        super(ISSScreen, self).__init__(**kwargs)

        # Set the path for the folder
        self.path = os.path.dirname(os.path.abspath(__file__))

        # Set the path for local images
        self.imagefolder = os.path.join(self.path, "images")

        # Ephem calculates the position using the Two Line Element data
        # We need to make sure we have up to date info
        tle = self.get_TLE()

        # Create an iss object from which we can get positional data
        self.iss = ephem.readtle(*tle)

        # Run the calculations
        self.iss.compute()

        # Get positon of iss and place a marker there
        lat, lon = self.get_loc()
        self.marker = MapMarker(lat=lat, lon=lon)

        # Create a value to check when we last drew ISS path
        self.last_path_update = 0

        # Create the path icon
        self.path_icon = os.path.join(self.imagefolder, "dot.png")

    def on_enter(self):

        # Create the world map
        self.map = MapView(id="mpv",lat=0, lon=0, zoom=1, scale=1.5)
        x, y = self.map.get_window_xy_from(0,0,1)
        self.map.scale_at(1.2, x, y)

        # Add the ISS marker to the map and draw the map on the screen
        self.map.add_widget(self.marker)
        self.add_widget(self.map)

        # Add a new layer for the path
        self.mmlayer = MarkerMapLayer()

        self.draw_iss_path()

        Clock.schedule_interval(self.update, 1)

    def utcnow(self):
        return (datetime.utcnow() - datetime(1970,1,1)).total_seconds()

    def draw_iss_path(self):

        # Path is drawn every 5 mins
        if self.utcnow() - self.last_path_update > 30:

            try:
                self.map.remove_layer(self.mmlayer)
            except:
                pass

            self.mmlayer = MarkerMapLayer()

            # Create markers showing the ISS's position every 5 mins
            for i in range(20):
                lat, lon = self.get_loc(datetime.now() + timedelta(0, i * 300))
                self.mmlayer.add_widget(MapMarker(lat=lat,
                                                  lon=lon,
                                                  source=self.path_icon))

            # Update the flag so we know when next update should be run
            self.last_path_update = self.utcnow()

            # Add the layer and call the reposition function otherwise the
            # markers don't show otherwise!
            self.map.add_layer(self.mmlayer)
            self.mmlayer.reposition()

    def get_TLE(self):

        # Set some flags
        need_update = False

        # Set our data source and the name of the object we're tracking
        source = "http://www.celestrak.com/NORAD/elements/stations.txt"
        ISS = "ISS (ZARYA)"

        # Get the current time
        utc_now = self.utcnow()

        # Set the name of our file to store data
        data = os.path.join(self.path, "iss_tle.json")

        # Try loading old data
        try:
            with open(data, "r") as savefile:
                saved = json.load(savefile)

        # If we can't create a dummy dict
        except IOError:
            saved = {"updated": 0}

        # If old data is more than an hour hold, let's check for an update
        if utc_now - saved["updated"] > 3600:
            need_update = True

        # If we don't have any TLE data then we need an update
        if not saved.get("tle"):
            need_update = True

        if need_update:

            # Load the TLE data
            raw = requests.get(source).text

            # Split the data into a neat list
            all_sats = [sat.strip() for sat in raw.split("\n")]

            # Find the ISS and grab the whole TLE (three lines)
            iss_index = all_sats.index(ISS)
            iss_tle = all_sats[iss_index:iss_index + 3]

            # Prepare a dict to save our data
            new_tle = {"updated": utc_now,
                       "tle": iss_tle}

            # Save it
            with open(data, "w") as savefile:
                json.dump(new_tle, savefile, indent=4)

            # ephem needs strings not unicode
            return [str(x) for x in iss_tle]

        else:
            # return the saved data (as strings)
            return [str(x) for x in saved["tle"]]

    def update(self, *args):

        # Update the ISS with newest TLE
        self.iss = ephem.readtle(*self.get_TLE())

        # Get the position and update marker
        lat, lon = self.get_loc()
        self.marker.lat = lat
        self.marker.lon = lon
        self.map.remove_widget(self.marker)
        self.map.add_widget(self.marker)

        # Check if the path needs redrawing
        self.draw_iss_path()

    def get_loc(self, dt=None):

        # We can get the location for a specific time as well
        if dt is None:
            self.iss.compute()
        else:
            self.iss.compute(dt)

        # Convert the ephem data into something that the map can use
        lat = float(self.iss.sublat / ephem.degree)
        lon = float(self.iss.sublong / ephem.degree)

        return lat, lon
