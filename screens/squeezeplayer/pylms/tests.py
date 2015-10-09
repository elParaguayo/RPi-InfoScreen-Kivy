#!/usr/bin/env python

from pylms import server

s = server.Server("10.0.2.10")
s.connect()

print(s.get_players())

p = s.get_player("Lounge")
p.set_volume(10)

r = s.request("songinfo 0 100 track_id:94")
print(r)

r = s.request("trackstat getrating 1019")
print(r)
