import imp
import os


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

class Game:
    config_file = "defaultconfig.html"
    template_file = "default.html"
    template_vars = {
        'module_name': '<name not set>'
    }

    def __init__(self, client):
        self.client = client

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
