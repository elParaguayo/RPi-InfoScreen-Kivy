import os
import sys
import time
from kivy.uix.widget import Widget
from kivy.properties import (ObjectProperty,
                             DictProperty,
                             ListProperty,
                             StringProperty,
                             BooleanProperty)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock
from kivy.config import Config
from kivy.graphics import Color
from datetime import datetime
from time import sleep
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import AsyncImage
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from footballresources.footballscores import FootballMatch, League
from core.bglabel import BGLabel

EVT_GOAL = 0
EVT_KICK_OFF = 1
EVT_HALF_TIME = 2
EVT_FULL_TIME = 3
EVT_YELLOW_CARD = 4
EVT_RED_CARD = 5

EVT_LOOKUP = {EVT_GOAL: {"text": "GOAL!", "size": 200},
              EVT_KICK_OFF: {"text": "KICK\nOFF", "size": 175},
              EVT_HALF_TIME: {"text": "HALF\nTIME", "size": 175},
              EVT_FULL_TIME: {"text": "FULL\nTIME", "size": 175}
              }

OBJ_MATCH = 0
OBJ_LEAGUE = 1

MATCH_COLOURS = {"L": [0.1, 0.1, 0.5, 1],
                 "HT": [0.1, 0.3, 0.3, 1],
                 "FT": [0.5, 0.1, 0.1, 1],
                 "FIXTURE": [0.1, 0.1, 0.1, 1],
                 "GOAL": [0.1, 0.4, 0.1, 1]}

# Football Matches ###########################################################


class FootballEvent(BGLabel):
    """Simple class to show a label displaying a notification."""
    event_text = StringProperty("")

    def __init__(self, **kwargs):
        super(FootballEvent, self).__init__(**kwargs)
        self.event_text = kwargs["eventtext"]


class FootballNoMatch(BoxLayout):
    """Widget when team is not playing."""
    teamname = StringProperty("")

    def __init__(self, **kwargs):
        super(FootballNoMatch, self).__init__(**kwargs)
        self.teamname = kwargs["teamname"]


class FootballBase(Screen):
    """Screen for a football match."""
    teamname = StringProperty("")

    def __init__(self, **kwargs):
        super(FootballBase, self).__init__(**kwargs)
        self.team = kwargs["team"]
        self.teamname = self.team
        self.running = False
        self.no_match = None
        self.scr_match = None
        self.timer = None
        self.nextupdate = 0

    def on_enter(self):
        """Calculates when next update is due and sets schedule."""
        if not self.running:
            Clock.schedule_once(self.getMatchObject, 0.5)

        tm = time.time()

        if tm > self.nextupdate:
            dt = 0.5
        else:
            dt = self.nextupdate - tm

        self.timer = Clock.schedule_once(self.update, dt)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def getMatchObject(self, *args):
        """Initialise the FootballMatch object (can take time)."""
        if not self.running:
            self.matchobject = FootballMatch(self.team, detailed=True)
            self.running = True
        self.checkscreen()

    def checkscreen(self):
        """Updates the screen depending on wether or not there is a match
           happening today.
        """
        # Remove the "loading" screen
        try:
            loading = self.ids.lbl_load
            self.ids.base_float.remove_widget(loading)
        except:
            pass

        # There is a football match so clear the screen and show the
        # football match information.
        if self.matchobject.MatchFound:
            if self.no_match or not self.scr_match:
                if self.no_match:
                    self.ids.base_float.remove_widget(self.ids.no_match)
                    self.no_match = None
                self.scr_match = FootballMatchScreen(mo=self.matchobject,
                                                     id="scr_match")
                self.ids.base_float.add_widget(self.scr_match)
            else:
                if self.scr_match:
                    self.scr_match.update(self.matchobject)

        # There's no football match so clear the screen and tell the user.
        else:
            if self.scr_match or not self.no_match:
                if self.scr_match:
                    self.ids.base_floatremove_widget(self.ids.scr_match)
                    self.scr_match = None
                self.no_match = FootballNoMatch(teamname=self.team,
                                                id="no_match")
                self.ids.base_float.add_widget(self.no_match)

    def notifyEvent(self, event_type=EVT_HALF_TIME):
        """A bit of fun animation to notify match events."""
        t = EVT_LOOKUP[event_type]
        g = FootballEvent(eventtext=t["text"])
        self.ids.base_float.add_widget(g)
        in_anim = Animation(font_size=t["size"], d=1, t="out_back")
        in_anim &= Animation(bgcolour=[0, 0, 0, 1], d=1, t="out_expo")
        out_anim = Animation(font_size=0, d=1, t="out_back")
        out_anim &= Animation(bgcolour=[0, 0, 0, 0], d=1, t="out_expo")
        anim = in_anim + Animation(d=2.) + out_anim
        anim.bind(on_complete=self.notifyComplete)
        anim.start(g)

    def notifyComplete(self, anim, widget):
        """Removes the notification widget once the animation is finished."""
        anim.unbind()
        self.ids.base_float.remove_widget(widget)

    def update(self, *args):
        """Updates the matchobject and then triggers additional events
           depending on the match status.
        """
        self.matchobject.Update()

        # Gooooooooooooaaaaaaaaaaaaaallllllllll!
        if self.matchobject.Goal:
            self.notifyEvent(event_type=EVT_GOAL)

        elif self.matchobject.StatusChanged:
            status = self.matchobject.Status
            if status == "FT":
                self.notifyEvent(event_type=EVT_FULL_TIME)
            elif status == "HT":
                self.notifyEvent(event_type=EVT_HALF_TIME)
            elif status == "L":
                self.notifyEvent(event_type=EVT_KICK_OFF)

        # Schedule next update
        if self.matchobject:
            dt = 30
        else:
            dt = 60 * 60

        self.nextupdate = time.time() + dt
        self.timer = Clock.schedule_once(self.update, dt)

        # Refresh data on the screen.
        self.checkscreen()


class FootballMatchScreen(FloatLayout):
    """Displays information of active football match."""
    hometeam = StringProperty("")
    awayteam = StringProperty("")
    homescore = StringProperty("")
    awayscore = StringProperty("")
    homebadge = StringProperty("images/10x10_transparent.png")
    awaybadge = StringProperty("images/10x10_transparent.png")
    status = StringProperty("")

    def __init__(self, **kwargs):
        super(FootballMatchScreen, self).__init__(**kwargs)
        self.matchobject = kwargs["mo"]
        self.homestack = self.ids.home_incidents
        self.awaystack = self.ids.away_incidents
        self.checkMatch()

        # Try loading team badges
        if self.matchobject.getTeamBadges():
            self.homebadge = self.matchobject.HomeBadge
            self.awaybadge = self.matchobject.AwayBadge

    def update(self, mo):
        """Updates the screen with the information from the match object
           provided.
        """
        self.matchobject = mo
        self.checkMatch(None)

    def checkMatch(self, dt=0):
        """Updates the screen with the information from the match object
           provided.
        """
        self.hometeam = self.matchobject.HomeTeam
        self.awayteam = self.matchobject.AwayTeam
        self.homescore = str(self.matchobject.HomeScore)
        self.awayscore = str(self.matchobject.AwayScore)
        self.status = str(self.matchobject.MatchTime)
        self.doIncidents()

    def doIncidents(self):
        """Format details of match incidents (currently just goal scorers)."""
        self.homestack.clear_widgets()
        self.awaystack.clear_widgets()
        m = self.matchobject
        if m.HomeScorers:
            for p in m.formatIncidents(m.HomeScorers, True).split("\n"):
                i = Incident(player=p, home=True)
                self.homestack.add_widget(i)

        if m.AwayScorers:
            for p in m.formatIncidents(m.AwayScorers, True).split("\n"):
                i = Incident(player=p, home=False)
                self.awaystack.add_widget(i)


class Incident(BoxLayout):
    """Widget to display match incidents."""
    home = BooleanProperty(True)
    player = StringProperty("")

    def __init_(self, **kwargs):
        super(Incident, self).__init__(**kwargs)
        self.home = kwargs["home"]
        self.player = kwargs["player"]


# Leagues ####################################################################

class LeagueBase(Screen):
    """Base widget for football league summary screen."""
    leaguename = StringProperty("")

    def __init__(self, **kwargs):
        super(LeagueBase, self).__init__(**kwargs)
        self.leagueid = kwargs["league"]
        self.leaguename = "Retrieving league information."
        self.running = False
        self.timer = None
        self.nextupdate = 0
        self.leaguestack = None
        self.newbox = None
        self.leaguebox = self.ids.league_box
        self.spacer = False
        self.h = 0

    def on_enter(self):
        """Works out if we're due an update or not and schedules the refesh as
           appropriate.
        """
        if not self.running:
            Clock.schedule_once(self.getLeagueObject, 0.5)

        tm = time.time()

        if tm > self.nextupdate:
            dt = 0.5
        else:
            dt = self.nextupdate - tm

        self.timer = Clock.schedule_once(self.update, dt)

    def on_leave(self):
        Clock.unschedule(self.timer)

    def getLeagueObject(self, *args):
        """Creates the league object if we don't have one yet."""
        if not self.running:
            self.leagueobject = League(self.leagueid, detailed=False)
            self.running = True
        self.checkscreen()

    def update(self, *args):
        # Reresh the league object data.
        self.leagueobject.Update()

        # Schedule the next update
        if self.leagueobject.HasFinished or not self.leagueobject:
            dt = 60 * 60
        else:
            dt = 30

        self.nextupdate = time.time() + dt
        self.timer = Clock.schedule_once(self.update, dt)

        # Update the screen.
        self.checkscreen()

    def checkscreen(self):
        """Updates the screen depending on the state of the league object."""
        # If there are league matches, clear the screen
        if self.leagueobject:
            self.leaguename = self.leagueobject.LeagueName
            if self.newbox:
                self.newbox.clear_widgets()
            else:
                self.newbox = BoxLayout(orientation="vertical",
                                        size_hint_y=0.8)
                self.leaguebox.add_widget(self.newbox)

            # Get the stack of league matches
            self.leaguestack = self.createStack()

            # And work out how to place it in the middle of the screen.
            if self.spacer:
                sph = ((self.parent.height * .8) - self.h) / 2.0
                self.newbox.add_widget(Widget(size_hint=(1, None), height=sph))

            self.newbox.add_widget(self.leaguestack)

            if self.spacer:
                self.newbox.add_widget(Widget(size_hint=(1, None), height=sph))

        # No league matches
        else:
            if self.newbox:
                self.leaguebox.remove_widget(self.newbox)
            self.leaguename = "No league matches found."

    def createStack(self):
        """Works out how to display the league matches.

        Layout depends on the number of matches found.
        """
        matches = self.leagueobject.LeagueMatches
        x = len(matches)

        # Single column, no scrolling
        if x <= 10:
            self.spacer = True
            w = 1
            scroll = False
            self.h = 42 * x

        # Dual columns, no scrolling
        elif x <= 20:
            self.spacer = False
            w = 0.5
            scroll = False
            self.h = round(x/2.0) * 42

        # Dual columns, scrolling
        else:
            self.spacer = False
            w = 0.5
            scroll = True
            self.h = round(x/2.0) * 42

        # Create a stack layout
        stack = StackLayout(orientation="tb-lr",
                            size_hint_y=None,
                            height=self.h)

        stack.bind(minimum_height=stack.setter('height'))

        # Add the league matches to it.
        for l in matches:
            lg = LeagueGame(match=l, size_hint=(w, None))
            stack.add_widget(lg)

        # Create a scroll view
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(stack)

        return scroll

    def notifyEvent(self, event_type=EVT_HALF_TIME):
        """Animation for incident notifications."""
        t = EVT_LOOKUP[event_type]
        g = FootballEvent(eventtext=t["text"])
        self.ids.base_float.add_widget(g)
        in_anim = Animation(font_size=t["size"], d=1, t="out_back")
        in_anim &= Animation(bgcolour=[0, 0, 0, 1], d=1, t="out_expo")
        out_anim = Animation(font_size=0, d=1, t="out_back")
        out_anim &= Animation(bgcolour=[0, 0, 0, 0], d=1, t="out_expo")
        anim = in_anim + Animation(d=2.) + out_anim
        anim.bind(on_complete=self.notifyComplete)
        anim.start(g)

    def notifyComplete(self, anim, widget):
        anim.unbind()
        self.ids.base_float.remove_widget(widget)

    def showDetail(self, mo):
        pass


class LeagueGame(ButtonBehavior, BoxLayout):
    """Widget for league game."""
    hometeam = StringProperty("")
    awayteam = StringProperty("")
    homescore = StringProperty("")
    awayscore = StringProperty("")
    status = StringProperty("")
    homebg = ListProperty([0.1, 0.1, 0.1, 1])
    awaybg = ListProperty([0.1, 0.1, 0.1, 1])

    def __init__(self, **kwargs):
        super(LeagueGame, self).__init__(**kwargs)
        m = kwargs["match"]
        self.hometeam = m.HomeTeam
        self.awayteam = m.AwayTeam
        self.homescore = str(m.HomeScore)
        self.awayscore = str(m.AwayScore)
        self.status = m.Status
        self.mo = m

        # Format score background depending on status.
        if not m.HasStarted:
            self.homebg = self.awaybg = MATCH_COLOURS["FIXTURE"]
        else:
            statuscol = MATCH_COLOURS.get(m.Status, MATCH_COLOURS["FIXTURE"])
            self.homebg = self.awaybg = statuscol

        if m.HomeGoal:
            self.homebg = MATCH_COLOURS["GOAL"]
        elif m.AwayGoal:
            self.awaybg = MATCH_COLOURS["GOAL"]

    def on_press(self):
        """Handler for when widget is clicked.

        Triggers detailed overlay.
        """
        scr = self.parent.parent.parent.parent.parent
        ld = LeagueDetail(mo=self.mo)
        scr.add_widget(ld)


class LeagueDetail(ButtonBehavior, BoxLayout):
    """Widget to show detailed info of league match."""
    hometeam = StringProperty("Loading..")
    awayteam = StringProperty("Loading..")
    homescore = StringProperty("0")
    awayscore = StringProperty("0")
    homescorers = StringProperty("Loading..")
    awayscorers = StringProperty("Loading..")
    matchtime = StringProperty("L")
    homebg = ListProperty([0.1, 0.1, 0.1, 1])
    awaybg = ListProperty([0.1, 0.1, 0.1, 1])

    def __init__(self, **kwargs):
        super(LeagueDetail, self).__init__(**kwargs)
        self.mo = kwargs["mo"]
        self.getDetail()
        m = self.mo
        self.hometeam = m.HomeTeam
        self.awayteam = m.AwayTeam
        self.homescore = str(m.HomeScore)
        self.awayscore = str(m.AwayScore)
        self.matchtime = m.MatchTime
        self.homescorers = m.formatIncidents(m.HomeScorers, True)
        self.awayscorers = m.formatIncidents(m.AwayScorers, True)

        # Format background colour of score depending on status.
        if not m.HasStarted:
            self.homebg = self.awaybg = MATCH_COLOURS["FIXTURE"]
        else:
            statuscol = MATCH_COLOURS.get(m.Status, MATCH_COLOURS["FIXTURE"])
            self.homebg = self.awaybg = statuscol

        if m.HomeGoal:
            self.homebg = MATCH_COLOURS["GOAL"]
        elif m.AwayGoal:
            self.awaybg = MATCH_COLOURS["GOAL"]

    def getDetail(self):
        """Takes the current match object and requests additional detail."""
        self.mo.detailed = True
        self.mo.Update()


class FootballErrorScreen(Screen):
    errormessage = ("Football Scores\n\nUh oh... Something's gone wrong.\n"
                    "Have you entered details of teams or leagues to"
                    " follow?\nSee the README file in the football folder for"
                    " further information.")


class FootballScreen(Screen):
    """Base screen for football scores."""
    def __init__(self, **kwargs):
        super(FootballScreen, self).__init__(**kwargs)
        self.params = kwargs["params"]
        self.setup()
        self.flt = self.ids.football_float
        self.flt.remove_widget(self.ids.football_base_box)
        self.fscrmgr = self.ids.football_scrmgr
        self.running = False
        self.scrid = 0

    def setup(self):
        """Creates a list of screens requested by the user."""
        self.myteams = self.params["teams"]
        self.myleagues = self.params["leagues"]
        self.myscreens = self.myteams[:] + self.myleagues[:]
        self.running = False

    def on_enter(self):
        """Creates football match and/or league screens depending on user's
           requirements.
        """
        if not self.running:
            for team in self.myteams:
                self.fscrmgr.add_widget(FootballBase(team=team, name=team))
            for league in self.myleagues:
                self.fscrmgr.add_widget(LeagueBase(league=league, name=league))
            if not self.myscreens:
                er = FootballErrorScreen(name="ErrorScreen")
                self.myscreens.append("ErrorScreen")
                self.fscrmgr.add_widget(er)

            self.running = True

        else:
            # Fixes bug where nested screens don't have "on_enter" or
            # "on_leave" methods called.
            for c in self.fscrmgr.children:
                if c.name == self.fscrmgr.current:
                    c.on_enter()

    def on_leave(self):
        # Fixes bug where nested screens don't have "on_enter" or
        # "on_leave" methods called.
        for c in self.fscrmgr.children:
            if c.name == self.fscrmgr.current:
                c.on_leave()

    def next_screen(self, rev=True):
        a = self.myscreens
        n = -1 if rev else 1
        self.scrid = (self.scrid + n) % len(a)
        self.fscrmgr.transition.direction = "up" if rev else "down"
        self.fscrmgr.current = a[self.scrid]
