"""
An asynchronous client that listens to messages broadcast by the server.

The client also accepts callback functions.

The client subclasses python threading so methods are built-in to the class
object.
"""
from threading import Thread
from telnetlib import IAC, NOP
import select

from pylms.server import Server


class CallbackServer(Server, Thread):

    MIXER_ALL = "mixer"
    VOLUME_CHANGE = "mixer volume"

    PLAYLIST_ALL = "playlist"
    PLAY_PAUSE = "playlist pause"
    PLAY = "playlist pause 0"
    PAUSE = "playlist pause 1"
    PLAYLIST_OPEN = "playlist open"
    PLAYLIST_CHANGE_TRACK = "playlist newsong"
    PLAYLIST_LOAD_TRACKS = "playlist loadtracks"
    PLAYLIST_ADD_TRACKS = "playlist addtracks"
    PLAYLIST_LOADED = "playlist load_done"
    PLAYLIST_REMOVE = "playlist delete"
    PLAYLIST_CLEAR = "playlist clear"
    PLAYLIST_CHANGED = [PLAYLIST_LOAD_TRACKS,
                        PLAYLIST_ADD_TRACKS,
                        PLAYLIST_REMOVE,
                        PLAYLIST_CLEAR]

    CLIENT_ALL = "client"
    CLIENT_NEW = "client new"
    CLIENT_DISCONNECT = "client disconnect"
    CLIENT_RECONNECT = "client reconnect"

    SYNC = "sync"

    def __init__(self, **kwargs):
        super(CallbackServer, self).__init__(**kwargs)
        self.callbacks = {}
        self.notifications = []
        self.abort = False

    def add_callback(self, event, callback):
        """Add a callback.

           Takes two parameter:
             event:    string of single notification or list of notifications
             callback: function to be run if server sends matching notification
        """
        if type(event) == list:
            for ev in event:
                self.__add_callback(ev, callback)

        else:
            self.__add_callback(event, callback)

    def __add_callback(self, event, callback):
        self.callbacks[event] = callback
        notification = event.split(" ")[0]
        if notification not in self.notifications:
            self.notifications.append(notification)

    def remove_callback(self, event):
        """Remove a callback.

           Takes one parameter:
             event: string of single notification or list of notifications
        """
        if type(event) == list:
            for ev in event:
                self.__remove_callback(ev)

        else:
            self.__remove_callback(event)

    def __remove_callback(self, event):
        del self.callbacks[event]

    def check_event(self, event):
        """Checks whether any of the requested notification types match the
           received notification. If there's a match, we run the requested
           callback function passing the notification as the only parameter.
        """
        for cb in self.callbacks:
            if cb in event:
                self.callbacks[cb](self.unquote(event))
                break

    def check_connection(self):
        # TO DO: Find a way of checking if server is unavailable
        # Stopping the server triggers EOFError which can be caught, but
        # suspending the server leaves the connection open.

        # I have no idea if this works yet!!
        if self.telnet:
            conn = self.telnet.sock

            try:
                ready_to_read, ready_to_write, in_error = \
                      select.select([conn, ], [conn, ], [], 5)

            except select.error:
                self.abort = True

    def run(self):
        self.connect()

        # If we've already defined callbacks then we know which events we're
        # listening out for
        if self.notifications:
            nots = ",".join(self.notifications)
            self.request("subscribe {}".format(nots))

        # If not, let's just listen for everything.
        else:
            self.request("listen")

        while not self.abort:
            try:
                data = self.telnet.read_until("\n".encode(self.charset))[:-1]

                # We've got a notification, so let's see if it's one we're
                # watching.
                if data:
                    self.check_event(data)

            # Server is unavailable so exit gracefully
            except EOFError:
                self.abort = True
