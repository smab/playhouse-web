import imp
import os
import tornado.escape
import tornado.ioloop
import datetime


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

def reply_wrong_player(game, handler):
    if handler in game.players:
        print("Wrong player")
        send_msg(handler, {'error':'Not your turn!'})
    else:
        print("Spectator")
        send_msg(handler, {'error':'You are not a player!'})

def game_over(game, winnerH, coords = frozenset()):
    if winnerH == None:
        send_msgs(game.players,     {'state': 'gameover'})
        send_msgs(game.connections, {'message': 'The game tied'})
        print("The game tied")

    else:
        winner = game.players.index(winnerH)
        send_msg(winnerH, {'state': 'gameover', 'message': 'You won!'})
        send_msgs((p for p in game.players if p != winnerH),
                          {'state': 'gameover', 'message': 'You lost!'})
        send_msgs(game.get_spectators(), {'message': "Player %d won" % (winner + 1)})
        print("Player %d wins!" % winner)

    changes = []
    for (x,y) in coords:
        changes += [ { 'x': x, 'y': y,             'change': { 'alert': 'lselect' } },
                     { 'x': x, 'y': y, 'delay': 3, 'change': { 'alert': 'none'    } } ]
    game.send_lamp_multi(changes)

    game.player = None
    set_timeout(datetime.timedelta(seconds = len(coords) + 3), game.reset)

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
    pass

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
    print("parse_color:", color) 
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

def rgb_to_hsl(r, g, b):
    # via http://en.wikipedia.org/wiki/HSL_and_HSV
    print("rgb_to_hsl:", r, g, b) 
    M, m = max(r,g,b), min(r,g,b)
    c = M - m

    print("rgb_to_hsl:", M, m, c) 
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
    sat = c / divisor * 256

    print("rbg_to_hsl:", [hue, sat, lum]) 
    return (int(hue), int(sat), int(lum))

def to_lamp_hue(hsl):
  return int(hsl[0] * 65536 / 360)


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
        self.players     = []

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
        # Print response
        print(self.client.getresponse().read().decode())

    def send_lamp(self, x, y, change):
        if 'hue' in change: 
            if type(change['hue']) is list: 
                raise TypeError("Aoeu") 
        self.send_lamp_multi([ { 'x': x, 'y': y, 'change': change } ])

    def send_lamp_all(self, change):
        if 'hue' in change: 
            if type(change['hue']) is list: 
                raise TypeError("Aoeu") 
        json    = tornado.escape.json_encode(change)
        headers = add_auth_cookie({'Content-Type': 'application/json'})
        self.client.request("POST", "/lights/all", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())

    def reset_lamp_all(self):
        self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0 })

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

    def try_get_new_players(game, n):
        for _ in range(n):
            game.add_player(game.queue.get_first())

    def get_spectators(self):
        """
        Generator for spectators, handy for use with `send_msg_many`.
        """
        for h in self.connections:
            if h not in self.players:
                yield h

    # Feel free to override these, but make sure to call the super function
    # directly if you do, so that the connection-managing logic still works.
    def add_player(self, handler):
        print("Add player: %s" % handler)

        if handler != None:
            player = self.players.index(None)
            self.players[player] = handler

            print("Connection %s as player %d" % (handler, player))
            send_msg(handler, { 'state':   'playing',
                                'playerId': player+1, 
                                'message': 'You are player %d' % (player + 1) })
            self.sync(handler)

    def remove_player(self, handler):
        player = self.players.index(handler)
        self.players[player] = None
        # try to replace the player with one from the queue
        self.add_player(self.queue.get_first())


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
        if handler not in self.players:
            self.sync(handler)

            if None in self.players:
                top = self.queue.get_first()
                self.add_player(top)


    def on_close(self, handler):
        """
        Event: a client has lost/closed their connection

        If you override this, you likely want to invoke this method manually!
        """
        self.connections -= {handler}

        if handler in self.players:
            self.remove_player(handler)
           

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
                         'message': "The game got destroyed!"})

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
        vars = self.template_vars 
        vars['grid_x'] = max(0, int(config['grid_x']))
        vars['grid_y'] = max(0, int(config['grid_y']))
        vars['cell_w'] = max(0, int(config['cell_w']))
        vars['cell_h'] = max(0, int(config['cell_h']))
        vars['color_empty'] = config['color_empty']
        #self.destroy() 
        self.reset() 

        
    def set_description(self, handler):
        """
        Sends the game description to the client.
        """
        pass 
