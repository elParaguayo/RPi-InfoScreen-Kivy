import os
import sys
import re

from datetime import datetime
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, DictProperty

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import finlandarrivals as HB

# regex for natural sort.
nsre = re.compile('([0-9]+)')


# Define a natural sort method (thanks StackOverflow!)
def natural_sort_key(s, _nsre=nsre):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)]


class FinlandArrivals(BoxLayout):
    """Custom widget to display bus information.

       Displays route name, destination and expected arrival time.
    """
    bus_route = StringProperty("Loading...")
    bus_type = StringProperty("Loading...")
    bus_destination = StringProperty("Loading...")
    bus_time = StringProperty("Loading...")
    bus_delay = StringProperty("Loading...")

    def __init__(self, **kwargs):
        super(FinlandArrivals, self).__init__(**kwargs)
        bus = kwargs["bus"]
        self.bus_route = bus["route"]
        self.bus_type = bus["type"]
        self.bus_destination = bus["destination"]
        self.bus_time = bus["time"]
        self.bus_delay = bus["delay"]


class FinlandArrivalsStop(Screen):
    """Custom screen class for showing countdown information for a specific
       bus stop.
    """
    # String Property to hold time
    timedata = StringProperty("")
    description = StringProperty("")
    alert = StringProperty("")

    def get_time(self):
        """Sets self.timedata to current time."""
        self.timedata = "{:%H:%M:%S}".format(datetime.now())

    def update(self, dt):
        self.get_time()

    def __init__(self, **kwargs):
        super(FinlandArrivalsStop, self).__init__(**kwargs)
        self.stop = kwargs["stop"]
        self.description = self.stop["description"]
        self.filters = None
        self.get_time()
        self.stimer = None

    def on_pre_enter(self):
        self.get_time()

    def on_enter(self):
        # Refresh the information when we load the screen
        Clock.schedule_once(self.get_buses, 0.5)

        # and schedule updates every 30 seconds.
        self.timer = Clock.schedule_interval(self.get_buses, 3)
        # We only need to update the clock every second.
        self.stimer = Clock.schedule_interval(self.update, 1)


    def on_pre_leave(self):
        # Save resource by unscheduling the updates.
        Clock.unschedule(self.stimer)

    def on_leave(self):
        # Save resource by removing schedule
        Clock.unschedule(self.timer)

    def get_buses(self, *args):
        """Starts the process of retrieving countdown information."""
        try:
            # Load the bus data.
            self.buses = HB.BusLookup(self.stop["stopid"])
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
            route_found=False
            for child in self.ids.bx_filter.children:
                if (route == child.text):
                    route_found = True
            if (route_found == False):
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

        # Loop over the buses, create a FinlandArrivals object and add it to the
        # StackLayout
        for bus in buses:
            bs = FinlandArrivals(bus=bus)
            if "alert" in(bus):
                self.alert = bus["alert"]
            sl.add_widget(bs)

    def toggled(self, instance, value):
        """Updates self.filters to include only those bus routes whose
           toggle buttons are set.
        """
        self.filters = [tb.text for tb in self.ids.bx_filter.children
                        if tb.state == "down"]
        self.draw_buses()


class FinlandArrivalsScreen(Screen):
    """Base screen object for Finland Public transports.

    Has a screenmanager to hold screens for specific bus stops.
    """
    def __init__(self, **kwargs):
        super(FinlandArrivalsScreen, self).__init__(**kwargs)
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
                self.scrmgr.add_widget(FinlandArrivalsStop(stop=stop, name=nm))
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
