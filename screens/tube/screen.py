import sys
import os
from datetime import datetime
import time

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import (ObjectProperty,
                             DictProperty,
                             StringProperty,
                             ListProperty)
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from resources.londonunderground import TubeStatus

LINES = ['BAK',
         'CEN',
         'CIR',
         'DIS',
         'DLR',
         'HAM',
         'JUB',
         'MET',
         'NOR',
         'OVE',
         'PIC',
         'TFL',
         'VIC',
         'WAT']


class TubeScreen(Screen):
    tube = DictProperty({})

    def __init__(self, **kwargs):
        self.params = kwargs["params"]
        _NUMERALS = '0123456789abcdefABCDEF'
        self._HEXDEC = {v: int(v, 16) for v in (x+y for x in _NUMERALS
                        for y in _NUMERALS)}
        self.build_dict()
        super(TubeScreen, self).__init__(**kwargs)
        self.timer = None

    def hex_to_kcol(self, hexcol):
        """Method to turn hex colour code to Kivy compatible list."""
        if hexcol.startswith("#"):
            hexcol = hexcol[1:7]

        return [self._HEXDEC[hexcol[0:2]]/255.,
                self._HEXDEC[hexcol[2:4]]/255.,
                self._HEXDEC[hexcol[4:6]]/255.,
                1]

    def build_dict(self):
        """Creates default entries in dictionary of tube status."""
        for l in LINES:
            # Alert user that we're waiting for data.
            self.tube[l] = "Loading data..."

        # Get the colours and create a dictionary
        coldict = self.params["colours"]
        self.coldict = {x[:3].upper(): coldict[x] for x in coldict}

        # Convert Tube hex colours to Kivy colours.
        hk = self.hex_to_kcol
        for c in self.coldict:
            self.coldict[c]["background"] = hk(self.coldict[c]["background"])
            self.coldict[c]["text"] = hk(self.coldict[c]["text"])
        self.tube["colours"] = self.coldict

        self.tube["update"] = "Waiting for data..."

    def update(self, dt):
        # Get the tube data or handle failure to retrieve data.
        try:
            raw = TubeStatus()
        except:
            raw = None

        # If we've got data, let's show the status
        if raw:
            temp = {x["name"][:3].upper(): x["status"] for x in raw}

        # Otherwise just say there's been an error.
        else:
            temp = {x: "Error." for x in LINES}

        for k in temp:
            self.tube[k] = temp[k]

        # Add the additional detail
        if raw:
            self.tube["detail"] = {x["name"][:3].upper(): x["detail"]
                                   for x in raw}
            self.tube["name"] = {x["name"][:3].upper(): x["name"]
                                 for x in raw}
        else:
            self.tube["detail"] = {x: "Error retrieving data." for x in LINES}
            self.tube["name"] = {x: x for x in LINES}

        self.tube["colours"] = self.coldict

        if raw:
            updt = datetime.now().strftime("%H:%M")
            self.tube["update"] = "Last updated at {}".format(updt)
            self.nextupdate = time.time() + 300

    def on_enter(self):
        self.update(None)
        self.timer = Clock.schedule_interval(self.update, 5 * 60)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def show_info(self, line):
        """If user clicks on tube line we need to show extra data.

        This method creates a TubeDetail widget instance and displays it.
        """
        w = TubeDetail(line=self.tube["name"][line],
                       detail=self.tube["detail"][line],
                       bg=self.tube["colours"][line]["background"],
                       fg=self.tube["colours"][line]["text"])
        self.ids.tubefloat.add_widget(w)


class TubeDetail(BoxLayout):
    line = StringProperty("")
    detail = StringProperty("")
    bg = ListProperty([])
    fg = ListProperty([])

    def _init__(self, **kwargs):
        super(TubeDetail, self).__init__(**kwargs)
        self.line = kwargs["line"]
        self.detail = kwargs["detail"]
        self.bg = kwargs["bg"]
        self.fg = kwargs["fg"]
