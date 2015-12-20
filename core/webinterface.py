'''Web interface for the Raspberry Pi Information Screen.

   by elParaguayo

   Provides a web interface to enable/disabl/configure screens.

   Has an underlying API so screens can define their own web pages for custom
   configuration.

   API format:

   [HOST]/api/<screenname>/configure
        GET: returns JSON format of user-configurable settings for screen
        POST: takes JSON format of updated configuration.

   [HOST]/api/<screenname>/enable
        GET: enable the selected screen

   [HOST]/api/<screenname>/disable
        GET: disable the selected screen

'''

from threading import Thread
from time import sleep
import os
import json
import imp

from kivy.app import App

from bottle import Bottle, template, request, TEMPLATE_PATH, redirect
import requests

from getplugins import getPlugins
from webapi import InfoScreenAPI



HEADER = '''Raspberry Pi Information Screen<br />'''

SCREEN_CONFIG = '''% rebase("base.tpl", title="Configuration Screen: {}".format(screen.capitalize()))
    <form action="/configure/{{screen}}" method="POST">
    <br />
    <textarea cols="60" rows="10" name="params" maxlength="2500">{{conf}}</textarea><br />
    <br />
    <button type="submit">Save Config</button></form>'''

class InfoScreenWebServer(Bottle):
    def __init__(self, infoscreen, folder):
        super(InfoScreenWebServer, self).__init__()
        self.infoscreen = infoscreen.base
        self.folder = folder
        tpls = os.path.join(self.folder, "web", "templates")
        TEMPLATE_PATH.insert(0, tpls)
        self.custom_screens = {}
        self.process_plugins()
        self.route("/current", callback=self.show_current)
        self.route("/change/<screen>", callback=self.change_screen)
        self.route("/configure/<screen>", callback=self.update_config, method="GET")
        self.route("/configure/<screen>", callback=self.save_config, method="POST")
        self.route("/", callback=self.list_screens, method=["GET", "POST"])

        self.add_custom_routes()

    def process_plugins(self):
        self.screens = {s["name"]: {"web": s["web"], "enabled": s["enabled"]}
                         for s in getPlugins(True)}

    def add_custom_routes(self):
        sc = self.screens
        addons = [(x, sc[x]["web"]) for x in sc if sc[x]["web"]]
        for screen, addon in addons:
            plugin = imp.load_module("web", *addon)
            for route in plugin.bindings:
                self.route(route[0], callback=getattr(plugin, route[1]), method=route[2])
            self.custom_screens[screen] = plugin.bindings[0][0]

    def valid_screen(self, screen):
        return (screen is not None and
                screen in self.infoscreen.availablescreens)

    def show_current(self):
        return "Hello World! {}".format(self.infoscreen.scrmgr.current)

    def list_screens(self):

        form = request.forms.get("submit", False)
        if form:
            action, screen = form.split("+")
            if action == "enable":
                r = requests.get("http://localhost:8089/api/{}/enable".format(screen))

            elif action == "disable":
                r = requests.get("http://localhost:8089/api/{}/disable".format(screen))

            elif action == "configure":
                redirect("/configure/{}".format(screen))

            elif action == "custom":
                url = self.custom_screens.get(screen, "/")
                redirect(url)

        self.process_plugins()
        sc = self.screens
        active = sorted([x for x in sc if sc[x]["enabled"]])
        inactive = sorted([x for x in sc if x not in active])
        return template("all_screens.tpl", screens=sc)

    def change_screen(self, screen=None):
        if self.valid_screen(screen):
            self.infoscreen.scrmgr.current = screen

        return self.show_current()

    def update_config(self, screen=None):
        if screen in self.screens:
            conffile = os.path.join(self.folder, "screens", screen, "conf.json")
            params = json.load(open(conffile, "r"))
            enabled = "checked /" if self.screens[screen]["enabled"] else " /"
            conf = json.dumps(params.get("params", dict()), indent=4)

            return template(SCREEN_CONFIG, screen=screen, conf=conf, enabled=enabled)

    def save_config(self, screen):

        change_params = False

        try:
            params = json.loads(request.forms.get("params"))
        except ValueError:
            return "INVALID JSON"
        else:
            # enabled = bool(request.forms.get("enabled"))
            conffile = os.path.join(self.folder, "screens", screen, "conf.json")
            conf = json.load(open(conffile, "r"))
            # if conf["enabled"] != enabled:
            #     change_state = True

            if conf.get("params", dict()) != params:
                change_params = True

            if change_params:
                r = requests.post("http://localhost:8089/api/{}/configure".format(screen), json=params)
                print r.text
                # conf["enabled"] = enabled
                # conf["params"] = params
                # with open(conffile, "w") as config:
                #     json.dump(conf, config, indent=4)
                #
                # self.screens[screen]["enabled"] = enabled

            # if change_state:
            #     if enabled:
            #         self.infoscreen.add_screen(screen)
            #
            #     else:
            #         self.infoscreen.remove_screen(screen)
            #
            # if change_params and enabled:
            #     self.infoscreen.reload_screen(screen)

            # return self.update_config(screen)
            redirect("/")


def start_web(appdir):
    infoapp = App.get_running_app()

    while infoapp is None:
        infoapp = App.get_running_app()
        sleep(1)

    ws = InfoScreenWebServer(infoapp, appdir)

    ws.run(host="localhost", port=8088, debug=True)

def start_api(appdir):
    infoapp = App.get_running_app()

    while infoapp is None:
        infoapp = App.get_running_app()
        sleep(1)

    ws = InfoScreenAPI(infoapp, appdir)

    ws.run(host="localhost", port=8089, debug=True)

def start_web_server(appdir):
    os.chdir(appdir)
    t = Thread(target=start_web, args=(appdir, ))
    t.daemon = True
    t.start()

    api = Thread(target=start_api, args=(appdir, ))
    api.daemon = True
    api.start()
