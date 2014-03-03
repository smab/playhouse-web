import imp
import os
import tornado.escape


def load(name, path, client):
    file, pathname, description = imp.find_module(name, path)
    mod = imp.load_module(name, file, pathname, description)

    return mod.create(client)

def get_games(paths):
    games = []
    for path in paths:
        for file in os.listdir(path):
            if file.endswith(".py"):
                games += [file.split('.')[0]]

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

def reply_wrong_player(game, handler):
    if handler in game.players:
        print("Wrong player")
        send_msg(handler, {'error':'Not your turn!'})
    else:
        print("Spectator")
        send_msg(handler, {'error':'You are not a player!'})


class Game:
    config_file = "defaultconfig.html"
    template_file = "default.html"
    template_vars = {
        'module_name': '<name not set>',
        'cell_w':      64,
        'cell_h':      64,
        'color_empty': "#222",
        'color_hover': "#999"
    }


    # State variables, to be used by the game
    queue       = None
    connections = set()     # connections to sync the board with
    players     = []        # current players


    def __init__(self, client):
        self.client = client

    # Internal, do not override/use
    def set_queue(self, queue):
        self.queue = queue
        queue.enqueue_callback = self.on_enqueue


    # Methods for updating the lamps
    def send_lamp_multi(self, changes):
        json    = tornado.escape.json_encode(changes)
        headers = {'Content-Type': 'application/json'}
        self.client.request("POST", "/lights", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())

    def send_lamp(self, x, y, change):
        self.send_lamp_multi([ { 'x': x, 'y': y, 'change': change } ])

    def send_lamp_all(self, change):
        json    = tornado.escape.json_encode(change)
        headers = {'Content-Type': 'application/json'}
        self.client.request("POST", "/lights/all", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())

    def reset_lamp_all(self):
        self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0 })


    # Other utility methods for abstracting snippets commonly used in games
    def sync_all(self):
        for handler in self.connections:
            self.sync(handler)

    def try_get_new_players(game, n):
        for i in range(n):
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
                                'message': 'You are player %d' % (player + 1) })

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
        completed.
        """
        pass

    def destroy(self):
        """
        Destroy this game instance.  This is called only once when the game is
        unloaded because of a configuration change, and marks the final
        interaction with this instance.
        """
        for h in self.connections:
            send_msg(h, {'message':"The game got destroyed!"})

        connections = set()
        players     = []

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
        """
        pass
