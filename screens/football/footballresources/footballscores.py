# -*- coding: utf-8 -*-
'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import urllib2
import string
from BeautifulSoup import BeautifulSoup
import re
from datetime import datetime, time
import json
import codecs
import requests
import socket

__version__ = "0.3.0"


class matchcommon(object):
    '''class for common functions for match classes.'''

    livescoreslink = ("http://www.bbc.co.uk/sport/shared/football/"
                      "live-scores/matches/{comp}/today")

    def getPage(self, url, sendresponse=False):
        # page = None
        # try:
        #     user_agent = ('Mozilla/5.0 (Windows; U; Windows NT 6.1; '
        #                   'en-US; rv:1.9.1.5) Gecko/20091102 Firefox')
        #     headers = { 'User-Agent' : user_agent }
        #     request = urllib2.Request(url)
        #     response = urllib2.urlopen(request)
        #     page = response.read()
        # except:
        #     pass
        #
        # if sendresponse:
        #     return response
        # else:
        #     # Fixed this line to handle accented team namess
        #     return codecs.decode(page, "utf-8") if page else None
        try:
            r = requests.get(url, timeout=2)
        # requests timeout doesn'r catch socket.timeout so we need to catch
        # both explicitly
        except (socket.timeout, requests.Timeout, requests.ConnectionError):
            return None

        if r.status_code == 200:
            return codecs.decode(r.content, "utf-8")
        else:
            return None


class FootballMatch(matchcommon):
    '''Class for getting details of individual football matches.
    Data is pulled from BBC live scores page.
    '''
    # self.accordionlink = ("http://polling.bbc.co.uk/sport/shared/football/"
    #                       "accordion/partial/collated")

    detailprefix = ("http://www.bbc.co.uk/sport/football/live/"
                    "partial/{id}")

    def __init__(self, team, detailed=False, data=None):
        '''Creates an instance of the Match object.
        Must be created by passing the name of one team.

        data - User can also send data to the class e.g. if multiple instances
        of class are being run thereby saving http requests. Otherwise class
        can handle request on its own.

        detailed - Do we want additional data (e.g. goal scorers, bookings)?
        '''
        self.detailed = detailed

        # Set the relevant urls
        self.detailedmatchpage = None
        self.scorelink = None

        # Boolean to notify user if there is a valid match
        self.matchfound = False

        # Which team am I following?
        self.myteam = team

        self.__resetMatch()

        # Let's try and load some data
        data = self.__loadData(data)

        # If our team is found or we have data
        if data:

            # Update the class properties
            self.__update(data)
            # No notifications for now
            self.goal = self.homegoal = self.awaygoal = False
            self.statuschange = False
            self.newmatch = True

    def __getUKTime(self):
        rawbbctime = self.getPage("http://api.geonames.org/timezoneJSON"
                                  "?formatted=true&lat=51.51&lng=0.13&"
                                  "username=elParaguayo&style=full")

        bbctime = json.loads(rawbbctime).get("time") if rawbbctime else None

        if bbctime:
            servertime = datetime.strptime(bbctime,
                                           "%Y-%m-%d %H:%M")
            return servertime

        else:

            return None

    def __resetMatch(self):
        '''Clear all variables'''
        self.hometeam = None
        self.awayteam = None
        self.homescore = None
        self.awayscore = None
        self.scorelink = None
        self.homescorers = None
        self.awayscorers = None
        self.homeyellowcards = []
        self.awayyellowcards = []
        self.homeredcards = []
        self.awayredcards = []
        self.competition = None
        self.matchtime = None
        self.status = None
        self.goal = self.homegoal = self.awaygoal = False
        self.statuschange = False
        self.newmatch = False
        self.homebadge = None
        self.awaybadge = None
        self.matchid = None
        self.matchlink = None
        self.rawincidents = []
        self.booking = False
        self.redcard = False
        self.leagueid = None

    def __findMatch(self):
        leaguepage = self.getPage(self.livescoreslink.format(comp=""))
        data = None
        teamfound = False

        if leaguepage:

            # Start with the default page so we can get list of active leagues
            raw = BeautifulSoup(leaguepage)

            # Find the list of active leagues
            active = {"class": "drop-down-filter live-scores-fixtures"}
            selection = raw.find("div", active)

            # Loop throught the active leagues
            for option in selection.findAll("option"):

                # Build the link for that competition
                league = option.get("value")[12:]

                if league:
                    scorelink = self.livescoreslink.format(comp=league)

                    scorepage = self.getPage(scorelink)

                    if scorepage:
                        # Prepare to process page
                        optionhtml = BeautifulSoup(scorepage)

                        # We just want the live games...
                        liveid = {"id": "matches-wrapper"}
                        live = optionhtml.find("div", liveid)

                        # Let's look for our team
                        if live.find(text=self.myteam):
                            teamfound = True
                            self.scorelink = scorelink
                            self.competition = option.text.split("(")[0]
                            self.competition = self.competition.strip()
                            self.leagueid = league
                            data = live
                            break

        self.matchfound = teamfound

        return data

    def __getScores(self, data, update=False):

        for match in data.findAll("tr", {"id": re.compile(r'^match-row')}):
            if match.find(text=self.myteam):

                ht = {"class": "team-home"}
                at = {"class": "team-away"}

                self.hometeam = match.find("span", ht).text

                self.awayteam = match.find("span", at).text

                linkrow = match.find("td", {"class": "match-link"})
                try:
                    link = linkrow.find("a").get("href")
                    self.matchlink = "http://www.bbc.co.uk%s" % (link)
                except AttributeError:
                    self.matchlink = None

                mclass = {"class": "elapsed-time"}

                if match.get("class") == "fixture":
                    status = "Fixture"
                    matchtime = match.find("span", mclass).text.strip()[:5]

                elif match.get("class") == "report":
                    status = "FT"
                    matchtime = None

                elif ("%s" %
                      (match.find("span",
                       mclass).text.strip()) == "Half Time"):
                    status = "HT"
                    matchtime = None

                else:
                    status = "L"
                    matchtime = match.find("span", mclass).text.strip()

                matchid = match.get("id")[10:]

                sclass = {"class": "score"}
                score = match.find("span", sclass).text.strip().split(" - ")

                try:
                    homescore = int(score[0].strip())
                    awayscore = int(score[1].strip())

                except:
                    homescore = 0
                    awayscore = 0

                self.statuschange = False
                self.newmatch = False
                self.goal = self.homegoal = self.awaygoal = False
                self.myteamgoal = None

                if update:

                    if not status == self.status:
                        self.statuschange = True

                    if not matchid == self.matchid:
                        self.newmatch = True

                    # if not (homescore == self.homescore and
                    #         awayscore == self.awayscore):

                    if homescore > self.homescore:
                        self.myteamgoal = self.hometeam == self.myteam
                        self.homegoal = True
                    elif awayscore > self.awayscore:
                        self.myteamgoal = self.awayteam == self.myteam
                        self.awaygoal = True

                    self.goal = any([self.homegoal, self.awaygoal])

                self.status = status if status else None
                self.matchtime = matchtime if matchtime else None
                self.matchid = matchid if matchid else None
                self.homescore = homescore
                self.awayscore = awayscore

    def __update(self, data=None):

        self.__getScores(data)

        if self.detailed:
            self.__getDetails()

    def __loadData(self, data=None):

        self.matchfound = False

        if data:
            if data.find(text=self.myteam):
                self.matchfound = True
            else:
                data = None

        if not data and self.scorelink:
            scorepage = self.getPage(self.scorelink)
            if scorepage:
                scorehtml = BeautifulSoup(scorepage)
                data = scorehtml.find("div", {"id": "matches-wrapper"})
                if data.find(text=self.myteam):
                    self.matchfound = True
                else:
                    data = None
            else:
                data = None

        if not data:
            data = self.__findMatch()

        if not data:
            self.__resetMatch()

        return data

    def Update(self, data=None):

        data = self.__loadData(data)

        if data:
            self.__getScores(data, update=True)

        if self.detailed:
            self.__getDetails()

    def __getDetails(self):

        if self.matchid:
            # Prepare bautiful soup to scrape match page

                # Let's get the home and away team detail sections
            try:
                bs = BeautifulSoup(self.getPage(self.detailprefix.format(
                                             id=self.matchid)))
                iclass = {"class": "incidents-table"}
                incidents = bs.find("table", iclass).findAll("tr")
            except:
                incidents = None

            # Get incidents
            # This populates variables with details of scorers and bookings
            # Incidents are stored in a list of tuples: format is:
            # [(Player Name, [times of incidents])]
            hsc = []
            asc = []
            hyc = []
            ayc = []
            hrc = []
            arc = []

            if incidents:

                self.__goalscorers = []
                self.__yellowcards = []
                self.__redcards = []

                itclass = {"class": re.compile(r"\bincident-type \b")}
                ithclass = {"class": "incident-player-home"}
                itaclass = {"class": "incident-player-away"}
                ittclass = {"class": "incident-time"}
                for incident in incidents:
                    i = incident.find("td", itclass)
                    if i:
                        h = incident.find("td", ithclass).text.strip()

                        a = incident.find("td", itaclass).text.strip()

                        t = incident.find("td", ittclass).text.strip()

                        if "goal" in i.get("class"):
                            if h:
                                hsc = self.__addIncident(hsc, h, t)
                                self.__goalscorers.append((self.hometeam,
                                                           h, t))
                                self.__addRawIncident("home", "goal", h, t)
                            else:
                                asc = self.__addIncident(asc, a, t)
                                self.__goalscorers.append((self.awayteam,
                                                           a, t))
                                self.__addRawIncident("away", "goal", a, t)

                        elif "yellow-card" in i.get("class"):
                            if h:
                                hyc = self.__addIncident(hyc, h, t)
                                self.__yellowcards.append((self.hometeam,
                                                           h, t))
                                self.__addRawIncident("home", "yellow", h, t)
                            else:
                                ayc = self.__addIncident(ayc, a, t)
                                self.__yellowcards.append((self.awayteam,
                                                           a, t))
                                self.__addRawIncident("away", "yellow", a, t)

                        elif "red-card" in i.get("class"):
                            if h:
                                hrc = self.__addIncident(hrc, h, t)
                                self.__redcards.append((self.hometeam, h, t))
                                self.__addRawIncident("home", "red", h, t)
                            else:
                                arc = self.__addIncident(arc, a, t)
                                self.__redcards.append((self.awayteam, a, t))
                                self.__addRawIncident("away", "red", a, t)

            self.booking = not (self.homeyellowcards == hyc and
                                self.awayyellowcards == ayc)

            self.redcard = not (self.homeredcards == hrc and
                                self.awayredcards == arc)

            self.homescorers = hsc
            self.awayscorers = asc
            self.homeyellowcards = hyc
            self.awayyellowcards = ayc
            self.homeredcards = hrc
            self.awayredcards = arc

    def __addIncident(self, incidentlist, player, incidenttime):
        '''method to add incident to list variable'''
        found = False
        for incident in incidentlist:
            if incident[0] == player:
                incident[1].append(incidenttime)
                found = True
                break

        if not found:
            incidentlist.append((player, [incidenttime]))

        return incidentlist

    def __addRawIncident(self, team, incidenttype, player, incidenttime):

        incident = (team, incidenttype, player, incidenttime)

        if incident not in self.rawincidents:
            self.rawincidents.append(incident)

    def formatIncidents(self, incidentlist, newline=False):
        '''Incidents are in the following format:
        List:
          [Tuple:
            (Player name, [list of times of incidents])]

        This function converts the list into a string.
        '''
        temp = []
        incidentjoin = "\n" if newline else ", "

        for incident in incidentlist:
            temp.append("%s (%s)" % (incident[0],
                                     ", ".join(incident[1])))

        return incidentjoin.join(temp)

    def getTeamBadges(self):
        found = False

        if self.matchlink:
            badgepage = self.getPage(self.matchlink)
            if badgepage:
                linkpage = BeautifulSoup(badgepage)
                badges = linkpage.findAll("div", {"class": "team-badge"})
                if badges:
                    self.homebadge = badges[0].find("img").get("src")
                    self.awaybadge = badges[1].find("img").get("src")
                    found = True

        return found

    def __nonzero__(self):

        return self.matchfound

    def __repr__(self):

        return "FootballMatch(\'%s\', detailed=%s)" % (self.myteam,
                                                       self.detailed)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.matchid is not None:
                return self.matchid == other.matchid
            else:
                return self.myteam == other.myteam
        else:
            return False

    # Neater functions to return data:

    @property
    def HomeTeam(self):
        """Returns string of the home team's name

        """
        return self.hometeam

    @property
    def AwayTeam(self):
        """Returns string of the away team's name

        """
        return self.awayteam

    @property
    def HomeScore(self):
        """Returns the number of goals scored by the home team

        """
        return self.homescore

    @property
    def AwayScore(self):
        """Returns the number of goals scored by the away team

        """
        return self.awayscore

    @property
    def Competition(self):
        """Returns the name of the competition to which the match belongs

        e.g. "Premier League", "FA Cup" etc

        """
        return self.competition

    @property
    def Status(self):
        """Returns the status of the match

        e.g. "L", "HT", "FT"

        """
        if self.status == "Fixture":
            return self.matchtime
        else:
            return self.status

    @property
    def HasStarted(self):
        """Boolean returns False if match has not yet started

        """
        return not self.status == "Fixture"

    @property
    def HasFinished(self):
        """Boolean returns True if match has finished

        """
        return self.status == "FT"

    @property
    def IsLive(self):
        """Boolean returns True if match is in play (or HT)

        """
        return self.HasStarted and not self.HasFinished

    @property
    def Goal(self):
        """Boolean. Returns True if score has changed since last update

        """
        return self.goal

    @property
    def HomeGoal(self):
        """Boolean. Returns True if home team has scored since last update

        """
        return self.homegoal

    @property
    def AwayGoal(self):
        """Boolean. Returns True if away team has scored since last update

        """
        return self.awaygoal

    @property
    def MyTeamGoal(self):
        """Boolean. Returns:
           True - Goal scored by selected team
           False - Goal scored by opposition
           None - No goal scored since last update
        """
        return self.myteamgoal

    @property
    def StatusChanged(self):
        """Boolean. Returns True if status has changed since last update

        e.g. Match started, half-time started etc

        """
        return self.statuschange

    @property
    def NewMatch(self):
        """Boolean. Returns True if the match found since last update

        """
        return self.newmatch

    @property
    def MatchFound(self):
        """Boolean. Returns True if a match is found in JSON feed

        """
        return self.matchfound

    @property
    def HomeBadge(self):
        """Returns link to image for home team's badge

        """
        return self.homebadge

    @property
    def AwayBadge(self):
        """Returns link to image for away team's badge

        """
        return self.awaybadge

    @property
    def HomeScorers(self):
        """Returns list of goalscorers for home team

        """
        return self.homescorers

    @property
    def AwayScorers(self):
        """Returns list of goalscorers for away team

        """
        return self.awayscorers

    @property
    def HomeYellowCards(self):
        """Returns list of players receiving yellow cards for home team

        """
        return self.homeyellowcards

    @property
    def AwayYellowCards(self):
        """Returns list of players receiving yellow cards for away team

        """
        return self.awayyellowcards

    @property
    def HomeRedCards(self):
        """Returns list of players sent off for home team

        """
        return self.homeredcards

    @property
    def AwayRedCards(self):
        """Returns list of players sent off for away team

        """
        return self.awayredcards

    @property
    def LastGoalScorer(self):
        if self.detailed:
            if self.__goalscorers:
                return self.__goalscorers[-1]
            else:
                return None
        else:
            return None

    @property
    def LastYellowCard(self):
        if self.detailed:
            if self.__yellowcards:
                return self.__yellowcards[-1]
            else:
                return None
        else:
            return None

    @property
    def LastRedCard(self):
        if self.detailed:
            if self.__redcards:
                return self.__redcards[-1]
            else:
                return None
        else:
            return None

    @property
    def MatchDate(self):
        """Returns date of match i.e. today's date

        """
        d = datetime.now()
        datestring = "%s %d %s" % (
                                        d.strftime("%A"),
                                        d.day,
                                        d.strftime("%B %Y")
                                      )
        return datestring

    @property
    def MatchTime(self):
        """If detailed info available, returns match time in minutes.

        If not, returns Status.

        """
        if self.status == "L" and self.matchtime is not None:
            return self.matchtime
        else:
            return self.Status

    def abbreviate(self, cut):
        """Returns short formatted summary of match but team names are
        truncated according to the cut parameter.

        e.g. abbreviate(3):
          "Ars 1-1 Che (L)"

        Should handle accented characters.

        """
        return u"%s %s-%s %s (%s)" % (
                                      self.hometeam[:cut],
                                      self.homescore,
                                      self.awayscore,
                                      self.awayteam[:cut],
                                      self.Status
                                      )

    def __unicode__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        Should handle accented characters.

        """
        if self.matchfound:

            return u"%s %s-%s %s (%s)" % (
                                          self.hometeam,
                                          self.homescore,
                                          self.awayscore,
                                          self.awayteam,
                                          self.Status
                                          )

        else:

            return u"%s are not playing today." % (self.myteam)

    def __str__(self):
        """Returns short formatted summary of match.

        e.g. "Arsenal 1-1 Chelsea (L)"

        """
        return unicode(self).encode('utf-8')

    @property
    def PrintDetail(self):
        """Returns detailed summary of match (if available).

        e.g. "(L) Arsenal 1-1 Chelsea (Arsenal: Wilshere 10',
              Chelsea: Lampard 48')"
        """
        if self.detailed:
            hscore = False
            scorerstring = ""

            if self.homescorers or self.awayscorers:
                scorerstring = " ("
                if self.homescorers:
                    hscore = True
                    hscorers = self.formatIncidents(self.homescorers)
                    scorerstring += "%s: %s" % (self.hometeam, hscorers)

                if self.awayscorers:
                    if hscore:
                        scorerstring += " - "
                    ascorers = self.formatIncidents(self.awayscorers)
                    scorerstring += "%s: %s" % (self.awayteam, ascorers)

                scorerstring += ")"

            return "(%s) %s %s-%s %s%s" % (
                                            self.MatchTime,
                                            self.hometeam,
                                            self.homescore,
                                            self.awayscore,
                                            self.awayteam,
                                            scorerstring
                                            )
        else:
            return self.__str__()

    @property
    def TimeToKickOff(self):
        '''Returns a timedelta object for the time until the match kicks off.

        Returns None if unable to parse match time or if match in progress.

        Should be unaffected by timezones as it gets current time from bbc
        server which *should* be the same timezone as matches shown.
        '''
        if self.status == "Fixture":
            try:
                koh = int(self.matchtime[:2])
                kom = int(self.matchtime[3:5])
                kickoff = datetime.combine(
                            datetime.now().date(),
                            time(koh, kom, 0))
                timetokickoff = kickoff - self.__getUKTime()
            except Exception, e:
                timetokickoff = None
            finally:
                pass
        else:
            timetokickoff = None

        return timetokickoff

    @property
    def matchdict(self):
        return {"hometeam": self.hometeam,
                "awayteam": self.awayteam,
                "status": self.status,
                "matchtime": self.MatchTime,
                "homescore": self.homescore,
                "awayscore": self.awayscore,
                "homescorers": self.homescorers,
                "awayscorers": self.awayscorers,
                "homeyellow": self.homeyellowcards,
                "awayyellow": self.awayyellowcards,
                "homered": self.homeredcards,
                "awayred": self.awayredcards,
                "incidentlist": self.rawincidents}


class League(matchcommon):
    '''Get summary of matches for a given league.

    NOTE: this may need to be updated as currently uses the accordion
    source data whereas main Match module uses more complete source.
    '''

    accordionlink = ("http://polling.bbc.co.uk/sport/shared/football/"
                     "accordion/partial/collated")

    def __init__(self, league, detailed=False):

        self.__leaguematches = self.__getMatches(league, detailed=detailed)
        self.__leagueid = league
        self.__leaguename = self.__getLeagueName(league)
        self.__detailed = detailed

    def __getData(self, league):

        scorelink = self.livescoreslink.format(comp=league)
        data = None
        # Prepare to process page
        optionpage = self.getPage(scorelink)
        if optionpage:
            optionhtml = BeautifulSoup(optionpage)

            # We just want the live games...
            data = optionhtml.find("div", {"id": "matches-wrapper"})

        return data

    def __getLeagueName(self, league):

        leaguename = None
        rawpage = self.getPage(self.livescoreslink.format(comp=league))

        if rawpage:
            raw = BeautifulSoup(rawpage)

            # Find the list of active leagues
            selection = raw.find("div",
                                 {"class":
                                  "drop-down-filter live-scores-fixtures"})

            if selection:

                selectedleague = selection.find("option",
                                                {"selected": "selected"})

                if selectedleague:
                    leaguename = selectedleague.text.split("(")[0].strip()

        return leaguename

    @staticmethod
    def getLeagues():
        leagues = []
        # raw =  BeautifulSoup(self.getPage(self.accordionlink))
        # # Loop through all the competitions being played today
        # for option in raw.findAll("option"):
        #     league = {}
        #     league["name"] = option.text
        #     league["id"] = option.get("value")
        #     leagues.append(league)

        # return leagues
        livescoreslink = matchcommon().livescoreslink

        # Start with the default page so we can get list of active leagues
        rawpage = matchcommon().getPage(livescoreslink.format(comp=""))
        if rawpage:
            raw = BeautifulSoup(rawpage)

            # Find the list of active leagues
            selection = raw.find("div",
                                 {"class":
                                  "drop-down-filter live-scores-fixtures"})

            # Loop throught the active leagues
            for option in selection.findAll("option"):

                # Build the link for that competition
                # league = option.get("value")[12:]
                league = {}
                league["name"] = option.text.split("(")[0].strip()
                league["id"] = option.get("value")[12:]
                if league["id"]:
                    leagues.append(league)

        return leagues

    def __getMatches(self, league, detailed=False, data=None):

        if data is None:
            data = self.__getData(league)

        matches = []
        if data:
            rawmatches = data.findAll("tr", {"id": re.compile(r'^match-row')})
        else:
            rawmatches = None

        if rawmatches:

            for match in rawmatches:
                team = match.find("span", {"class": "team-home"}).text
                m = FootballMatch(team, detailed=detailed, data=data)
                matches.append(m)

        return matches

    def __repr__(self):
        return "League(\'%s\', detailed=%s)" % (self.__leagueid,
                                                self.__detailed)

    def __str__(self):
        if self.__leaguematches:
            if len(self.__leaguematches) == 1:
                matches = "(1 match)"
            else:
                matches = "(%d matches)" % (len(self.__leaguematches))
            return "%s %s" % (self.__leaguename, matches)
        else:
            return None

    def __nonzero__(self):
        return bool(self.__leaguematches)

    def Update(self):
        '''Updates all matches in the league.

        If there are no games (e.g. a new day) then the old matches
        are removed.

        If there are new games, these are added.
        '''

        # Get the data for league
        data = self.__getData(self.__leagueid)

        # We've found some data so let's process
        if data:
            # Get a list of the current matches from the new data
            currentmatches = self.__getMatches(self.__leagueid, data=data)

            # If the match is already in our league, then we keep it
            self.__leaguematches = [m for m in self.__leaguematches
                                    if m in currentmatches]

            # Check if there are any matches in the new data which
            # aren't in our list
            newmatches = [m for m in currentmatches
                          if m not in self.__leaguematches]

            # If so...
            if newmatches:
                # If we want detailed info on each match
                if self.__detailed:
                    for m in newmatches:

                        # then we need to update the flag for that match
                        m.detailed = True

                        # and add it to our list
                        self.__leaguematches.append(m)
                else:
                    # If not, then we can just add the new matches to our list
                    self.__leaguematches += newmatches

            # If we've got matches in our list
            if self.__leaguematches:
                for match in self.__leaguematches:

                    # Update the matches
                    # NB we need to update each match to ensure the "Goal"
                    # flag is updated appropriately, rather than just adding a
                    # new match object.
                    match.Update(data=data)

        else:
            # If there's no data, there are no matches...
            self.__leaguematches = []

        # If we haven't managed to set the league name yet
        # then we should be able to find it if there are some matches
        if self.__leaguematches and self.LeagueName is None:
            self.LeagueName = self.__getLeagueName(self.__leagueid)

    @property
    def LeagueMatches(self):
        return self.__leaguematches

    @property
    def LeagueName(self):
        return self.__leaguename

    @property
    def LeagueID(self):
        return self.__leagueid

    @property
    def NewMatch(self):
        return any((m.NewMatch for m in self.__leaguematches))

    @property
    def Goal(self):
        return any((m.Goal for m in self.__leaguematches))

    @property
    def StatusChanged(self):
        return any((m.StatusChanged for m in self.__leaguematches))

    @property
    def HasFinished(self):
        return all((m.HasFinished for m in self.__leaguematches))

    @property
    def HasStarted(self):
        return any((m.HasStarted for m in self.__leaguematches))

    @property
    def IsLive(self):
        return any((m.HasStarted for m in self.__leaguematches))


class LeagueTable(matchcommon):
    '''class to convert BBC league table format into python list/dict.'''

    leaguebase = "http://www.bbc.co.uk/sport/football/tables"
    leaguemethod = "filter"

    def __init__(self):
        # self.availableLeague = self.getLeagues()
        pass

    def getLeagues(self):
        '''method for getting list of available leagues'''

        leaguelist = []
        raw = BeautifulSoup(self.getPage(self.leaguebase))
        form = raw.find("div", {"class": "drop-down-filter",
                                "id": "filter-fixtures-no-js"})
        self.leaguemethod = form.find("select").get("name")
        leagues = form.findAll("option")
        for league in leagues:
            l = {}
            if league.get("value") != "":
                l["name"] = league.text
                l["id"] = league.get("value")
                leaguelist.append(l)
        return leaguelist

    def getLeagueTable(self, leagueid):
        '''method for creating league table of selected league.'''

        result = []

        class LeagueTableTeam(object):

            def __init__(self, team):

                f = team.find
                mov = re.compile(r"no-movement|moving-up|moving-down")
                movmap = {"No movement": "same",
                          "Moving up": "up",
                          "Moving down": "down"}
                self.name = f("td", {"class": "team-name"}).text
                self.movement = movmap.get(f("span", {"class": mov}).text)
                self.position = int(f("span",
                                      {"class": "position-number"}).text)
                self.played = int(f("td", {"class": "played"}).text)
                self.won = int(f("td", {"class": "won"}).text)
                self.drawn = int(f("td", {"class": "drawn"}).text)
                self.lost = int(f("td", {"class": "lost"}).text)
                self.goalsfor = int(f("td", {"class": "for"}).text)
                self.goalsagainst = int(f("td", {"class": "against"}).text)
                self.goaldifference = int(f("td",
                                            {"class":
                                             "goal-difference"}).text)
                self.points = int(f("td", {"class": "points"}).text)

                try:
                    lastgames = f("td", {"class": "last-10-games"})
                    lg = []
                    for game in lastgames.findAll("li"):
                        g = {}
                        g["result"] = game.get("class")
                        g["score"] = game.get("data-result")
                        g["opponent"] = game.get("data-against")
                        g["date"] = game.get("data-date")
                        g["summary"] = game.get("title")
                        lg.append(g)
                    self.lasttengames = lg

                except:
                    self.lasttengames = []

                def __repr__(self):
                    return "<LeagueTableTeam object - %s>" % self.name

            def __str__(self):
                return "%d %s %d" % (self.position,
                                     self.name,
                                     self.points)

        leaguepage = "%s?%s=%s" % (self.leaguebase,
                                   self.leaguemethod,
                                   leagueid)

        raw = BeautifulSoup(self.getPage(leaguepage))

        for table in raw.findAll("div", {"class":
                                         "league-table full-table-wide"}):

            lg = {}
            teamlist = []

            leaguename = table.find("h2", {"class": "table-header"})

            for tag in ["div", "script"]:
                for nest in leaguename.findAll(tag):
                    nest.extract()

            lg["name"] = leaguename.text.strip()

            for team in table.findAll("tr", {"id": re.compile(r'team')}):
                t = LeagueTableTeam(team)
                teamlist.append(t)

            lg["table"] = teamlist
            result.append(lg)

        return result


class Teams(matchcommon):

    def getTeams(self):
        # Start with the default page so we can get list of active leagues
        rawpage = self.getPage(self.livescoreslink.format(comp=""))
        teamlist = []

        if rawpage:
            raw = BeautifulSoup(rawpage)

            # Find the list of active leagues
            liveclass = {"class": "drop-down-filter live-scores-fixtures"}
            selection = raw.find("div", liveclass)

            # Loop throught the active leagues
            for option in selection.findAll("option"):

                # Build the link for that competition
                league = option.get("value")[12:]

                if league:
                    scorelink = self.livescoreslink.format(comp=league)

                    # Prepare to process page
                    scorepage = self.getPage(scorelink)
                    if scorepage:
                        optionhtml = BeautifulSoup(scorepage)

                        # We just want the live games...
                        live = optionhtml.find("div",
                                               {"id": "matches-wrapper"})

                        mtid = {"id": re.compile(r'^match-row')}
                        for match in live.findAll("tr", mtid):

                            teamlist.append(match.find("span",
                                                       {"class":
                                                        "team-home"}).text)

                            teamlist.append(match.find("span",
                                                       {"class":
                                                        "team-away"}).text)

            teamlist = sorted(teamlist)

        return teamlist


class Results(matchcommon):

    '''class to convert BBC league table format into python list/dict.'''

    resultbase = "http://www.bbc.co.uk/sport/football/results"
    resultmethod = "filter"

    def __init__(self):
        pass

    def getCompetitions(self):
        '''method for getting list of available results pages'''

        complist = []
        raw = BeautifulSoup(self.getPage(self.resultbase))
        form = raw.find("div", {"class": "drop-down-filter",
                                "id": "filter-fixtures-no-js"})
        self.resultmethod = form.find("select").get("name")
        comps = form.findAll("option")
        for comp in comps:
            l = {}
            if comp.get("value") != "":
                l["name"] = comp.text
                l["id"] = comp.get("value")
                complist.append(l)
        return complist

    def getResults(self, compid):
        '''method for creating league table of selected league.'''

        result = []

        leaguepage = "%s?%s=%s" % (self.resultbase,
                                   self.resultmethod,
                                   compid)

        raw = BeautifulSoup(self.getPage(leaguepage))

        raw = raw.find("div", {"class": re.compile(r"\bfixtures-table\b")})

        while raw.find("h2", {"class": "table-header"}) is not None:

            resultdate = raw.find("h2", {"class": "table-header"})
            matchdate = resultdate.text.strip()
            resultdate.extract()

            results = raw.find("table", {"class": "table-stats"})

            matches = []

            hclass = {"class": re.compile(r'^team-home')}
            aclass = {"class": re.compile(r'^team-away')}
            for matchresult in results.findAll("tr",
                                               {"id":
                                                re.compile(r'^match-row')}):
                hometeam = matchresult.find("span", hclass).text.strip()
                awayteam = matchresult.find("span", aclass).text.strip()
                score = matchresult.find("span", {"class":
                                                  "score"}).text.strip()
                matches.append({"hometeam": hometeam,
                                "awayteam": awayteam,
                                "score": score})

            resultday = {"date": matchdate,
                         "results": matches}

            result.append(resultday)

            results.extract()

        return result


class Fixtures(matchcommon):

    '''class to convert BBC league table format into python list/dict.'''

    fixturebase = "http://www.bbc.co.uk/sport/football/fixtures"
    fixturemethod = "filter"

    def __init__(self):
        pass

    def getCompetitions(self):
        '''method for getting list of available results pages'''

        complist = []
        raw = BeautifulSoup(self.getPage(self.fixturebase))
        form = raw.find("div", {"class": "drop-down-filter",
                                "id": "filter-fixtures-no-js"})
        self.fixturemethod = form.find("select").get("name")
        comps = form.findAll("option")
        for comp in comps:
            l = {}
            if comp.get("value") != "":
                l["name"] = comp.text
                l["id"] = comp.get("value")
                complist.append(l)
        return complist

    def getFixtures(self, compid):
        '''method for creating league table of selected league.'''

        result = []

        leaguepage = "%s?%s=%s" % (self.fixturebase,
                                   self.fixturemethod,
                                   compid)

        raw = BeautifulSoup(self.getPage(leaguepage))

        raw = raw.find("div", {"class": re.compile(r"\bfixtures-table\b")})

        while raw.find("h2", {"class": "table-header"}) is not None:

            fixturedate = raw.find("h2", {"class": "table-header"})
            matchdate = fixturedate.text.strip()
            fixturedate.extract()

            results = raw.find("table", {"class": "table-stats"})

            matches = []

            hclass = {"class": re.compile(r'^team-home')}
            aclass = {"class": re.compile(r'^team-away')}

            for matchresult in results.findAll("tr",
                                               {"id":
                                                re.compile(r'^match-row')}):
                hometeam = matchresult.find("span", hclass).text.strip()
                awayteam = matchresult.find("span", aclass).text.strip()
                matches.append({"hometeam": hometeam,
                                "awayteam": awayteam})

            resultday = {"date": matchdate,
                         "fixtures": matches}

            result.append(resultday)

            results.extract()

        return result


def getAllLeagues():

    tableleagues = LeagueTable().getLeagues()
    tableleagues = [{"name": x["name"], "id": x["id"][12:]}
                    for x in tableleagues]
    matchleagues = League.getLeagues()

    tableleagues += [x for x in matchleagues if x not in tableleagues]

    return tableleagues
