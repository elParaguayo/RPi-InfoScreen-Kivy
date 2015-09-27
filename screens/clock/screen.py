from datetime import datetime

from kivy.properties import DictProperty
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen


class ClockScreen(Screen):
    """Simple plugin screen to show digital clock of current time."""
    # String Property to hold time
    timedata = DictProperty(None)

    def __init__(self, **kwargs):
        self.get_time()
        super(ClockScreen, self).__init__(**kwargs)
        self.timer = None

    def get_time(self):
        """Sets self.timedata to current time."""
        n = datetime.now()
        self.timedata["h"] = n.hour
        self.timedata["m"] = n.minute
        self.timedata["s"] = n.second

    def update(self, dt):
        self.get_time()

    def on_enter(self):
        # We only need to update the clock every second.
        self.timer = Clock.schedule_interval(self.update, 1)

    def on_pre_enter(self):
        self.get_time()

    def on_pre_leave(self):
        # Save resource by unscheduling the updates.
        Clock.unschedule(self.timer)
