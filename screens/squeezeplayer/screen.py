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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivy.uix.slider import Slider
from kivy.uix.dropdown import DropDown

from core.bgimage import BGImageButton
from core.bglabel import BGLabelButton

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pylms.server import Server as LMSServer
from pylms.player import Player as LMSPlayer
from pylms.callback_server import CallbackServer as LMSCallbackServer
from artworkresolver import ArtworkResolver

# TAGLIST - sets the relevant fields we need for our playlist queries:
# a - artist	Artist name.
# c - coverid	coverid to use when constructing an artwork URL, such as
#               /music/$coverid/cover.jpg
# d - duration	Song duration in seconds.
# j - coverart	1 if coverart is available for this song. Not listed otherwise.
# K - artwork_url	A full URL to remote artwork. Only available for certain
#                   plugins such as Pandora and Rhapsody.
# l - album	Album name. Only if known.
# x - remote	If 1, this is a remote track.
TAGLIST = ["a", "c", "d", "j", "K", "l", "x"]


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

    def checkCurrent(self, current):
        """Sets the 'current' property to True if the current player is the
           same as the instance reference.
        """
        self.current = self.ref == current

    def on_press(self, *args):
        """Tells the main screen that we want to control the selected
           player.
        """
        self.basescreen.changePlayer(self.ref)


class SqueezePlaylistItem(ButtonBehavior, BoxLayout):
    """Class object for displaying playlist items."""
    artwork = StringProperty("images/10x10_transparent.png")
    artist = StringProperty("Loding playlist")
    trackname = StringProperty("Loding playlist")
    posnum = StringProperty("")
    current = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(SqueezePlaylistItem, self).__init__(**kwargs)
        # Create references to underlying objects
        self.player = kwargs["player"]
        self.np = kwargs["np"]

        # Set the display properties
        try:
            self.artwork = kwargs["track"]["art"]
            self.artist = kwargs["track"]["artist"]
            self.trackname = kwargs["track"]["title"]
            self.posnum = str(kwargs["track"]["pos"])

        # Sometimes the server hasn't loaded all the metadata yet
        except KeyError:

            # Create a dummy entry in the playlist
            self.artwork = "10x10_transparent.png"
            self.artist = "Loading..."
            self.trackname = "Loading..."
            self.posnum = "0"

            # but schedule a refresh of the playlist
            Clock.schedule_once(self.np.refresh_playlist, 2)

        # Check if we're the current track
        self.updatePlaylistPosition(self.np.cur_track["pos"])

    def updatePlaylistPosition(self, playpos):
        self.current = int(self.posnum) == playpos

    def on_press(self, *args):
        self.player.playlist_play_index((int(self.posnum) - 1))


class SqueezeNowPlaying(Accordion):
    """Class object to display the Now Playing information.

       Widget is split into 3 parts:
         Players:     Shows available Squeeze players
         Now Playing: Shows info about the currently playing track
         Playlist:    Shows the current playlist
    """
    # Dict property to hold the track information
    cur_track = DictProperty({"name": "Loading...",
                              "artist": "Loading..."})

    # Properties for two scrollviews
    sv_playlist = ObjectProperty(None)
    sv_players_list = ObjectProperty(None)

    # Progress bar, elapsed and total track time
    playprog = ObjectProperty(None)
    playtime = StringProperty("00:00")
    endtime = StringProperty("00:00")

    # Play/Pause button changes depending on state, so give an initial value
    sqbtn_pause = ObjectProperty(None)
    pause_icon = StringProperty("sq_play.png")
    icon_path = StringProperty("")

    # Limit the volume between 0 and 100
    vol = BoundedNumericProperty(10, min=0, max=100, error=10)

    def __init__(self, *args, **kwargs):
        super(SqueezeNowPlaying, self).__init__(*args, **kwargs)
        self.sq_root = kwargs["sq_root"]

        # Create a reference to the artwork resolver
        self.awr = self.sq_root.awr
        self.icon_path = os.path.join(kwargs["plugindir"], "icons")
        self.cur_track = kwargs["cur_track"]
        self.player = kwargs["player"]
        self.pl_vol = -1

        # Draw the playlist
        self.updatePlaylist(kwargs["playlist"])

        # Get the volume of current player
        self.vol = int(float(self.player.get_volume()))

        # Get the status of the player
        self.paused = None
        self.checkStatus()
        self.updatePlayTime(self.cur_track)

        # Set the timers
        self.set_clocks()

        # Set flags to say we're up and running
        self.running = True
        self.active = True

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
        if not self.paused and self.active:
            self.elapsed += 1
            self.updatePlayTime()

    def checkStatus(self, *args):
        """If there's some variance in Kivy's internal clock then the play time
           can drift from the actual time. This function checks the time
           intermittently and updates accordingly.
        """
        # Sometimes some of the pause callbacks are missed. This is a safety
        # precaustion but should only run if the call back has been missed.
        paused = self.player.get_mode() != "play"
        if paused != self.paused:
            self.play_pause(paused)

        # This section only runs when the function has been called by the
        # Clock.
        if args:
            try:
                self.elapsed = self.player.get_time_elapsed()
            except ValueError:
                self.elapsed = 0
                self.paused = True

            self.updatePlayTime()

    def update(self, cur_track):
        """Updates the player for the information of the currently playing
           track.
        """
        # If it's a new track then we need to update the playlist to make
        # sure the currently playing track is highlighted.
        if cur_track["pos"] != self.cur_track["pos"]:
            for c in self.sv_playlist.children:

                # This will raise an error when it tries to update the
                # "Refresh" button, so let's make sure we catch it.
                try:
                    c.updatePlaylistPosition(cur_track["pos"])
                except AttributeError:
                    pass

        # Set the local flag (so we can check it later)
        self.cur_track = cur_track

        # Update the track time info
        self.updatePlayTime(cur_track)

        # No harm checking the volume too
        self.vol = int(float(self.player.get_volume()))

    def update_players(self, sps):
        """Method to populate the "Players" section of the screen."""
        # Remove old players
        self.sv_players_list.clear_widgets()

        # Get the reference of the current player
        current = self.sq_root.cur_player

        # Loop over available players
        for sp in sps:

            # Create a player item object
            player = SqueezePlayerItem(player=sp, base=self.sq_root)

            # Check if it's current (so it will be higlighted)
            player.checkCurrent(current)

            # Add it to the screen
            self.sv_players_list.add_widget(player)

    def play_pause(self, paused):
        """Method to change the play pause icon as appropriate."""
        self.paused = paused
        if paused:
            self.pause_icon = "sq_play.png"
        else:
            self.pause_icon = "sq_pause.png"

    def updatePlayTime(self, cur_track=None):
        """Method to format and display track time."""
        # If we've got a new track then we need to reset some variables
        if cur_track:
            self.elapsed = cur_track["elapsed"]
            self.duration = cur_track["duration"]

        # Calculate the % of track played
        pr = self.elapsed / self.duration

        # Split the times into minutes and seconds...
        em, es = divmod(self.elapsed, 60)
        dm, ds = divmod(self.duration, 60)

        # ...and display the values
        self.playtime = "{0:.0f}:{1:02.0f}".format(em, es)
        self.endtime = "{0:.0f}:{1:02.0f}".format(dm, ds)
        self.playprog.value = pr

    def btn_refresh_playlist(self):
        """Creates a Refresh button for the playlist screen and binds it
           to the refresh_playlist method.
        """
        btn = BGLabelButton(text="Refresh Playlist",
                            size=(780,30),
                            size_hint=(None, None),
                            bgcolour=[0, 0, 0, 0.5])
        btn.bind(on_press=self.refresh_playlist)

        return btn

    def refresh_playlist(self, *args):
        """Requests a refresh of the playlist."""
        # We need to fake an event for the current player.
        event = "{} playlist".format(self.player.get_ref())
        self.sq_root.playlist_changed(event)


    def updatePlaylist(self, pl):
        """Method to display playlist for current player."""
        # Get the playlist info
        self.playlist = pl
        pos = self.playlist["pos"]
        plyl = self.playlist["playlist"]

        # Clear the playlist
        self.sv_playlist.clear_widgets()

        self.sv_playlist.add_widget(self.btn_refresh_playlist())

        # Loop over the playlist
        for i, tr in enumerate(plyl):

            # Set the artwork and position values
            tr["art"] = self.awr.getURL(tr)
            tr["pos"] = i + 1

            # Create the playlist item object
            item = SqueezePlaylistItem(track=tr,
                                       player=self.player,
                                       np=self)

            # add it to the screen
            self.sv_playlist.add_widget(item)

    def vol_change(self, value, update=True):
        """Method or handling volume changes."""
        # If the volume has changed
        if self.pl_vol != value:

            # display the change
            value = float(value)
            self.pl_vol = value

            # If we've changed volume, then we need to update the player
            if update:
                self.player.set_volume(self.pl_vol)

            # but if the player changed, then we need to update the slider
            else:
                self.vol = value

    # Button press events to send commands to the player
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
        self.cur_track["name"] = "Loading..."

        # Get reference to the box layout.
        self.bx = self.ids.squeeze_box

        # Create an object to handle retrieving artwork URLs
        self.awr = ArtworkResolver(host=self.host,
                                   port=self.webport,
                                   default="images/10x10_transparent.png")

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
        self.checker = None

    def on_enter(self):
        """Start the screen running."""
        self.timer = Clock.schedule_once(self.update, 0.1)
        if self.now_playing:
            self.now_playing.start()

    def on_leave(self):
        """Stop the screen."""
        Clock.unschedule(self.timer)
        if self.now_playing:
            self.now_playing.quit()

    def lmsLogon(self, host, port):
        """Log on to the Logitect Server and return a Server object."""
        try:
            sc = LMSServer(hostname=host, port=port)
            sc.connect()
        except:
            sc = None
        return sc

    def changePlayer(self, player):
        """Method to change the current player and update the screen."""
        if player != self.cur_player:
            self.cur_player = player
            self.squeezePlayer = self.getPlayer(self.cur_player)
            self.now_playing.player = self.squeezePlayer
            self.playlist_changed()
            self.track_changed()
            self.now_playing.update_players(self.squeezeplayers)

    def getSqueezePlayers(self, server):
        """Method to return list of currently active players."""
        try:
            sq = server.get_players()
        except:
            sq = None
        return sq

    def getPlayer(self, cur_player):
        """Method to return the current player. If current player is no longer
           available, this method returns the first available player."""
        pl = {x.get_ref(): x for x in self.squeezeplayers}

        if cur_player in pl:
            return pl[cur_player]

        else:
            return self.squeezeplayers[0]

    # Get current track information
    def getCurrentTrackInfo(self, playlist, pos):
        """Method to update the current playing track info with extra info."""
        track = {}

        # Need to check if there's a playlist, if not this would cause a crash
        if playlist:
            track = playlist[pos]
            track["pos"] = pos + 1
            track["elapsed"] = self.squeezePlayer.get_time_elapsed()

            # Get the artwork - get large version if possible...
            track["art"] = self.awr.getURL(track, size=(800, 800))

            # ...as we'll use as background too
            self.currentArt = track["art"]

        # No playlist so send some dummy info
        else:
            track = {"artist": "Playlist is empty",
                     "album": "Playlist is empty",
                     "title": "Playlist is empty",
                     "elapsed": 0,
                     "duration": 1,
                     "art": "10x10_transparent.png",
                     "pos": 0}

        return track

    def getCallbackServer(self):
        """Method to create and set up a callback server."""
        # Create the server
        cbs = LMSCallbackServer(hostname=self.host, port=self.telnetport)

        # Se up our callbacks
        cbs.add_callback(cbs.VOLUME_CHANGE, self.volume_change)
        cbs.add_callback(cbs.CLIENT_ALL, self.client_event)
        cbs.add_callback(cbs.PLAY_PAUSE, self.play_pause)
        cbs.add_callback(cbs.PLAYLIST_CHANGED, self.playlist_changed)
        cbs.add_callback(cbs.PLAYLIST_CHANGE_TRACK, self.track_changed)
        cbs.add_callback(cbs.SYNC, self.sync_event)

        # Deamonise the object so it dies if the main program dies.
        cbs.daemon = True

        return cbs

    def getCallbackPlayer(self, event):
        """Return the player reference from the callback event."""
        return self.cur_player if event is None else event.split(" ")[0]

    def checkCallbackServer(self, *args):
        """Checks if there's still a connection to the server and deletes
           callback server instance if there isn't.
        """
        self.cbs.check_connection()

    def cur_or_sync(self, ref):
        """Method to determine if the event player is our player or in a sync
           group with our player.
        """
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
             [player_ref] client new
             [player_ref] client disconnect
             [player_ref] client reconnect
             [player_ref] client forget
        """
        # Get the list of current players
        self.squeezeplayers = self.getSqueezePlayers(self.lms)

        # If there are none
        if not self.squeezeplayers:

            # update the screen to tell the user
            self.drawNoPlayer()

        # If our player disconnected, then we need to show a new one
        elif (self.getCallbackPlayer(event) == self.cur_player and
                event.split()[2] == "forget"):

            # get the player and update the screen
            self.squeezePlayer = self.getPlayer(self.cur_player)
            self.changePlayer(self.squeezePlayer.get_ref())

        # If this is the first player connecting
        elif self.squeezeplayers and not self.now_playing:

            # Get the player details
            self.squeezePlayer = self.getPlayer(self.cur_player)
            self.cur_player = self.squeezePlayer.get_ref()

            # Draw the screen
            self.createPlayerScreen()
            self.drawSqueezePlayers(self.squeezeplayers)

        # Another player connected/disconnected
        else:

            # Update the list of players
            self.now_playing.update_players(self.squeezeplayers)

        # Update list of sync groups
        if self.squeezeplayers:
            self.sync_groups = self.lms.get_sync_groups()

    def play_pause(self, event=None):
        """Method to handle callback for play pause event.

           Expected event is:
             [player_ref] playlist pause 0|1
        """
        # We're only interested in our sync group
        if (self.cur_or_sync(self.getCallbackPlayer(event)) and
                self.now_playing):

            # Update the now playing screen
            paused = (event.split()[3] == "1")
            self.now_playing.play_pause(paused)

    def playlist_changed(self, event=None):
        """Method to handle callback for a playlist change.

           Expected events are:
             [player_ref] playlist addtracks
             [player_ref] playlist loadtracks
             [player_ref] playlist delete
        """
        # If our playlist has changed
        if (self.cur_or_sync(self.getCallbackPlayer(event)) and
                self.now_playing):

            # Update the screen
            self.now_playing.updatePlaylist(self.getCurrentPlaylist())

            try:
                ev = event.split()
                if ev[2] == "clear":
                    # We know there are no tracks.
                    self.ct = self.getCurrentTrackInfo({}, 0)
                    self.now_playing.update(self.ct)

            except (IndexError, AttributeError):
                pass

    def track_changed(self, event=None):
        """Method to handle track change callback.

           Expected event:
             [player_ref] playlist newsong [playlist_position]
        """
        # We're only interested in our sync group
        if (self.cur_or_sync(self.getCallbackPlayer(event)) and
                self.now_playing):

            # Work out where we are in the playlist
            pos = int(self.squeezePlayer.playlist_get_position())
            self.playlistposition = pos
            plyl = {"pos": self.playlistposition,
                    "playlist": self.playlist}

            # Get the info for the current track
            self.ct = self.getCurrentTrackInfo(self.playlist,
                                               self.playlistposition)

            # Update the screen
            self.now_playing.update(self.ct)

    def sync_event(self, event=None):
        """Method to handle sync callback.

           Expected event:
             [player_ref] sync
        """
        self.now_playing.updatePlaylist(self.getCurrentPlaylist())
        self.squeezeplayers = self.getSqueezePlayers(self.lms)
        self.sync_groups = self.lms.get_sync_groups()
        pos = int(self.squeezePlayer.playlist_get_position())
        self.playlistposition = pos
        plyl = {"pos": self.playlistposition,
                "playlist": self.playlist}
        self.ct = self.getCurrentTrackInfo(self.playlist,
                                           self.playlistposition)
        self.now_playing.update(self.ct)

    def drawNoServer(self):
        """Method to tell the user that there's no server."""
        # Clear the screen
        self.bx.clear_widgets()
        self.now_playing = None

        # Create the label and display it.
        lb = Label(text="No Squeezeserver found. Please check your settings.")
        self.bx.add_widget(lb)

    def drawNoPlayer(self):
        """Method to tell the user that there are no players."""
        # Clear the screen
        self.bx.clear_widgets()
        self.now_playing = None

        # Create the label and display it.
        lb = Label(text="There are no players connected to your server.")
        self.bx.add_widget(lb)

    def checkForPlayers(self):
        """Before the callback server is running we need to run regular checks
           on the network."""

        # Clear the screen if there was something there
        if self.inactive:
            self.bx.clear_widgets()

        # Get list of players
        self.squeezeplayers = self.getSqueezePlayers(self.lms)

        # If there are players we need to set up our screen
        if self.squeezeplayers:
            self.squeezePlayer = self.getPlayer(self.cur_player)
            self.cur_player = self.squeezePlayer.get_ref()
            self.sync_groups = self.lms.get_sync_groups()
            self.inactive = False
            self.createPlayerScreen()
            self.drawSqueezePlayers(self.squeezeplayers)

        # If not, then we should say there are no players
        else:
            self.drawNoPlayer()
            self.inactive = True

    def getCurrentPlaylist(self):
        """Method to return the playlist for the current player."""
        # Get the playlist and current position
        self.playlist = self.squeezePlayer.playlist_get_info(taglist=TAGLIST)
        try:
            pos = int(self.squeezePlayer.playlist_get_position())
        except ValueError:
            pos = 0

        self.playlistposition = pos

        # Combine into a dict
        plyl = {"pos": self.playlistposition,
                "playlist": self.playlist}

        return plyl

    def createPlayerScreen(self):
        """Method to create the Now Playing screen."""
        # Clear the screen
        self.bx.clear_widgets()

        # Get the playlist
        plyl = self.getCurrentPlaylist()

        # Get the current track info
        self.ct = self.getCurrentTrackInfo(self.playlist,
                                           self.playlistposition)

        # Create the Now Playing object
        self.now_playing = SqueezeNowPlaying(cur_track=self.ct,
                                             height=480,
                                             size_hint_y=None,
                                             player=self.squeezePlayer,
                                             playlist=plyl,
                                             plugindir=self.plugindir,
                                             sq_root=self)

        # Add to the screen
        self.bx.add_widget(self.now_playing)

        # Make sure we start off showing the "Now Playing" section
        for c in self.now_playing.children:
            if c.title == "Now Playing":
                c.collapse = False

    def drawSqueezePlayers(self, sps):
        """Method to trigger the update of the list of squeeze players."""
        if self.now_playing:
            self.now_playing.update_players(sps)

    def update(self, *args):
        """Method to be run on clock interval."""
        # Set default update time
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

                # Set up a timer to check if the server is active
                check = self.checkCallbackServer
                self.checker = Clock.schedule_interval(check, 5)

                # If we don't have a Now Playing screen initialised
                if not self.now_playing:

                    # then we need to make one
                    self.checkForPlayers()

                    # We've got a callback server running so we don't need
                    # a regular interval now but we may want to test the
                    # connection every 15 seconds or so
                    interval = 15

            else:

                # There's no active server found
                self.drawNoServer()
                self.inactive = True

        else:

            # If the callback server has died (e.g. no connection)...
            if not self.cbs.isAlive():

                # Stop checking for the connection
                Clock.unschedule(self.checker)

                # Stop timers for now playing screen
                if self.now_playing:
                    self.now_playing.quit()

                # Remove the callback server
                del self.cbs
                self.cbs = None

        self.timer = Clock.schedule_once(self.update, interval)
