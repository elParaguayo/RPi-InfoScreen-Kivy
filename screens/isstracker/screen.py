from datetime import datetime, timedelta
import os

from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.garden.mapview import MapView, MapMarker, MarkerMapLayer
from kivy.clock import Clock
import ephem

class ISSScreen(Screen):
    def __init__(self, **kwargs):
        super(ISSScreen, self).__init__(**kwargs)
        tle = ("ISS",
               "1 25544U 98067A   16036.50874454  .00016717  00000-0  10270-3 0  9000",
               "2 25544  51.6401 359.6943 0006595  78.3022 281.8870 15.54418818 24347")
        self.iss = ephem.readtle(*tle)
        self.iss.compute()
        lat, lon = self.get_loc()
        self.marker = MapMarker(lat=lat, lon=lon)
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.imagefolder = os.path.join(self.path, "images")

    def on_enter(self):

        self.map = MapView(id="mpv",lat=0, lon=0, zoom=1, scale=1.5)
        #self.map.set_zoom_at(1, 200, 0, 2.5)
        x, y = self.map.get_window_xy_from(0,0,1)
        self.map.scale_at(1.2, x, y)
        self.map.add_widget(self.marker)
        self.add_widget(self.map)
        self.mmlayer = MarkerMapLayer()
        for i in range(20):
            lat, lon = self.get_loc(datetime.now() + timedelta(0, i * 300))
            self.mmlayer.add_widget(MapMarker(lat=lat, lon=lon, source=os.path.join(self.imagefolder, "dot.png")))

        self.map.add_widget(self.mmlayer)
        Clock.schedule_interval(self.update, 1)


    def update(self, *args):
        lat, lon = self.get_loc()
        self.marker.lat = lat
        self.marker.lon = lon
        self.map.remove_widget(self.marker)
        self.map.add_widget(self.marker)



    def get_loc(self, dt=None):
        if dt is None:
            self.iss.compute()
        else:
            self.iss.compute(dt)
        lat = float(self.iss.sublat / ephem.degree)
        lon = float(self.iss.sublong / ephem.degree)
        return lat, lon
