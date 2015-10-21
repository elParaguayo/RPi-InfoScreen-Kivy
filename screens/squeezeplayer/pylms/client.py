__author__ = 'Ben Weiner, http://github.com/readingtype'

"""
A listening Client derived from Server by Ben Weiner, https://github.com/readingtype
Start the Client instance in a thread so you can do other stuff while it is running.
"""

import telnetlib
import urllib
import pylms
from pylms.server import Server
from pylms.player import Player

class Client(Server):

    def start(self):
        self.connect()
        self.request("listen")

        while True:
            received = self.telnet.read_until("\n".encode(self.charset))[:-1]
            if received:
                status = self.request_with_results(command_string=None, received=received)

    def telnet_connect(self):
        """
        Stay connected forever
        """
        self.telnet = telnetlib.Telnet(self.hostname, self.port, timeout=None)

    def update(self, data):
        # overload this in your instance to do stuff
        print "update: %s" % data
