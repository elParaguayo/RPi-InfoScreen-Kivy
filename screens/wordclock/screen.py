import imp
import os
import sys
from datetime import datetime as DT

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen


def round_down(num, divisor):
    return num - (num % divisor)


class WordClockLetter(Label):
    """Word clock letter object. The colour of the letter is changed by calling
       the "toggle" method.
    """
    textcol = ListProperty([0.15, 0.15, 0.15, 1])

    def __init__(self, **kwargs):
        super(WordClockLetter, self).__init__(**kwargs)

        # Flag for determining whether the state of the letter has changed
        self.oldstate = False

        # Variable for the duration of the animated fade
        self.fadetime = 1

    def toggle(self, on):
        if on:
            colour = [0, 0.8, 0.8, 1]
        else:
            colour = [0.15, 0.15, 0.15, 1]

        # Add some animation effect to fade between different times.
        if on != self.oldstate:
            self.oldstate = on
            anim = Animation(textcol=colour, duration=self.fadetime)
            anim.start(self)


class WordClockScreen(Screen):
    def __init__(self, **kwargs):
        super(WordClockScreen, self).__init__(**kwargs)
        self.running = False
        self.timer = None
        self.oldtime = None

        # Set up some variables to help load the chosen layout.
        self.basepath = os.path.dirname(os.path.abspath(__file__))
        self.layouts = os.path.join(self.basepath, "layouts")
        self.lang = kwargs["params"]["language"]

    def on_enter(self):
        # We only want to set up the screen once
        if not self.running:
            self.setup()
            self.running = True

        # Set the interval timer
        self.timer = Clock.schedule_interval(self.update, 1)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def update(self, *args):
        # What time is it?
        nw = DT.now()
        hour = nw.hour
        minute = round_down(nw.minute, 5)

        # Is our language one where we need to increment the hour after 30 mins
        # e.g. 9:40 is "Twenty to ten"
        if self.config.HOUR_INCREMENT and (minute > 30):
            hour += 1

        # Convert rounded time to string
        tm = "{:02d}:{:02d}".format(hour, minute)

        # If it's the same as the last update then we don't need to do anything
        if tm != self.oldtime:

            # Change to 12 hour clock
            if hour == 24:
                hour = 0
            elif hour > 12:
                hour -= 12

            if hour == 0:
                hour = 12

            # Morning or afternoon?
            ampm = "am" if nw.hour < 12 else "pm"

            # Get necessary key names
            h = "h{:02d}".format(hour)
            m = "m{:02d}".format(minute)

            # Load the map
            d = self.config.MAP

            # Build list of the letters we need
            tm = d.get("all", []) + d[h] + d[m] + d.get(ampm, [])

            # Build a map of all letters saying whether they're on or off
            st = [x in tm for x in range(120)]

            # Create a list of tuples of (letter, state)
            updt = zip(self.letters, st)

            # Loop over the list and toggle the letter
            for z in updt:
                z[0].toggle(z[1])

    def loadLayout(self):
        """Simple method to import the layout. If the module can't be found
           then it defaults to loading the English layout.
        """
        module = os.path.join(self.layouts, "{}.py".format(self.lang))

        try:
            config = imp.load_source("layouts.{}".format(self.lang), module)

        except ImportError:
            self.lang = "english"
            config = imp.load_source("layouts.{}".format(self.lang), module)

        return config

    def setup(self):
        # Get the layout
        self.config = self.loadLayout()

        # We'll want to keep a list of all the letter objects
        self.letters = []

        # Create a grid layout that's the right size
        grid = GridLayout(cols=self.config.COLS)

        # Loop over the letters
        for ltr in self.config.LAYOUT:

            # Create a letter object
            word = WordClockLetter(text=ltr,
                                   size=self.config.SIZE,
                                   font_size=self.config.FONTSIZE)

            # add it to our list...
            grid.add_widget(word)

            # ...and to the grid layout
            self.letters.append(word)

        # Clear the screen
        self.clear_widgets()

        # add the clock layout
        self.add_widget(grid)
