#!/usr/bin/env python
import os
import sys

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Rectangle, Color
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from core.bglabel import BGLabel, BGLabelButton
from core.hiddenbutton import HiddenButton
from core.infoscreen import InfoScreen
from core.getplugins import getPlugins

# Set the current working directory
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

VERSION = "0.4.0"


class InfoScreenApp(App):
    def build(self):
        # Window size is hardcoded for resolution of official Raspberry Pi
        # display. Can be altered but plugins may not display correctly.
        Window.size = (800, 480)
        return InfoScreen(plugins=plugins)

if __name__ == "__main__":
    # Get a list of installed plugins
    plugins = getPlugins()

    # Get the base KV language file for the Info Screen app.
    kv_text = "".join(open("base.kv").readlines()) + "\n"

    # Loop over the plugins
    for p in plugins:

        # and add their custom KV files to create one master KV file
        kv_text += "".join(p["kv"])

    # Load the master KV file
    Builder.load_string(kv_text)

    # Good to go. Let's start the app.
    InfoScreenApp().run()
