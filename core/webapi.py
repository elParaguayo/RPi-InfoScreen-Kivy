'''Web interface for the Raspberry Pi Information Screen.

   by elParaguayo

   This module defines the underlying API.

   Screens can define their own web pages for custom configuration by using
   methods available in this API.

   API format:

   [HOST]/api/<screenname>/configure
        GET: returns JSON format of user-configurable settings for screen
        POST: takes JSON format of updated configuration.

   [HOST]/api/<screenname>/enable
        GET: enable the selected screen

   [HOST]/api/<screenname>/disable
        GET: disable the selected screen

   [HOST]/api/<screenname>/view
        GET: change to screen


   API Response format:
     successful:
       {"status": "success",
        "data": [body of response]}

     unsuccessful:
       {"status": "error",
        "message": [Error message]}
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

        # Get reference to base screen object so API server can
        # access methods
        self.infoscreen = infoscreen.base

        # Get the folder path so we can access config files
        self.folder = folder

        # Get the list of screens
        #self.process_plugins()

        # Define our routes
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
        self.route("/api/<screen>/view",
                   callback=self.view)

    def api_success(self, data):
        """Base method for response to successful API calls."""

        return {"status": "success",
                  "data": data}

    def api_error(self, message):
        """Base method for response to unsuccessful API calls."""

        return {"status": "error",
                  "message": message}

    def get_config(self, screen):
        """Method to retrieve config file for screen."""

        # Define the path to the config file
        conffile = os.path.join(self.folder, "screens", screen, "conf.json")

        if os.path.isfile(conffile):

            # Get the config file
            with open(conffile, "r") as cfg_file:

                # Load the JSON object
                conf = json.load(cfg_file)

            # Return the "params" section
            result = self.api_success(conf.get("params", dict()))

        else:

            # Something's gone wrong
            result = self.api_error("No screen called: {}".format(screen))

        # Provide the response
        return json.dumps(result)

    def set_config(self, screen):

        try:
            # Get JSON data
            js = request.json

            if js is None:
                # No data, so provide error
                return self.api_error("No JSON data received. "
                                      "Check headers are set correctly.")

            else:
                # Try to save the new config
                success = self.save_config(screen, js)

                # If successfully saved...
                if success:

                    # Reload the screen with the new config
                    self.infoscreen.reload_screen(screen)

                    # Provide success notification
                    return self.api_success(json.dumps(js))

                else:
                    # We couldn't save new config
                    return self.api_error("Unable to save configuration.")

        except:
            # Something's gone wrong
            return self.api_error("Invalid data received.")

    def default(self):
        # Generic response for unknown requests
        result = self.api_error("Invalid method.")
        return json.dumps(result)

    def unknown(self, addr):
        return self.default()

    def view(self, screen):
        try:
            self.infoscreen.switch_to(screen)
            return self.api_success("Changed screen to: {}".format(screen))
        except:
            return self.api_error("Could not change screen.")


    # Helper Methods ###########################################################

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
            # Update status in config
            self.change_screen_state(screen, True)

            # Make sure the screen is added
            self.infoscreen.add_screen(screen)

            # Success!
            return self.api_success("{} screen enabled.".format(screen))

        except:

            # Something went wrong
            return self.api_error("Could not enable {} screen.".format(screen))

    def disable_screen(self, screen):
        try:
            # Update status in config
            self.change_screen_state(screen, False)

            # Make sure the screen is added
            self.infoscreen.remove_screen(screen)

            # Success!
            return self.api_success("{} screen disabled.".format(screen))
        except:

            # Something went wrong!
            return self.api_error("Could not disable {} screen.".format(screen))

    def change_screen_state(self, screen, enabled):

        # Build path to config
        conffile = os.path.join(self.folder, "screens", screen, "conf.json")

        # Load existing config
        with open(conffile, "r") as f_config:
            conf = json.load(f_config)

        # Change status to desired state
        conf["enabled"] = enabled

        # Save the updated config
        with open(conffile, "w") as f_config:
            json.dump(conf, f_config, indent=4)
