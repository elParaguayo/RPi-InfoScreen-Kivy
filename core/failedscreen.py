from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label


class FailedScreen(Screen):
    """Custom Screen to notify users where certain plugins have not installed
       correctly.
    """
    def __init__(self, **kwargs):
        super(FailedScreen, self).__init__(**kwargs)

        # Get details of the screens that have failed
        # Unmet dependencies
        self.dep = kwargs["dep"]
        # Other unhandled failures
        self.failed = kwargs["failed"]

        # Build our screen
        self.buildLabel()

    def buildLabel(self):
        mess = "One or more screens have not been initialised.\n\n"

        # Loop over screens with unmet dependencies
        if self.dep:
            mess += "The following screens have unmet dependencies:\n\n"
            for dep in self.dep:
                mess += "{0}: {1}\n".format(dep[0], ",".join(dep[1]))
            if self.failed:
                mess += "\n\n"

        # Loop over screens with other unhandled erros.
        if self.failed:
            mess += ("Errors were encountered trying to create the following "
                     "screens:\n\n")
            for f in self.failed:
                mess += "{0}: {1}\n".format(*f)

        # Create a label.
        lbl = Label(text=mess)

        # Display it.
        self.add_widget(lbl)
