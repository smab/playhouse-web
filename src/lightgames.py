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
        'cell_w':      74,
        'cell_h':      74,
        'color_empty': "#222"
    }


    def __init__(self, client):
        self.client = client


    def send_lamp(self, x, y, change):
        self.send_lamp_multi([ { 'x': x, 'y': y, 'change': change } ])

    def send_lamp_all(self, change):
        json    = tornado.escape.json_encode(change)
        headers = {'Content-Type': 'application/json'}
        self.client.request("POST", "/lights/all", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())

    def send_lamp_multi(self, changes):
        json    = tornado.escape.json_encode(changes)
        headers = {'Content-Type': 'application/json'}
        self.client.request("POST", "/lights", json, headers)
        # Print response
        print(self.client.getresponse().read().decode())


    def init(self):
        pass

    def destroy(self):
        pass

    def on_connect(self, handler):
        pass

    def on_message(self, handler, message):
        pass

    def on_close(self, handler):
        pass

    def set_queue(self, queue):
        self.queue = queue

    def set_options(self, config):
        pass
