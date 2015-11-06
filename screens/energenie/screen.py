import os
import sys

from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.stacklayout import StackLayout

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from energenie_pigpio import EnergenieControl


class EnergenieButton(BoxLayout):
    """Class for displaying controls for a custom switch.

       Displays the name of the switch (if set) and two buttons to turn the
       switch on and off.
    """
    switch_name = StringProperty("")

    def __init__(self, switch_id, switch_name=None, control=None, **kwargs):
        super(EnergenieButton, self).__init__(**kwargs)

        # The ID of the switch tells the transmitter which switch it needs to
        # control
        self.switch_id = switch_id

        # Check if there's a friendly name for the switch
        if switch_name:
            self.switch_name = switch_name

        # but provide a fallback if not
        else:
            self.switch_name = "Switch #{}".format(self.switch_id)

        # Get the instance of the control object
        self.control = control

    # Events to switch the switch on and off.
    def switch_on(self):
        self.control.switch_on(self.switch_id)

    def switch_off(self):
        self.control.switch_off(self.switch_id)


class EnergenieScreen(Screen):
    nrg_box = ObjectProperty(None)
    nrg_stack = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(EnergenieScreen, self).__init__(**kwargs)
        self.running = False

        # Get the user's preferences
        self.host = kwargs["params"]["host"]
        self.switchnames = kwargs["params"].get("switchnames", {})

    def on_enter(self):
        # If we've not managed to set up the screen yet...
        if not self.running:

            # Create an instance of the controller
            self.ec = EnergenieControl(host=self.host)

            # If we can't connect
            if not self.ec.connected:

                # Let the user know
                self.nrg_stack.clear_widgets()
                msg = "Cannot connect to server on {}".format(self.host)
                lbl = Label(text=msg)
                self.nrg_stack.add_widget(lbl)

            # if we can then we need to show the buttons
            else:
                self.nrg_stack.clear_widgets()

                # We're controlling switches 1 to 4
                for i in range(1, 5):

                    # Create a button
                    switch_name = self.switchnames.get(str(i), None)
                    btn = EnergenieButton(i,
                                          switch_name=switch_name,
                                          control=self.ec)

                    # Add to the display
                    self.nrg_stack.add_widget(btn)

                # We're running
                self.running = True
