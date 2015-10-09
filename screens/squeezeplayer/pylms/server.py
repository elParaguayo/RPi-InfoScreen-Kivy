"""
PyLMS: Python Wrapper for Logitech Media Server CLI
(Telnet) Interface

Copyright (C) 2010 JingleManSweep <jinglemansweep [at] gmail [dot] com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import telnetlib
from pylms.player import Player


class Server(object):

    """
    Server
    """

    def __init__(self, hostname="localhost",
                       port=9090,
                       username="",
                       password="",
                       charset="utf8"):

        """
        Constructor
        """
        self.debug = False
        self.logger = None
        self.telnet = None
        self.logged_in = False
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.version = ""
        self.player_count = 0
        self.players = []
        self.charset = charset

    def connect(self, update=True):
        """
        Connect
        """
        self.telnet_connect()
        self.login()
        self.get_players(update=update)

    def telnet_connect(self):
        """
        Telnet Connect
        """
        self.telnet = telnetlib.Telnet(self.hostname, self.port)

    def login(self):
        """
        Login
        """
        result = self.request("login %s %s" % (self.username, self.password))
        self.logged_in = (result == "******")

    def request(self, command_string, preserve_encoding=False):
        """
        Request
        """
        # self.logger.debug("Telnet: %s" % (command_string))
        self.telnet.write(self.__encode(command_string + "\n"))
        response = self.__decode(self.telnet.read_until(self.__encode("\n"))[:-1])
        if not preserve_encoding:
            response = self.__unquote(response)
        else:
            command_string_quoted = command_string[0:command_string.find(':')] + command_string[command_string.find(':'):].replace(':',self.__quote(':'))
        start = command_string.split(" ")[0]
        if start in ["songinfo", "trackstat", "albums", "songs", "artists", "rescan", "rescanprogress"]:
            if not preserve_encoding:
                result = response[len(command_string)+1:]
            else:
                result = response[len(command_string_quoted)+1:]
        else:
            if not preserve_encoding:
                result = response[len(command_string)-1:]
            else:
                result = response[len(command_string_quoted)-1:]
        result = result.strip()
        return result

    def request_with_results(self, command_string, preserve_encoding=False):
        """
        Request with results
        Return tuple (count, results, error_occured)
        """
        quotedColon = self.__quote(':')
        try:
            #init
            quotedColon = urllib.quote(':')
            #request command string
            resultStr = ' '+self.request(command_string, True)
            #get number of results
            count = 0
            if resultStr.rfind('count%s'%quotedColon)>=0:
                count = int(resultStr[resultStr.rfind('count%s'%quotedColon):].replace('count%s'%quotedColon,''))
            #remove number of results from result string and cut result string by "id:"
            idIsSep = True
            if resultStr.find(' id%s'%quotedColon)<0:
                idIsSep = False
            if resultStr.find('count')>=0:
                resultStr = resultStr[:resultStr.rfind('count')-1]
            results = resultStr.split(' id%s'%quotedColon)

            output = []
            for result in results:
                result = result.strip()
                if len(result)>0:
                    if idIsSep:
                        #fix missing 'id:' at beginning
                        result = 'id%s%s' % (quotedColon, result)
                    subResults = result.split(' ')
                    item = {}
                    for subResult in subResults:
                        #save item
                        key,value = subResult.split(quotedColon,1)
                        if not preserve_encoding:
                            item[urllib.unquote(key)] = self.__unquote(value)
                        else:
                            item[key] = value
                    output.append(item)
            return count,output,False
        except Exception as e:
            #error parsing results (not correct?)
            return 0,[],True


    def get_players(self, update=True):
        """
        Get Players
        """
        self.players = []
        player_count = self.get_player_count()
        for i in range(player_count):
            player = Player(server=self, index=i-1, update=update)
            self.players.append(player)
        return self.players

    def get_player(self, ref=None):
        """
        Get Player
        """
        ref = str(ref).lower()
        if ref:
            for player in self.players:
                player_name = str(player.name).lower()
                player_ref = str(player.ref).lower()
                if ref == player_ref or ref in player_name:
                    return player

    def get_version(self):
        """
        Get Version
        """
        self.version = self.request("version ?")
        return self.version

    def get_player_count(self):
        """
        Get Number Of Players
        """
        self.player_count = self.request("player count ?")
        return int(self.player_count)

    def search(self, term, mode='albums'):
        """
        Search term in database
        """
        if mode=='albums':
            return self.request_with_results("albums 0 50 tags:%s search:%s" % ("l", term))
        elif mode=='songs':
            return self.request_with_results("songs 0 50 tags:%s search:%s" % ("", term))
        elif mode=='artists':
            return self.request_with_results("artists 0 50 search:%s" % (term))

    def rescan(self, mode='fast'):
        """
        Rescan library
        Mode can be 'fast' for update changes on library, 'full' for complete library scan and 'playlists' for playlists scan only
        """
        is_scanning = True
        try:
            is_scanning = bool(self.request("rescan ?"))
        except:
            pass

        if not is_scanning:
            if mode=='fast':
                return self.request("rescan")
            elif mode=='full':
                return self.request("wipecache")
            elif mode=='playlists':
                return self.request("rescan playlists")
        else:
            return ""

    def rescanprogress(self):
        """
        Return current rescan progress
        """
        return self.request_with_results("rescanprogress")

    def __encode(self, text):
        return text.encode(self.charset)

    def __decode(self, bytes):
        return bytes.decode(self.charset)

    def __quote(self, text):
        try:
            import urllib.parse
            return urllib.parse.quote(text, encoding=self.charset)
        except ImportError:
            import urllib
            return urllib.quote(text)

    def __unquote(self, text):
        try:
            import urllib.parse
            return urllib.parse.unquote(text, encoding=self.charset)
        except ImportError:
            import urllib
            return urllib.unquote(text)
