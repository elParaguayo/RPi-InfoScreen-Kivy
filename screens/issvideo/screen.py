from datetime import datetime

from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.videoplayer import VideoPlayer

class ISSVideoScreen(Screen):

    player = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ISSVideoScreen, self).__init__(**kwargs)
        self.timer = None

    def on_enter(self):
        self.player.state = "play"

    def on_leave(self):
        self.player.state = "stop"
