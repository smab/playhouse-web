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

import datetime
import imp
import io
import os
import traceback

import tornado.concurrent
import tornado.escape
import tornado.gen
import tornado.ioloop

import PIL.Image


def load(name, path, client):
    file, pathname, description = imp.find_module(name, path)
    mod = imp.load_module(name, file, pathname, description)

    return mod.create(client)

def get_games(paths):
    games = []
    for path in paths:
        try:
            for file in os.listdir(path):
                if file.endswith(".py"):
                    games += [file.split('.')[0]]
        except FileNotFoundError:
            pass

    return games


#### Game API ###################################
# This is the API that game modules make use of (by extending the Game class
# and invoking the other functions provided here).

def send_msg(handler, msg):
    if handler != None:
        handler.write_message(tornado.escape.json_encode(msg))

def send_msgs(handlers, msg):
    for h in handlers:
        send_msg(h, msg)

def send_msgs_animation(handlers, coords, message, callback = None, revert = False,
                            ms_between = 500, ms_transition = 600, ms_revert = 500):
    for i, (x,y) in enumerate(coords):
        send_msgs(handlers, dict(message,
                                 x = x,
                                 y = y,
                                 delay = i * ms_between,
                                 transitiontime = ms_transition // 100))
        if revert:
            send_msgs(handlers, dict(message,
                                     power = False,
                                     x = x,
                                     y = y,
                                     delay = i*ms_between + ms_revert,
                                     transitiontime = ms_transition // 100))

    if callback:
        ms = (len(coords) - 1)*ms_between + (ms_revert if revert else 0)
        set_timeout(datetime.timedelta(milliseconds = ms), callback)

def set_timeout(deadline, callback):
    """
    Runs `callback` at the time `deadline` from Tornado's I/O loop.

    Thin wrapper over Tornado's `IOLoop.add_timeout`.
    """
    ioloop = tornado.ioloop.IOLoop.instance()
    return ioloop.add_timeout(deadline, callback)

def remove_timeout(handler): 
    """ 
    Removes the given timeout. 

    Thin wrapper over Tornado's `IOLoop.add_timeout`. 
    """
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.remove_timeout(handler) 

def get_grid_size():
    import manager
    return (manager.grid['height'], manager.grid['width'])

def add_auth_cookie(headers):
    if light_cookie and 'user' in light_cookie:
        headers['Cookie'] = light_cookie['user'].output(attrs=[], header='')
    return headers

light_cookie = None

def rgb_to_xyz(r, g, b):
    X =  1.076450 * r - 0.237662 * g + 0.161212 * b
    Y =  0.410964 * r + 0.554342 * g + 0.034694 * b
    Z = -0.010954 * r - 0.013389 * g + 1.024343 * b

    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
    return x, y, Z

def parse_color(color):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

def rgb_to_hsl(r, g, b):
    # via http://en.wikipedia.org/wiki/HSL_and_HSV
    M, m = max(r,g,b), min(r,g,b)
    c = M - m

    if c == 0:
        hue = 0
    elif M == r: # ↓ may be <0, so use + and % to make sure that it is in [0,360]
        hue = ((g - b)/c * 360 + 360*6) % (360 * 6)
    elif M == g:
        hue =  (b - r)/c * 360 + (360 * 2)
    elif M == b:
        hue =  (r - g)/c * 360 + (360 * 4)

    hue /= 6
    lum = M/2 + m/2
    divisor = 2 * (lum if lum < 128 else 256 - lum)
    if divisor == 0: return (0, 0, 0)
    sat = c / divisor * 255

    return (int(hue), int(sat), int(lum))

def to_lamp_hue(hsl):
    return int(hsl[0] * 65536 / 360)

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

def validate_xy(f): 
    def helper(self, handler, message):
        if 'x' in message and 'y' in message:
            x, y = message['x'], message['y']
            width  = self.template_vars['grid_x']
            height = self.template_vars['grid_y']
            if x >= 0 and x < width and \
               y >= 0 and y < height:
                return f(self, handler, message)
        send_msg(handler, {'error':'Invalid move!'})

    return helper

class Game:
    config_file = "defaultconfig.html"
    template_file = "default.html"
    template_vars = {
        'module_name': '<name not set>',
        'title':       'Default', 
        'cell_w':      64,
        'cell_h':      64,
        'grid_x':       None, 
        'grid_y':       None, 
        'color_empty': "#222222",
        'color_hover': "#999999"
    }

    def __init__(self, client):
        # State variables, to be used by the game
        self.queue       = None
        self.connections = set()

        # Internal variables
        self.client      = client

    # Internal, do not override/use
    def set_queue(self, queue):
        self.queue = queue
        queue.enqueue_callback = self.on_enqueue


    # Methods for updating the lamps
    def send_lamp_multi(self, changes):
        json    = tornado.escape.json_encode(changes)
        headers = add_auth_cookie({'Content-Type': 'application/json'})
        self.client.request("POST", "/lights", json, headers)
      # # Print response
      # print(self.client.getresponse().read().decode())
        # Get response
        self.client.getresponse().read().decode()

    def send_lamp(self, x, y, change):
        self.send_lamp_multi([ { 'x': x, 'y': y, 'change': change } ])

    def send_lamp_all(self, change):
        json    = tornado.escape.json_encode(change)
        headers = add_auth_cookie({'Content-Type': 'application/json'})
        self.client.request("POST", "/lights/all", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())

    def reset_lamp_all(self):
        self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0, 'blink':False })

    def send_lamp_animation(self, coords, change, callback = None, revert = False,
                            ms_between = 500, ms_transition = 600, ms_revert = 500):
        changes = []
        for i, (x,y) in enumerate(coords):
            changes += [ { 'x': x,
                           'y': y,
                           'delay': i * ms_between / 1000,
                           'change': dict(change, transitiontime = ms_transition // 100, bri=255)} ]
            if revert:
                changes += [ { 'x': x,
                               'y': y,
                               'delay': i * ms_between / 1000 + ms_revert / 1000,
                               'change': { 'sat':0, 'bri':0,
                                           'transitiontime': ms_transition // 100} } ]
        self.send_lamp_multi(changes)

        if callback:
            ms = (len(coords) - 1)*ms_between + (ms_revert if revert else 0)
            set_timeout(datetime.timedelta(milliseconds = ms), callback)


    # Other utility methods for abstracting snippets commonly used in games
    def sync_all(self):
        for handler in self.connections:
            self.sync(handler)

    # Feel free to override these, but make sure to call the super function
    # directly if you do, so that the connection-managing logic still works.
    def on_connect(self, handler):
        """
        Event: a client has connected

        If you override this, you likely want to invoke this method manually!
        """
        self.connections |= {handler}
        send_msg(handler, { 'state':   'spectating',
                            'message': 'You are a spectator!' })
        # Sync game
        self.sync(handler)

    def on_enqueue(self, handler):
        """
        Event: a client has been enqueued

        If you override this, you likely want to invoke this method manually!
        """
        pass


    def on_close(self, handler):
        """
        Event: a client has lost/closed their connection

        If you override this, you likely want to invoke this method manually!
        """
        self.connections -= {handler}
           

    # Override these to implement the actual game
    def init(self):
        """
        Initialize this game for the first time.  This is called only once
        when the game object is created, and acts as an ad-hoc constructor.
        """
        self.reset()

    def reset(self):
        """
        Reset this game to prepare for a new session.  Try to fetch new
        players for the new game.  This is called after each game has been
        completed. If you make changes to the start board (e.g. Othello), make 
        sure to sync all clients. 
        """
        pass

    def destroy(self):
        """
        Destroy this game instance.  This is called only once when the game is
        unloaded because of a configuration change, and marks the final
        interaction with this instance.
        """
        print("lightgames: destroy", self.connections)
        for h in self.connections:
            send_msg(h, {'state'  : "destroyed",
                         'overlaymessage': "Game changed, reloading..."})

    def on_message(self, handler, message):
        """
        Event: game-related JSON message was received.  This is where you want
        to implement the actual game logic.
        """
        pass

    def sync(self, handler):
        """
        Synchronize `handler` with the current state of the board/game.  See
        also the `sync_all` utility for synchronizing all currently-connected
        clients.
        """
        pass

    def set_options(self, config):
        """
        The game options were updated; update instance variables reflecting
        this here.  Return a string with an error message if the configuration
        is bad/invalid. 

        If you override this, you likely want to invoke this method manually!
        """
        tvars = self.template_vars 
        if 'grid_x' in config: tvars['grid_x'] = max(0, int(config['grid_x']))
        if 'grid_y' in config: tvars['grid_y'] = max(0, int(config['grid_y']))
        if 'cell_w' in config: tvars['cell_w'] = max(0, int(config['cell_w']))
        if 'cell_h' in config: tvars['cell_h'] = max(0, int(config['cell_h']))
        if 'color_empty' in config: tvars['color_empty'] = config['color_empty']
        self.reset() 

        
    def set_description(self, handler):
        """
        Sends the game description to the client.
        """
        pass 


class _CancelledError(Exception):
    pass

class GIFAnimation:

    def __init__(self, game):
        self.game = game
        self.running = False
        self.io_loop = tornado.ioloop.IOLoop.current()
        self.timeout_handle = None
        self.wait_future = None

    @tornado.gen.coroutine
    def run_animation(self, gif_data, bounds=None, offset=(0, 0), loop=float('inf'),
                      transitiontime=0, transparentcolor=(0, 0, 0), on_frame=None):
        if self.running:
            return False

        try:
            cur_pos = gif_data.tell()
            copied_data = io.BytesIO(gif_data.read())
            gif_data.seek(cur_pos)

            self.running = True

            web_buffer = []

            if on_frame is None:
                def on_frame(xy, color, is_transparent):
                    x, y = xy
                    web_buffer.append({'x': x, 'y': y, 'color': color, 'power': not is_transparent})

            image = PIL.Image.open(copied_data)
            offset_x, offset_y = offset

            while loop >= 0:
                try:
                    frame = 0
                    while True:
                        image.seek(frame)
                        rgb_image = image.convert('RGBA')
                        width, height = rgb_image.size

                        del web_buffer[:]

                        message_buffer = []
                        for i, (r, g, b, a) in enumerate(rgb_image.getdata()):
                            if a == 0:
                                continue

                            x, y = i % width + offset_x, i // width + offset_y

                            if (bounds is not None
                                    and (not 0 <= x <= bounds[0] or not 0 <= y <= bounds[1])):
                                continue

                            color = r, g, b

                            if on_frame is not None:
                                on_frame((x, y), color, color == transparentcolor)

                            message_buffer.append({
                                "x": x,
                                "y": y,
                                "change": {
                                    # set bri=255 for set pixels and bri=0 for transparent ones
                                    "rgb": color if color != transparentcolor else [0,0,0],
                                    "bri": 255 if color != transparentcolor else 0,
                                    "transitiontime": transitiontime
                                  # "on": color != transparentcolor
                                }
                            })

                        if message_buffer:
                            self.game.send_lamp_multi(message_buffer)

                        if web_buffer:
                            send_msgs(self.game.connections, web_buffer)

                        self.wait_future = tornado.concurrent.Future()
                        self.timeout_handle = self.io_loop.add_timeout(
                            datetime.timedelta(milliseconds=image.info['duration']),
                            lambda: self.wait_future.set_result(None))
                        yield self.wait_future
                        self.timeout_handle = None

                        frame += 1
                except EOFError:
                    pass

                loop -= 1
        except _CancelledError:
            return False
        except Exception:
            traceback.print_exc()
            raise
        else:
            return True
        finally:
            image.close()
            self.running = False

    def cancel(self):
        if not self.running:
            return False

        if self.timeout_handle is not None:
            self.io_loop.remove_timeout(self.timeout_handle)
            self.timeout_handle = None
        if self.wait_future is not None and not self.wait_future.done():
            self.wait_future.set_exception(_CancelledError)
        return True

    def close(self):
        self.cancel()

