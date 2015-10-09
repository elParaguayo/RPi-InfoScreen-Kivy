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


class SqueezePlayerItem(ButtonBehavior, BoxLayout):
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
        self.artwork = self.art # art if self.current else

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
    icon_path = StringProperty("")
    vol = BoundedNumericProperty(10, min=0, max=100, error=10)



    def __init__(self, *args, **kwargs):
        super(SqueezeNowPlaying, self).__init__(*args, **kwargs)
        self.icon_path = os.path.join(kwargs["plugindir"], "icons")
        self.cur_track = kwargs["cur_track"]
        self.player = kwargs["player"]
        #self.playlist = kwargs["playlist"]
        self.currentArt = self.cur_track["art"]
        self.web = "http://{host}:{webport}".format(**kwargs)
        self.art = self.ids.squeeze_art
        self.updatePlaylist(kwargs["playlist"])
        self.pl_vol = -1
        self.sq_root = kwargs["sq_root"]
        self.vol = int(float(self.player.get_volume()))

    def update(self, cur_track):
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

    def updatePlayTime(self, cur_track):
        el = cur_track["elapsed"]
        du = cur_track["duration"]
        pr = el/du
        em, es = divmod(el, 60)
        dm, ds = divmod(du, 60)
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

    def vol_change(self, value):
        if self.pl_vol != value:
            value = float(value)
            self.pl_vol = value
            self.player.set_volume(self.pl_vol)

    def play(self, *args):
        self.player.play()

    def pause(self, *args):
        self.player.pause()

    def stop(self, *args):
        self.player.stop()

    def prev(self, *args):
        self.player.prev()

    def next(self, *args):
        self.player.next()

class SqueezePlayerScreen(Screen):
    pl = StringProperty("")
    cur_track = DictProperty({"name": "Loading..."})
    currentArt = StringProperty("images/10x10_transparent.png")


    def __init__(self, **kwargs):
        super(SqueezePlayerScreen, self).__init__(**kwargs)
        scr = sys.modules[self.__class__.__module__].__file__
        self.plugindir = os.path.dirname(scr)
        p = kwargs["params"]
        self.host = p["host"]["address"]
        self.webport = p["host"]["webport"]
        self.telnetport = p["host"]["telnetport"]
        art = "http://{}:{}/music/current/cover.jpg".format(self.host,
                                                            self.webport)

        self.currentArt = art
        self.cur_track["name"] = "Loading..."
        self.backendonline = False
        self.lms = None
        self.squeezeplayers = []
        self.cur_player = None
        self.now_playing = None
        self.bx = self.ids.squeeze_box
        self.currenttrack = None
        self.ct = {}
        self.inactive = True
        self.timer = None

    def on_enter(self):
        # self.lms = self.lmsLogon(self.host, self.telnetport)
        # self.squeezePlayer = self.getSqueezePlayers(self.lms)[0]
        # self.pl = self.squeezePlayer.get_name()
        self.timer = Clock.schedule_interval(self.update, 2)

    def on_leave(self):
        Clock.unschedule(self.timer)

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
        pl = {x.get_ref():x for x in self.squeezeplayers}

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
        # track["art"] = "{}#{}{}".format(self.currentArt,
        #                                 track["artist"],
        #                                 track["album"])
        track["elapsed"] = self.squeezePlayer.get_time_elapsed()
        track["duration"] = self.squeezePlayer.get_track_duration()
        self.currentArt = track["art"]
        return track

    def getNextTrackInfo(self, playlist, pos):
        ntracks = []

        for i in range(2):
            try:
                trackdetail = {}
                trackdetail['id'] = int(playlist[pos+i+1]['id'])
                trackdetail['trackname'] = str(playlist[pos+i+1]['title'])
                trackdetail['artist'] = str(playlist[pos+i+1]['artist'])
                ntracks.append(trackdetail)
            except:
                continue

        return ntracks

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

    def drawPlayerScreen(self):
        if self.inactive:
            self.bx.clear_widgets()

        pl = self.squeezePlayer.playlist_get_info()
        self.playlistposition = int(self.squeezePlayer.playlist_get_position())
        plyl = {"pos": self.playlistposition,
                "playlist": pl}

        if self.now_playing and pl != self.playlist:
            self.now_playing.updatePlaylist(plyl)

        self.playlist = pl

        if self.currentTrackChanged(self.playlist, self.playlistposition):

            self.ct = self.getCurrentTrackInfo(self.playlist,
                                               self.playlistposition)
            self.currenttrack = self.ct["id"]
            ca = "http://{}:{}/music/{}/cover.jpg".format(self.host,
                                                          self.webport,
                                                          self.ct["id"])
            self.currentArt = ca

        if self.nextTrackChanged(self.playlist, self.playlistposition):
            pass

        self.ct["elapsed"] = self.squeezePlayer.get_time_elapsed()


        if self.now_playing:
            self.now_playing.update(self.ct)
        else:
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
        # dd = DropDown()
        # for sp in self.squeezeplayers:
        #     btn = Button(text=sp.get_name(), size_hint_y=None, height=25)
        #     btn.bind(on_release=lambda btn: dd.select(btn.text))
        #     dd.add_widget(btn)
        #
        # mainbutton = Button(text='Hello', size_hint=(None, None), size=(80,30), pos=(500,300))
        # mainbutton.bind(on_release=dd.open)
        # dd.bind(on_select=lambda instance, x: setattr(mainbutton, 'text', x))
        # self.add_widget(dd)
        if self.now_playing:
            self.now_playing.update_players(sps)



    def update(self, *args):
        new_pls = False
        sps = []

        self.lms = self.lmsLogon(self.host, self.telnetport)

        if self.lms:
            sps = self.getSqueezePlayers(self.lms)
            
            if sps and (sps != self.squeezeplayers):
                new_pls = True
            self.squeezeplayers = sps

        else:
            self.drawNoServer()
            self.inactive = True

        if sps:
            self.squeezePlayer = self.getPlayer(self.cur_player)
            self.drawPlayerScreen()
            self.inactive = False
            if new_pls:
                self.drawSqueezePlayers(self.squeezeplayers)
        else:
            self.drawNoPlayer()
            self.inactive = True
