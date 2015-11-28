import imp

from kivy.uix.floatlayout import FloatLayout
from kivy.properties import BooleanProperty

from core.failedscreen import FailedScreen


class InfoScreen(FloatLayout):
    # Flag for determining whether screen is locked or not
    locked = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(InfoScreen, self).__init__(**kwargs)

        # Get our list of available plugins
        plugins = kwargs["plugins"]

        # We need a list to hold the names of the enabled screens
        self.availablescreens = []

        # and an index so we can loop through them:
        self.index = 0

        # We want to handle failures gracefully so set up some variables
        # variable to hold the FailScreen object (if needed)
        self.failscreen = None

        # Empty lists to track various failures
        dep_fail = []
        failedscreens = []

        # Create a reference to the screenmanager instance
        self.scrmgr = self.ids.iscreenmgr

        # Loop over plugins
        for p in plugins:

            # Set up a tuple to store list of unmet dependencies
            p_dep = (p["name"], [])

            # Until we hit a failure, there are no unmet dependencies
            unmet = False

            # Loop over dependencies and test if they exist
            for d in p["dependencies"]:
                try:
                    imp.find_module(d)
                except ImportError:
                    # We've got at least one unmet dependency for this screen
                    unmet = True
                    p_dep[1].append(d)

            # Can we use the screen?
            if unmet:
                # Add the tupe to our list of unmet dependencies
                dep_fail.append(p_dep)

            # No unmet dependencies so let's try to load the screen.
            else:
                try:
                    plugin = imp.load_module("screen", *p["info"])
                    screen = getattr(plugin, p["screen"])
                    self.scrmgr.add_widget(screen(name=p["name"],
                                           master=self,
                                           params=p["params"]))

                # Uh oh, something went wrong...
                except Exception, e:
                    # Add the screen name and error message to our list
                    failedscreens.append((p["name"], repr(e)))

                else:
                    # We can add the screen to our list of available screens.
                    self.availablescreens.append(p["name"])

        # If we've got any failures then let's notify the user.
        if dep_fail or failedscreens:

            # Create the FailedScreen instance
            self.failscreen = FailedScreen(dep=dep_fail,
                                           failed=failedscreens,
                                           name="FAILEDSCREENS")

            # Add it to our screen manager and make sure it's the first screen
            # the user sees.
            self.scrmgr.add_widget(self.failscreen)
            self.scrmgr.current = "FAILEDSCREENS"

    def toggle_lock(self, locked=None):
        if locked is None:
            self.locked = not self.locked
        else:
            self.locked = bool(locked)

    def next_screen(self, rev=False):
        if not self.locked:
            if rev:
                self.scrmgr.transition.direction = "right"
                inc = -1
            else:
                self.scrmgr.transition.direction = "left"
                inc = 1

            self.index = (self.index + inc) % len(self.availablescreens)
            self.scrmgr.current = self.availablescreens[self.index]
