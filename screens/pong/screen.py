'''Pong Game screen for the Raspberry Pi Information Screen.

Pong Game code is based on the code on the Kivy website:
  http://kivy.org/docs/tutorials/pong.html
'''
from time import sleep

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty,\
    ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App

from core.bglabel import BGLabelButton


class WinLabel(BGLabelButton):
    pass


class PongPaddle(Widget):
    score = NumericProperty(0)

    def bounce_ball(self, ball):
        if self.collide_widget(ball):
            vx, vy = ball.velocity
            offset = (ball.center_y - self.center_y) / (self.height / 2)
            bounced = Vector(-1 * vx, vy)
            vel = bounced * 1.1
            ball.velocity = vel.x, vel.y + offset


class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class PongScreen(Screen):
    ball = ObjectProperty(None)
    player1 = ObjectProperty(None)
    player2 = ObjectProperty(None)
    pongfloat = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PongScreen, self).__init__(**kwargs)
        try:
            self.winscore = int(kwargs["params"]["winningscore"])
            if self.winscore < 0:
                self.winscore = 5
        except ValueError:
            self.winscore = 5

        self.speed = 8

    def lock(self, locked=True):
        app = App.get_running_app()
        app.base.toggle_lock(locked)

    def on_enter(self):
        self.ball.center = self.center
        self.player1.center_y = self.center_y
        self.player2.center_y = self.center_y
        self.lbl = WinLabel(text="Press to start!",
                            pos=(200, 160),
                            bgcolour=[0, 0, 0, 0.8])
        cb = lambda instance, lbl=self.lbl: self.start(lbl)
        self.lbl.bind(on_press=cb)
        self.pongfloat.add_widget(self.lbl)

    def start(self, lbl):
        self.pongfloat.remove_widget(lbl)
        self.serve_ball()
        Clock.schedule_interval(self.update, 1.0 / 30.0)
        self.lock(True)

    def restart(self, vel, lbl):
        self.lock(True)
        self.pongfloat.remove_widget(lbl)
        self.player1.score = 0
        self.player2.score = 0
        self.serve_ball(vel)

    def on_leave(self):
        Clock.unschedule(self.update)
        self.player1.score = 0
        self.player2.score = 0
        for c in self.pongfloat.children:
            if isinstance(c, WinLabel):
                self.pongfloat.remove_widget(c)

    def win(self, player):

        self.lbl = WinLabel(text="Player {} wins!".format(player),
                            pos=(200, 160),
                            bgcolour=[0, 0, 0, 0.8])

        v = (0 - self.speed, 0) if player == 1 else (self.speed, 0)

        cb = lambda instance, v=v, lbl=self.lbl: self.restart(v, lbl)

        self.lbl.bind(on_press=cb)

        self.pongfloat.add_widget(self.lbl)
        self.ball.velocity = (0, 0)
        self.ball.center = self.center

        Clock.schedule_once(self.reset, 2)

    def reset(self, *args):
        self.lock(False)
        self.lbl.text = "Press to restart"

    def serve_ball(self, vel=None):
        self.ball.center = self.center
        if vel is None:
            self.ball.velocity = (self.speed, 0)
        else:
            self.ball.velocity = vel

    def update(self, dt):
        self.ball.move()

        # bounce of paddles
        self.player1.bounce_ball(self.ball)
        self.player2.bounce_ball(self.ball)

        # bounce ball off bottom or top
        if (self.ball.y < self.y) or (self.ball.top > self.top):
            self.ball.velocity_y *= -1

        # went of to a side to score point?
        if self.ball.x < self.x:
            self.player2.score += 1
            if self.player2.score == self.winscore:
                self.win(2)
            else:
                self.serve_ball(vel=(self.speed, 0))
        if self.ball.x > self.width:
            self.player1.score += 1
            if self.player1.score == self.winscore:
                self.win(1)
            else:
                self.serve_ball(vel=(0 - self.speed, 0))

    def on_touch_move(self, touch):
        if touch.x < self.width / 3:
            self.player1.center_y = touch.y
        if touch.x > self.width - self.width / 3:
            self.player2.center_y = touch.y
