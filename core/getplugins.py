import imp
import os
import json

# Constants that are used to find plugins
PluginFolder = "./screens"
PluginScript = "screen.py"
ScreenConf = "conf.json"


def getPlugins():
    plugins = []
    a = 1

    # Get the contents of the plugin folder
    possibleplugins = os.listdir(PluginFolder)

    # Loop over it
    for i in possibleplugins:
        location = os.path.join(PluginFolder, i)

        # Ignore anything that doesn't meet our criteria
        if (not os.path.isdir(location) or PluginScript not in
                                           os.listdir(location)):
            continue

        # Load the module info into a variavls
        inf = imp.find_module("screen", [location])

        # Plugin needs a conf file.
        if ScreenConf in os.listdir(location):
            conf = json.load(open(os.path.join(location, ScreenConf)))

            # See if the user has disabled the plugin.
            if conf.get("enabled", False):

                # Get the KV file text
                kv = open(os.path.join(location, conf["kv"])).readlines()

                # Custom dict for the plugin
                plugin = {"name": i,
                          "info": inf,
                          "id": a,
                          "screen": conf["screen"],
                          "dependencies": conf.get("dependencies", list()),
                          "kv": kv,
                          "params": conf.get("params", None)}

                plugins.append(plugin)
                a = a + 1

    # We're done so return the list of available/enabled plugins
    return plugins
