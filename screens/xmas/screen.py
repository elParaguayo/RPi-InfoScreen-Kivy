from datetime import datetime

from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

class XmasScreen(Screen):

    first_line = StringProperty("")
    second_line = StringProperty("")
    third_line = StringProperty("")

    def __init__(self, **kwargs):
        super(XmasScreen, self).__init__(**kwargs)
        self.xmas = self.getChristmas()
        self.first_line = "There are..."
        self.second_line = "[calculating time...]"
        self.third_line = "until Christmas!"
        self.timer = None

    def getChristmas(self):
        nw = datetime.now()
        if nw.month == 12 and nw.day > 25:
            yr = nw.year + 1
        else:
            yr = nw.year

        return datetime(yr, 12, 25, 0, 0)

    def on_enter(self):
        self.timer = Clock.schedule_interval(self.update, 1)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def update(self, *args):
        nw = datetime.now()

        delta = self.xmas - nw

        if delta.total_seconds() < 0:
            # It's Christmas

            self.first_line = ""
            self.second_line = "[size=100]Happy Christmas![/size]"
            self.third_line = ""

        else:

            d = delta.days
            h, rem = divmod(delta.seconds, 3600)
            m, _ = divmod(rem, 60)

            self.first_line = "There are..."
            self.second_line = ("[size=30][size=70]{d}[/size] days, "
                                "[size=60]{h}[/size] hours and "
                                "[size=60]{m}[/size] "
                                "minutes[/size]").format(d=d, h=h, m=m)
            self.third_line = "...until Christmas."
