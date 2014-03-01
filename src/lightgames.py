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


    def __init__(self, client):
        self.client = client

    def set_queue(self, queue):
        self.queue = queue
        queue.enqueue_callback = self.on_enqueue


    def send_lamp_multi(self, changes):
        """ Update a set of lamps according to the given operations """
        json    = tornado.escape.json_encode(changes)
        headers = {'Content-Type': 'application/json'}
        self.client.request("POST", "/lights", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())

    def send_lamp(self, x, y, change):
        """ Convenience function for updating a single lamp """
        self.send_lamp_multi([ { 'x': x, 'y': y, 'change': change } ])

    def send_lamp_all(self, change):
        """ Update all lamps with the given lamp operation """
        json    = tornado.escape.json_encode(change)
        headers = {'Content-Type': 'application/json'}
        self.client.request("POST", "/lights/all", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())


    def init(self):
        """ Game initialization routine """
        pass

    def destroy(self):
        """
        Game cleanup routine.  After `destroy()` is called, this instance will
        never be re-used again for future games.
        """
        pass

    def set_options(self, config):
        pass


    def on_connect(self, handler):
        """ Event: a client has connected """
        pass

    def on_enqueue(self, handler):
        """ Event: a client has been enqueued """
        pass

    def on_close(self, handler):
        """ Event: a client has disconnected """
        pass

    def on_message(self, handler, message):
        """ Event: a game message from a client was received """
        pass
