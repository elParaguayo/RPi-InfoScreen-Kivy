# Module for Energenie switches using pigpio module
# All credit due to the original energenie.py scrip by Amy Mather
# See: https://github.com/MiniGirlGeek/energenie-demo/blob/master/energenie.py

import pigpio
from time import sleep

# The GPIO pins for the Energenie module
BIT1 = 17  # Board 11
BIT2 = 22  # Board 15
BIT3 = 16  # Board 16
BIT4 = 21  # Board 13

ON_OFF_KEY = 24  # Board 18
ENABLE = 25  # Board 22

# Codes for switching on and off the sockets
#        all     1       2       3       4
ON = ['1011', '1111', '1110', '1101', '1100']
OFF = ['0011', '0111', '0110', '0101', '0100']


class EnergenieControl(object):
    def __init__(self, **kwargs):
        self.host = kwargs.get("host", "")
        self.connect()
        self.setup()

    def connect(self):
        """Create an instance of the pigpio pi."""
        self.pi = pigpio.pi(self.host)

    def setup(self):
        """Clear the pin values before we use the transmitter."""
        if self.connected:
            self.pi.write(ON_OFF_KEY, False)
            self.pi.write(ENABLE, False)
            self.pi.write(BIT1, False)
            self.pi.write(BIT2, False)
            self.pi.write(BIT3, False)
            self.pi.write(BIT4, False)

    def __change_plug_state(self, socket, on_or_off):
        """Method to set up the pins and fire the transmitter."""
        state = on_or_off[socket][3] == '1'
        self.pi.write(BIT1, state)
        state = on_or_off[socket][2] == '1'
        self.pi.write(BIT2, state)
        state = on_or_off[socket][1] == '1'
        self.pi.write(BIT3, state)
        state = on_or_off[socket][0] == '1'
        self.pi.write(BIT4, state)
        sleep(0.1)
        self.pi.write(ENABLE, True)
        sleep(0.25)
        self.pi.write(ENABLE, False)

    def switch_on(self, socket):
        self.__change_plug_state(socket, ON)

    def switch_off(self, socket):
        self.__change_plug_state(socket, OFF)

    @property
    def connected(self):
        return self.pi.connected
