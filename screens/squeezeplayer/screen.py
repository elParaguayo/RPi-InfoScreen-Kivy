import os
import inspect
import sys

from kivy.clock import Clock
from kivy.properties import (StringProperty,
                             BooleanProperty,
                             DictProperty,
                             ObjectProperty,
                             BoundedNumericProperty)
from kivy.uix.accordion import Accordion, AccordionItem
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from kivy.uix.dropdown import DropDown

from core.bgimage import BGImageButton

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pylms.server import Server as LMSServer
from pylms.player import Player as LMSPlayer
from pylms.callback_server import CallbackServer as LMSCallbackServer


class SqueezePlayerItem(ButtonBehavior, BoxLayout):
    """Class to represent a squeeze player instance on the network."""
    status = StringProperty("images/10x10_transparent.png")
    playername = StringProperty("")
    current = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(SqueezePlayerItem, self).__init__(**kwargs)
        self.player = kwargs["player"]
        self.basescreen = kwargs["base"]
        self.playername = self.player.get_name()
        self.ref = self.player.get_ref()

    def on_press(self, *args):
        """Tells the main screen that we want to control the selected
           player.
        """
        self.basescreen.changePlayer(self.ref)


class SqueezePlaylistItem(ButtonBehavior, BoxLayout):
    artwork = StringProperty("images/10x10_transparent.png")
    artist = StringProperty("Loding playlist")
    trackname = StringProperty("Loding playlist")
    posnum = StringProperty("")
    current = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(SqueezePlaylistItem, self).__init__(**kwargs)
        self.currentart = kwargs["currentart"]
        self.art = kwargs["art"]
        self.artist = kwargs["artist"]
        self.trackname = kwargs["trackname"]
        self.posnum = str(kwargs["posnum"])
        self.player = kwargs["player"]
        self.np = kwargs["np"]
        self.updatePlaylistPosition(self.np.cur_track["pos"], kwargs["art"])

    def updatePlaylistPosition(self, playpos, art):
        self.current = int(self.posnum) == playpos
        self.artwork = self.art

    def on_press(self, *args):
        self.player.playlist_play_index((int(self.posnum) - 1))


class SqueezeNowPlaying(Accordion):
    cur_track = DictProperty({"name": "Loading...",
                              "artist": "Loading..."})

    sv_playlist = ObjectProperty(None)
    sv_players_list = ObjectProperty(None)
    playprog = ObjectProperty(None)
    playtime = StringProperty("00:00")
    endtime = StringProperty("00:00")
    pause_icon = StringProperty("sq_play.png")
    icon_path = StringProperty("")
    vol = BoundedNumericProperty(10, min=0, max=100, error=10)
    sqbtn_pause = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        super(SqueezeNowPlaying, self).__init__(*args, **kwargs)
        self.icon_path = os.path.join(kwargs["plugindir"], "icons")
        self.cur_track = kwargs["cur_track"]
        self.player = kwargs["player"]
        self.currentArt = self.cur_track["art"]
        self.web = "http://{host}:{webport}".format(**kwargs)
        self.art = self.ids.squeeze_art
        self.updatePlaylist(kwargs["playlist"])
        self.pl_vol = -1
        self.sq_root = kwargs["sq_root"]
        self.vol = int(float(self.player.get_volume()))
        self.paused = None
        self.checkStatus()
        self.updatePlayTime(self.cur_track)
        self.set_clocks()
        self.running = True

    def quit(self):
        """Disables the intervals as they're not needed when the screen is
           inactive.
        """
        Clock.unschedule(self.prog_timer)
        Clock.unschedule(self.check_timer)
        self.prog_timer = None
        self.check_timer = None

    def start(self):
        """Restart the schedules."""
        if self.running:
            self.set_clocks()

    def set_clocks(self):
        self.prog_timer = Clock.schedule_interval(self.addTime, 1)
        self.check_timer = Clock.schedule_interval(self.checkStatus, 5)

    def addTime(self, *args):
        """Adds 1 second to the elapsed play time every second. Doing this
           means we don't have to constantly poll the server for updates.
        """
        if not self.paused:
            self.elapsed += 1
            self.updatePlayTime()

    def checkStatus(self, *args):
        """If there's some variance in Kivy's internal clock then the play time
           can drift from the actual time. This function checks the time
           intermittently and updates accordingly.
        """

        # Sometimes some of the pause callbacks are missed. This is a safety
        # precaustion but should only run if the call back has been missed.
        paused = self.player.get_mode() == "pause"
        if paused != self.paused:
            self.play_pause(paused)

        # This section only runs when the function has been called by the
        # Clock.
        if args:
            self.elapsed = self.player.get_time_elapsed()
            self.updatePlayTime()

    def update(self, cur_track):
        """Updates the player for the information of the currently playing
           track.
        """
        if cur_track["pos"] != self.cur_track["pos"]:
            for c in self.sv_playlist.children:
                c.updatePlaylistPosition(cur_track["pos"], cur_track["art"])
        self.cur_track = cur_track
        self.updatePlayTime(cur_track)
        self.vol = int(float(self.player.get_volume()))

    def update_players(self, sps):
        self.sv_players_list.clear_widgets()
        for sp in sps:
            player = SqueezePlayerItem(player=sp, base=self.sq_root)
            self.sv_players_list.add_widget(player)

    def play_pause(self, paused):
        reload_image = paused != self.paused
        self.paused = paused
        if paused:
            self.pause_icon = "sq_play.png"
        else:
            self.pause_icon = "sq_pause.png"

        # if reload_image:
        #     self.sqbtn_pause.reload()

    def updatePlayTime(self, cur_track=None):
        if cur_track:
            self.elapsed = cur_track["elapsed"]
            self.duration = cur_track["duration"]
        pr = self.elapsed / self.duration
        em, es = divmod(self.elapsed, 60)
        dm, ds = divmod(self.duration, 60)
        self.playtime = "{0:.0f}:{1:02.0f}".format(em, es)
        self.endtime = "{0:.0f}:{1:02.0f}".format(dm, ds)
        self.playprog.value = pr

    def updatePlaylist(self, pl):
        self.playlist = pl
        pos = self.playlist["pos"]
        plyl = self.playlist["playlist"]
        self.sv_playlist.clear_widgets()

        for i, tr in enumerate(plyl):
            art = "{}/music/{}/cover.jpg".format(self.web, tr["id"])
            artist = tr["artist"]
            trackname = tr["title"]
            posnum = str(1 + i)
            item = SqueezePlaylistItem(art=art,
                                       artist=artist,
                                       trackname=trackname,
                                       posnum=posnum,
                                       player=self.player,
                                       currentart=self.currentArt,
                                       np=self)
            self.sv_playlist.add_widget(item)

    def vol_change(self, value, update=True):
        if self.pl_vol != value:
            value = float(value)
            self.pl_vol = value
            if update:
                self.player.set_volume(self.pl_vol)
            else:
                self.vol = value

    def toggle(self, *args):
        self.player.toggle()

    def stop(self, *args):
        self.player.stop()

    def prev(self, *args):
        self.player.prev()

    def next(self, *args):
        self.player.next()


class SqueezePlayerScreen(Screen):
    """Main screen object for SqueezePlayer.

       This screen handles the main initial contact with the server and sets
       up child objects as required.
    """
    pl = StringProperty("")
    cur_track = DictProperty({"name": "Loading..."})
    currentArt = StringProperty("images/10x10_transparent.png")

    def __init__(self, **kwargs):
        super(SqueezePlayerScreen, self).__init__(**kwargs)

        # We need the path to this folder to load icons
        scr = sys.modules[self.__class__.__module__].__file__
        self.plugindir = os.path.dirname(scr)

        # Set variables based on the parameters in the config file
        p = kwargs["params"]
        self.host = p["host"]["address"]
        self.webport = p["host"]["webport"]
        self.telnetport = p["host"]["telnetport"]

        # Not sure we need this now...
        art = "http://{}:{}/music/current/cover.jpg".format(self.host,
                                                            self.webport)

        self.currentArt = art

        self.cur_track["name"] = "Loading..."

        # Get reference to the box layout.
        self.bx = self.ids.squeeze_box

        # Initialise some variables that we'll need later
        self.backendonline = False
        self.lms = None
        self.squeezeplayers = []
        self.cur_player = None
        self.now_playing = None
        self.currenttrack = None
        self.ct = {}
        self.inactive = True
        self.timer = None
        self.cbs = None
        self.sync_groups = []

    def on_enter(self):
        """Need to rewrite this once callback server is implemented."""
        self.timer = Clock.schedule_once(self.update, 0.1)
        if self.now_playing:
            self.now_playing.start()

    def on_leave(self):
        Clock.unschedule(self.timer)
        if self.now_playing:
            self.now_playing.quit()

    def lmsLogon(self, host, port):
        try:
            sc = LMSServer(hostname=host, port=port)
            sc.connect()
        except:
            sc = None
        return sc

    def changePlayer(self, player):
        if player != self.cur_player:
            self.cur_player = player

    def getSqueezePlayers(self, server):
        try:
            sq = server.get_players()
        except:
            sq = None
        return sq

    def getPlayer(self, cur_player):
        pl = {x.get_ref(): x for x in self.squeezeplayers}

        if cur_player in pl:
            return pl[cur_player]

        else:
            return self.squeezeplayers[0]

    # Only refresh all data if track has changed
    def currentTrackChanged(self, playlist, pos):
        try:
            if playlist[pos]['id'] == self.currenttrack:
                return False
            else:
                return True
        except:
            return True

    # Has the next track changed
    def nextTrackChanged(self, playlist, pos):
        try:
            if ((playlist[pos + 1]['id'] == self.nexttracks[0]['id']) or
                    (playlist[pos + 2]['id'] == self.nexttracks[1]['id'])):
                return False
            else:
                return True
        except:
            return True

    # Get current track information
    def getCurrentTrackInfo(self, playlist, pos):
        track = {}

        track["id"] = int(playlist[pos]['id'])
        track["name"] = self.squeezePlayer.get_track_title()
        track["artist"] = self.squeezePlayer.get_track_artist()
        track["album"] = self.squeezePlayer.get_track_album()
        track["pos"] = int(self.squeezePlayer.playlist_get_position()) + 1
        track["art"] = "http://{}:{}/music/{}/cover.jpg".format(self.host,
                                                                self.webport,
                                                                track["id"])
        track["elapsed"] = self.squeezePlayer.get_time_elapsed()
        track["duration"] = self.squeezePlayer.get_track_duration()
        self.currentArt = track["art"]
        return track

    def getCallbackServer(self):

        cbs = LMSCallbackServer(hostname=self.host, port=self.telnetport)
        cbs.add_callback(cbs.VOLUME_CHANGE, self.volume_change)
        cbs.add_callback(cbs.CLIENT_ALL, self.client_event)
        cbs.add_callback(cbs.PLAY_PAUSE, self.play_pause)
        cbs.add_callback(cbs.PLAYLIST_CHANGED, self.playlist_changed)
        cbs.add_callback(cbs.PLAYLIST_CHANGE_TRACK, self.track_changed)
        cbs.daemon = True
        return cbs

    def getCallbackPlayer(self, event):
        return event.split(" ")[0]

    def cur_or_sync(self, ref):
        if ref == self.cur_player:
            return True

        else:
            for gr in self.sync_groups:
                if ref in gr and self.cur_player in gr:
                    return True

        return False

    def volume_change(self, event=None):
        """Method to handle callback for volume change event.

           Event should be:
             [player_ref] mixer volume [vol_amount]
        """
        if self.getCallbackPlayer(event) == self.cur_player:
            vol = self.squeezePlayer.get_volume()
            self.now_playing.vol_change(vol, False)

    def client_event(self, event=None):
        """Method to handle callback for client event.

           Expected events are:
             [player_ref] new
             [player_ref] disconnect
             [player_ref] reconnect
        """
        pass

    def play_pause(self, event=None):
        """Method to handle callback for play pause event.

           Expected event is:
             [player_ref] playlist pause 0|1
        """
        if self.cur_or_sync(self.getCallbackPlayer(event)):
            paused = (event.split()[3] == "1")
            self.now_playing.play_pause(paused)

    def playlist_changed(self, event=None):
        """Method to handle callback for a playlist change.

           Expected events are:
             [player_ref] playlist addtracks
             [player_ref] playlist loadtracks
             [player_ref] playlist delete
        """
        if self.cur_or_sync(self.getCallbackPlayer(event)):
            self.now_playing.updatePlaylist(self.getCurrentPlaylist())

    def track_changed(self, event=None):
        """Method to handle track change callback.

           Expected event:
             [player_ref] playlist newsong [playlist_position]
        """
        if self.cur_or_sync(self.getCallbackPlayer(event)):
            self.playlist = self.squeezePlayer.playlist_get_info()
            pos = int(self.squeezePlayer.playlist_get_position())
            self.playlistposition = pos
            plyl = {"pos": self.playlistposition,
                    "playlist": self.playlist}
            self.ct = self.getCurrentTrackInfo(self.playlist,
                                               self.playlistposition)
            self.now_playing.update(self.ct)

    def drawNoServer(self):
        self.bx.clear_widgets()
        self.now_playing = None

        lb = Label(text="No Squeezeserver found. Please check your settings.")
        self.bx.add_widget(lb)

    def drawNoPlayer(self):
        self.bx.clear_widgets()
        self.now_playing = None

        lb = Label(text="There are no players connected to your server.")
        self.bx.add_widget(lb)

    def checkForPlayers(self):
        if self.inactive:
            self.bx.clear_widgets()

        self.squeezeplayers = self.getSqueezePlayers(self.lms)

        if self.squeezeplayers:
            self.squeezePlayer = self.getPlayer(self.cur_player)
            self.cur_player = self.squeezePlayer.get_ref()
            self.sync_groups = self.lms.get_sync_groups()
            self.inactive = False
            self.createPlayerScreen()
            self.drawSqueezePlayers(self.squeezeplayers)

        else:
            self.drawNoPlayer()
            self.inactive = True

    def getCurrentPlaylist(self):
        self.playlist = self.squeezePlayer.playlist_get_info()
        self.playlistposition = int(self.squeezePlayer.playlist_get_position())
        plyl = {"pos": self.playlistposition,
                "playlist": self.playlist}
        return plyl

    def createPlayerScreen(self):
        plyl = self.getCurrentPlaylist()

        self.ct = self.getCurrentTrackInfo(self.playlist,
                                           self.playlistposition)
        self.currenttrack = self.ct["id"]
        ca = "http://{}:{}/music/{}/cover.jpg".format(self.host,
                                                      self.webport,
                                                      self.ct["id"])
        self.currentArt = ca

        self.now_playing = SqueezeNowPlaying(cur_track=self.ct,
                                             height=480,
                                             size_hint_y=None,
                                             player=self.squeezePlayer,
                                             playlist=plyl,
                                             host=self.host,
                                             webport=self.webport,
                                             plugindir=self.plugindir,
                                             sq_root=self)
        self.bx.add_widget(self.now_playing)
        for c in self.now_playing.children:
            if c.title == "Now Playing":
                c.collapse = False

    def drawSqueezePlayers(self, sps):
        if self.now_playing:
            self.now_playing.update_players(sps)

    def update(self, *args):

        new_pls = False
        sps = []
        interval = 5

        # Check if there is a CallbackServer instance.
        if not self.cbs:

            # No CallbackServer. Can we connect to LMS?
            self.lms = self.lmsLogon(self.host, self.telnetport)

            # If so then we can set up a few things
            if self.lms:

                # Create a CallbackServer instance...
                self.cbs = self.getCallbackServer()

                # ...and start it running
                self.cbs.start()

                # If we don't have a Now Playing screen initialised
                if not self.now_playing:

                    # then we need to make one
                    self.checkForPlayers()

                    # We've got a callback server running so we don't need
                    # a regular interval now but we may want to test the
                    # connection every 30 seconds or so
                    interval = 30

            else:

                # There's no active server found
                self.drawNoServer()
                self.inactive = True

        Clock.schedule_once(self.update, interval)
