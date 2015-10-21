import os
import sys
import re

from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, DictProperty

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import londonbus as LB

# regex for natural sort.
nsre = re.compile('([0-9]+)')


# Define a natural sort method (thanks StackOverflow!)
def natural_sort_key(s, _nsre=nsre):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)]


class LondonBus(BoxLayout):
    """Custom widget to display bus information.

       Displays route name, destination and expected arrival time.
    """
    bus_route = StringProperty("Loading...")
    bus_destination = StringProperty("Loading...")
    bus_time = StringProperty("Loading...")

    def __init__(self, **kwargs):
        super(LondonBus, self).__init__(**kwargs)
        bus = kwargs["bus"]
        self.bus_route = bus["route"]
        self.bus_destination = bus["destination"]
        self.bus_time = bus["time"]


class LondonBusStop(Screen):
    """Custom screen class for showing countdown information for a specific
       bus stop.
    """
    description = StringProperty("")

    def __init__(self, **kwargs):
        super(LondonBusStop, self).__init__(**kwargs)
        self.stop = kwargs["stop"]
        self.description = self.stop["description"]
        self.filters = None

    def on_enter(self):
        # Refresh the information when we load the screen
        Clock.schedule_once(self.get_buses, 0.5)

        # and schedule updates every 30 seconds.
        self.timer = Clock.schedule_interval(self.get_buses, 30)

    def on_leave(self):
        # Save resource by removing schedule
        Clock.unschedule(self.timer)

    def get_buses(self, *args):
        """Starts the process of retrieving countdown information."""
        try:
            # Load the bus data.
            self.buses = LB.BusLookup(self.stop["stopid"])
        except:
            # If there's an error (e.g. no internet connection) then we have
            # no bus data.
            self.buses = None

        if self.buses:
            # We've got bus data so let's update the screen.
            self.draw_filter()
        else:
            # No bus data so notify the user.
            lb = Label(text="Error fetching data...")
            self.ids.bx_filter.clear_widgets()
            self.ids.bx_filter.add_widget(lb)

    def draw_filter(self):
        """Create a list of toggle buttons to allow user to show which buses
           should be shown on the screen.
        """
        # If we've got no filter then we need to set it up:
        if self.filters is None:

            # Clear the previous filter
            self.ids.bx_filter.clear_widgets()

            # Get the list of unique bus routes and apply a natural sort.
            routes = sorted(set([x["route"] for x in self.buses]),
                            key=natural_sort_key)

            # Create a toggle button for each route and set it as enabled
            # for now.
            for route in routes:
                tb = ToggleButton(text=route, state="down")
                tb.bind(state=self.toggled)
                self.ids.bx_filter.add_widget(tb)

        # Run the "toggled" method now as this updates which buses are shown.
        self.toggled(None, None)

    def draw_buses(self):
        """Adds the buses to the main screen."""
        # Clear the screen of any buses.
        self.ids.bx_buses.clear_widgets()

        # Get a list of just those buses who are included in the filter.
        buses = [b for b in self.buses if b["route"] in self.filters]

        # Work out the height needed to display all the buses
        # (we need this for the StackLayout)
        h = (len(buses) * 30)

        # Create a StackLayout and ScrollView
        sl = StackLayout(orientation="tb-lr", height=h, size_hint=(1, None))
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(sl)
        self.ids.bx_buses.add_widget(sv)

        # Loop over the buses, create a LondonBus object and add it to the
        # StackLayout
        for bus in buses:
            bs = LondonBus(bus=bus)
            sl.add_widget(bs)

    def toggled(self, instance, value):
        """Updates self.filters to include only those bus routes whose
           toggle buttons are set.
        """
        self.filters = [tb.text for tb in self.ids.bx_filter.children
                        if tb.state == "down"]
        self.draw_buses()


class LondonBusScreen(Screen):
    """Base screen object for London Buses.

    Has a screenmanager to hold screens for specific bus stops.
    """
    def __init__(self, **kwargs):
        super(LondonBusScreen, self).__init__(**kwargs)
        self.params = kwargs["params"]
        self.stops = self.params["stops"]
        self.flt = self.ids.lbus_float
        self.flt.remove_widget(self.ids.lbus_base_box)
        self.scrmgr = self.ids.lbus_scrmgr
        self.running = False
        self.scrid = 0
        self.myscreens = [str(x["stopid"]) for x in self.stops]

    def on_enter(self):
        # If this is the first time we've come across the screen then we need
        # to set up a sub-screen for each bus stop.
        if not self.running:
            for stop in self.stops:
                nm = str(stop["stopid"])
                self.scrmgr.add_widget(LondonBusStop(stop=stop, name=nm))
            self.running = True

        else:
            # Fixes bug where nested screens don't have "on_enter" or
            # "on_leave" methods called.
            for c in self.scrmgr.children:
                if c.name == self.scrmgr.current:
                    c.on_enter()

    def on_leave(self):
        # Fixes bug where nested screens don't have "on_enter" or
        # "on_leave" methods called.
        for c in self.scrmgr.children:
            if c.name == self.scrmgr.current:
                c.on_leave()

    def next_screen(self, rev=True):
        a = self.myscreens
        n = -1 if rev else 1
        self.scrid = (self.scrid + n) % len(a)
        self.scrmgr.transition.direction = "up" if rev else "down"
        self.scrmgr.current = a[self.scrid]
