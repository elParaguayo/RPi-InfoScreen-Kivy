from time import sleep
from datetime import datetime as DT
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

layout = ("ITQISHCUBMWLRPI"
          "AOQUARTERFDHALF"
          "TWENTYSFIVEGTEN"
          "TOXPASTNYTWELVE"
          "ONESIXTHREENINE"
          "FOURWTWOXELEVEN"
          "EIGHTOSEVENFIVE"
          "TENO'CLOCKHAMPM")

display = {
    "all": [0, 1, 3, 4],
    "m00": [108, 109, 110, 111, 112,	113, 114],
    "m05": [37,	38,	39,	40,	48, 49, 50, 51],
    "m10": [42,	43,	44,	48, 49,	50,	51],
    "m15": [15,	17,	18,	19,	20,	21,	22,	23,	48, 49, 50, 51],
    "m20": [30,	31,	32,	33,	34,	35,	48, 49, 50, 51],
    "m25": [30,	31,	32,	33,	34,	35,	37,	38,	39,	40,	48, 49, 50, 51],
    "m30": [26,	27,	28,	29, 48, 49, 50, 51],
    "m35": [30,	31,	32,	33,	34,	35,	37,	38,	39,	40,	45,	46],
    "m40": [30,	31,	32,	33,	34,	35,	45,	46],
    "m45": [15,	17,	18,	19,	20,	21,	22,	23,	45,	46],
    "m50": [42,	43,	44,	45,	46],
    "m55": [37,	38,	39,	40,	45,	46],
    "h01": [60,	61,	62],
    "h02": [80,	81,	82],
    "h03": [66,	67,	68,	69,	70],
    "h04": [75,	76,	77,	78],
    "h05": [101, 102, 103, 104],
    "h06": [63,	64,	65],
    "h07": [96,	97,	98,	99,	100],
    "h08": [90,	91,	92,	93,	94],
    "h09": [71,	72,	73,	74],
    "h10": [105, 106, 107],
    "h11": [84,	85,	86,	87,	88,	89],
    "h12": [54,	55,	56,	57,	58,	59],
    "am":  [116, 117],
    "pm":  [118, 119]
    }

def round_down(num, divisor):
    return num - (num%divisor)

class WordClockLetter(Label):
    textcol = ListProperty([0.15, 0.15, 0.15, 1])

    def __init__(self, **kwargs):
        super(WordClockLetter, self).__init__(**kwargs)

    def toggle(self, on):
        if on:
            self.textcol = [0, 0.8, 0.8, 1]
        else:
            self.textcol = [0.15, 0.15, 0.15, 1]

class WordClockScreen(Screen):
    def __init__(self, **kwargs):
        super(WordClockScreen, self).__init__(**kwargs)
        self.running = False
        self.timer = None

    def on_enter(self):
        if not self.running:
            self.setup()
        self.timer = Clock.schedule_interval(self.update, 1)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def update(self, *args):
        nw = DT.now()
        hour = nw.hour
        if hour > 12:
            hour -= 12
        elif hour == 0:
            hour = 1

        ampm = "am" if nw.hour < 12 else "pm"

        h = "h{:02d}".format(hour)
        m = "m{:02d}".format(round_down(nw.minute, 5))
        d = display
        tm = d["all"] + d[h] + d[m] + d[ampm]
        st = [x in tm for x in range(120)]
        updt = zip(self.letters, st)
        for z in updt:
            z[0].toggle(z[1])

    def setup(self):
        self.letters = []
        grid = GridLayout(cols=15)
        for ltr in layout:
            word = WordClockLetter(text=ltr)
            grid.add_widget(word)
            self.letters.append(word)

        self.clear_widgets()
        self.add_widget(grid)
