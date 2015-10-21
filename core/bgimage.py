from kivy.uix.image import Image
from kivy.properties import ListProperty
from kivy.uix.behaviors import ButtonBehavior


class BGImage(Image):
    """Custom widget to faciliate the ability to set background colour
       to an image via the "bgcolour" property.
    """
    bgcolour = ListProperty([0, 0, 0, 0])
    fgcolour = ListProperty([0, 0, 0, 0])

    def __init__(self, **kwargs):
        super(BGImage, self).__init__(**kwargs)


class BGImageButton(ButtonBehavior, BGImage):
    """Add button behaviour to the BGImage widget."""
    pass
