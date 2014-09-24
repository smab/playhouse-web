# Playhouse: Making buildings into interactive displays using remotely controllable lights.
# Copyright (C) 2014  John Eriksson, Arvid Fahlström Myrman, Jonas Höglund,
#                     Hannes Leskelä, Christian Lidström, Mattias Palo, 
#                     Markus Videll, Tomas Wickman, Emil Öhman.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PIL import Image
from tornado import gen
from tornado.ioloop import IOLoop
import time
import io

import lightgames


class Animator():

    def init(self, game, config):
        self.game = game
        self.config = config

        self.play = False
        try:
            self.data = open(self.config['animation_file'], 'rb').read()
        except FileNotFoundError:
            self.data = None

    def destroy(self):
        self.play = False

    def pause_animation(self):
        self.play = False

    @gen.engine
    def play_animation(self):
        if self.data is None:
            print("No idle animation")
            return

        self.play = True

        while self.play:
            try:
                gif = Image.open(io.BytesIO(self.data))
                (width, height) = gif.size

                self.grid = (width, height)
                self.transp_color = HTMLColorToRGB(self.config['color_off'])

                for frame in ImageSequence(gif):
                    # Break if animation turned off.
                    # Change this accordingly to wait for animation
                    # to finish before turning off/changing animation
                    if not self.play:
                        break
                    tt = int(self.config['transition_time'])
                    rgb_im = gif.convert("RGB")
                    # duration of frame is in milliseconds
                    dur = gif.info['duration']
                    buffer = []
                    for y in range(0, min(height,self.grid[1])):
                        for x in range(0, min(width,self.grid[0])):
                            x_im = x_grid = x
                            y_im = y_grid = y

                            # check boundaries that might be off after offset
                            if (0 <= x_im < width
                            and 0 <= x_grid < self.grid[0]
                            and 0 <= y_im < height
                            and 0 <= y_grid < self.grid[1]):
                                r, g, b = rgb_im.getpixel((x_im, y_im))
                                if (r, g, b) != self.transp_color:
                                    buffer += [{'x': x_grid, 'y': y_grid, \
                                                'change': {'rgb': (r,g,b), 'transitiontime':tt, 'on': True}}]
                                    lightgames.send_msgs(self.game.connections, \
                                                {'animator': True, 'x':x_grid, 'y':y_grid, 'color':(r,g,b), 'power':True})
                                else:
                                    buffer += [{'x': x_grid, 'y': y_grid, 'change': {'on': False}}]
                                    lightgames.send_msgs(self.game.connections, \
                                                {'animator': True, 'x':x_grid, 'y':y_grid, 'color':(r,g,b), 'power':False})

                    # only send if theres a lamp to be changed
                    if buffer:
                        self.game.send_lamp_multi(buffer)
                    yield gen.Task(IOLoop.instance().add_timeout, time.time() + (dur/1000.0))
            except IOError:
                print("Couldn't open image")

# Taken from http://code.activestate.com/recipes/266466/
# Edited for Python 3
def HTMLColorToRGB(colorstring):
    """ convert #RRGGBB to an (R, G, B) tuple """
    colorstring = colorstring.strip()
    if colorstring[0] == '#': colorstring = colorstring[1:]
    if len(colorstring) != 6:
        raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
    r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
    r, g, b = [int(n, 16) for n in (r, g, b)]
    return (r, g, b)

class ImageSequence:
    def __init__(self, im):
        self.im = im
    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError # end of sequence

