from kivy.uix.behaviors import ButtonBehavior
from core.bglabel import BGLabel, BGLabelButton


class HiddenButton(ButtonBehavior, BGLabel):
    pass
