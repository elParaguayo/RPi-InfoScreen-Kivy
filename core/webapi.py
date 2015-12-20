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

from bottle import Bottle, template, request, response

from getplugins import getPlugins

class InfoScreenAPI(Bottle):
    def __init__(self, infoscreen, folder):
        super(InfoScreenAPI, self).__init__()
        self.infoscreen = infoscreen.base
        self.folder = folder
        self.process_plugins()
        self.route("/", callback=self.default)
        self.error_handler[404] = self.unknown

        # API METHODS
        self.route("/api/<screen>/configure",
                   callback=self.get_config,
                   method="GET")
        self.route("/api/<screen>/configure",
                   callback=self.set_config,
                   method="POST")
        self.route("/api/<screen>/enable",
                   callback=self.enable_screen)
        self.route("/api/<screen>/disable",
                   callback=self.disable_screen)


    def process_plugins(self):
        self.screens = {s["name"]: {"web": s["web"], "enabled": s["enabled"]}
                         for s in getPlugins(True)}

    def api_success(self, data):

        return {"status": "success",
                  "data": data}

    def api_error(self, message):

        return {"status": "error",
                  "message": message}

    def get_config(self, screen):
        conffile = os.path.join(self.folder, "screens", screen, "conf.json")
        if os.path.isfile(conffile):
            conf = json.load(open(conffile, "r"))
            result = self.api_success(conf.get("params", dict()))

        else:
            result = self.api_error("No screen called: {}".format(screen))

        return json.dumps(result)

    def set_config(self, screen):
        try:
            js = request.json

            if js is None:
                return self.api_error("No JSON data received. "
                                      "Check headers are set correctly.")

            else:
                success = self.save_config(screen, js)

                if success:
                    self.infoscreen.reload_screen(screen)
                    return self.api_success(json.dumps(js))

                else:
                    return self.api_error("Unable to save configuration.")

        except:
            return self.api_error("Invalid data received.")

    def default(self):
        result = self.api_error("Invalid method.")
        return json.dumps(result)

    def unknown(self, addr):
        return self.default()

    def update_config(self, screen=None):
        if screen in self.screens:
            conffile = os.path.join(self.folder, "screens", screen, "conf.json")
            params = json.load(open(conffile, "r"))
            enabled = "checked /" if self.screens[screen]["enabled"] else " /"
            conf = json.dumps(params.get("params", dict()), indent=4)

            return template(SCREEN_CONFIG, screen=screen, conf=conf, enabled=enabled)

    def save_config(self, screen, params):
        try:
            conffile = os.path.join(self.folder, "screens", screen, "conf.json")
            conf = json.load(open(conffile, "r"))
            conf["params"] = params
            with open(conffile, "w") as config:
                json.dump(conf, config, indent=4)
            return True
        except:
            return False

    def enable_screen(self, screen):
        try:
            conffile = os.path.join(self.folder, "screens", screen, "conf.json")
            with open(conffile, "r") as f_config:
                conf = json.load(f_config)
            conf["enabled"] = True
            with open(conffile, "w") as f_config:
                json.dump(conf, f_config, indent=4)
            try:
                self.infoscreen.add_screen(screen)
            except:
                raise
            return self.api_success("{} screen enabled.".format(screen))
        except:
            return self.api_error("Could not enable {} screen.".format(screen))

    def disable_screen(self, screen):
        try:
            conffile = os.path.join(self.folder, "screens", screen, "conf.json")
            with open(conffile, "r") as f_config:
                conf = json.load(f_config)
            conf["enabled"] = False
            with open(conffile, "w") as f_config:
                json.dump(conf, f_config, indent=4)
            self.infoscreen.remove_screen(screen)
            return self.api_success("{} screen disabled.".format(screen))
        except:
            return self.api_error("Could not disable {} screen.".format(screen))

    # API METHODS ############################################################



def start_web(appdir):
    infoapp = App.get_running_app()

    while infoapp is None:
        infoapp = App.get_running_app()
        sleep(1)

    ws = InfoScreenWebServer(infoapp, appdir)

    ws.run(host="localhost", port=8088, debug=True)

def start_web_server(appdir):
    os.chdir(appdir)
    t = Thread(target=start_web, args=(appdir, ))
    t.daemon = True
    t.start()
