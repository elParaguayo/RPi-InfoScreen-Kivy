import json
import bottle
import os
import requests

plugin_path = os.path.dirname(__file__)
plugin = os.path.basename(plugin_path)
all_teams = os.path.join(plugin_path, "teams.txt")
all_leagues = os.path.join(plugin_path, "leagues.txt")
TEAM_OPTION = """<option value="{team}" {selected}>{team}</option>\n"""
LEAGUE_OPTION = """<option value="{leagueid}" {selected}>{league}</option>\n"""

LAYOUT = """% rebase("base.tpl", title="Configure Football Scores Screen")
<form action="/footballscores/update" method="POST">
<table class="centre" width="50"%>
<tr>
<td width="40%"">Select Teams</td>
<td>{teamselect}</td>
</tr>
<tr />
<tr>
<td width="40%"">Select Leagues</td>
<td>{leagueselect}</td>
</tr>
</table>
<br /><button type="submit">UPDATE</button>
"""

bindings = [("/footballscores", "show_teams", ["GET"]),
            ("/footballscores/update", "update", ["POST"])]

def show_teams():
    host = bottle.request.get_header('host')
    addr = "http://localhost:8089/api/{plugin}/configure".format(host=host,
                                                          plugin=plugin)
    getconfig = requests.get(addr).json()

    with open(all_teams, "r") as teamfile:
        teams = [x.strip() for x in teamfile.readlines()]

    ts = ("""<select name="teams" multiple size=15>\n""")
    selected_teams = getconfig["data"]["teams"]
    for team in teams:
        selected = " selected" if team in selected_teams else ""
        ts += TEAM_OPTION.format(team=team, selected=selected)

    ts += "</select>"

    with open(all_leagues, "r") as leaguefile:
        leagues = [x.strip().split("\t") for x in leaguefile.readlines()]

    ls = """<select name="leagues" multiple size=15>\n"""
    selected_leagues = getconfig["data"]["leagues"]
    for league in leagues:
        selected = " selected" if league[0] in selected_leagues else ""
        ls += LEAGUE_OPTION.format(leagueid=league[0],
                                     league=league[1],
                                     selected=selected)

    ls += """</select>"""

    tpl = LAYOUT.format(teamselect=ts, leagueselect=ls)

    return bottle.template(tpl)

def update():
    host = bottle.request.get_header('host')
    addr = "http://localhost:8089/api/{plugin}/configure".format(host=host,
                                                              plugin=plugin)
    leagues = bottle.request.forms.getall("leagues")
    teams = bottle.request.forms.getall("teams")
    data = {"teams": teams, "leagues": leagues}
    print data
    headers = {"Content-Type": "application/json; charset=utf8"}
    r = requests.post(addr, headers=headers, data=json.dumps(data))
    j = r.json()
    if j["status"] == "success":
        bottle.redirect("/")
    else:
        return "Error."
