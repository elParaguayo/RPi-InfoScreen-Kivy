import os
import sys
import time

from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.properties import StringProperty, ListProperty

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import nationalrail as NR


class TrainJourney(Screen):
    desc = StringProperty("")
    headers = {"departing": "Dep.",
               "arriving": "Arr.",
               "changes": "Changes",
               "duration": "Dur.",
               "status": "Status",
               "from_platform": "Platform"
               }

    def __init__(self, **kwargs):
        super(TrainJourney, self).__init__(**kwargs)
        j = kwargs["journey"]
        self.desc = j["description"]
        self.to = j["to"]
        self.frm = j["from"]
        self.running = False
        self.nextupdate = 0
        self.timer = None

    def on_enter(self):
        # Calculate when the next update is due.
        if (time.time() > self.nextupdate):
            dt = 0.5
        else:
            dt = self.nextupdate - time.time()

        self.timer = Clock.schedule_once(self.getTrains, dt)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def getTrains(self, *args):
        # Try loading the train data but handle any failure gracefully.
        try:
            trains = NR.lookup(self.frm, self.to)
        except:
            trains = None

        # If we've got trains then we need to set up the screen
        if trains:
            # Get rid of the previous widgets.
            self.clear_widgets()

            # Add a box layout
            self.bx = BoxLayout(orientation="vertical")

            # Show the name of the train route
            self.bx.add_widget(Label(text=self.desc, size_hint_y=0.2))

            # Add headers for the trains
            self.bx.add_widget(TrainDetail(train=self.headers,
                                           bg=[0.2, 0.2, 0.2, 1]))

            # Create a StackLayout in case we need to scroll over the trains.
            self.stck = StackLayout(orientation="tb-lr", size_hint_y=0.8)
            self.bx.add_widget(self.stck)

            # Loop over the trains
            for train in trains:

                # Create a TrainDetail widget and add it to the StackLayout
                trn = TrainDetail(train=train)
                self.stck.add_widget(trn)

            # Get rid of the Loading label (if it's there)
            try:
                self.remove_widget(self.ids.load_label)
            except ReferenceError:
                pass

            self.add_widget(self.bx)

            # Set the next update for 5 mins later
            self.nextupdate = time.time() + 300
            self.timer = Clock.schedule_once(self.getTrains, 300)

        # No trains so let the user know.
        else:
            self.clear_widgets()
            errorm = ("Error getting train data.\nPlease check that you are "
                      "connected to the internet and\nthat you have entered "
                      "valid station names.")
            lb = Label(text=errorm)
            self.add_widget(lb)


class TrainDetail(BoxLayout):
    """Custom widget to show detail for a specific train."""
    departing = StringProperty("")
    arriving = StringProperty("")
    changes = StringProperty("")
    status = StringProperty("")
    duration = StringProperty("")
    platform = StringProperty("")
    bg = ListProperty([0.1, 0.1, 0.1, 1])

    def __init__(self, **kwargs):
        super(TrainDetail, self).__init__(**kwargs)
        t = kwargs["train"]
        self.departing = t["departing"]
        self.arriving = t["arriving"]
        self.changes = t["changes"]
        self.duration = t["duration"]
        self.status = t["status"]
        self.platform = t.get("from_platform", "")
        self.bg = kwargs.get("bg", [0.1, 0.1, 0.1, 1])


class TrainScreen(Screen):
    def __init__(self, **kwargs):
        super(TrainScreen, self).__init__(**kwargs)
        self.params = kwargs["params"]
        self.journeys = self.params["journeys"]
        self.flt = self.ids.train_float
        self.flt.remove_widget(self.ids.train_base_box)
        self.scrmgr = self.ids.train_scrmgr
        self.running = False
        self.scrid = 0
        self.myscreens = ["{to}{from}".format(**x) for x in self.journeys]

    def on_enter(self):
        # If the screen hasn't been run before then we need to set up the
        # screens for the necessary train journeys.
        if not self.running:
            for journey in self.journeys:
                nm = "{to}{from}".format(**journey)
                self.scrmgr.add_widget(TrainJourney(journey=journey, name=nm))
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
