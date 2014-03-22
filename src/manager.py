import http.client

import queue
import lightgames
import config as webconfig

config = {
    'game_name': 'default',
    'game_path': ['src/games'],

    'lampdest': 'localhost',
    'lampport': 4711,

    'serverport': 8080,

    'stream_embedcode':''
}
grid = None
client = None
game = None
queue = queue.Queue()

connections = []


def connect_lampserver():
    print("Connecting to lamp server (%s:%d)" % (config['lampdest'], config['lampport']))
    return http.client.HTTPConnection(config['lampdest'], config['lampport'])


def load_game():
    global game
    global connections

    new_game = lightgames.load(config["game_name"], config["game_path"], client)

    if game != None:
        game.destroy()
    queue.clear()

    for conn in connections:
        conn.close()
    connections = []

    game = new_game
    game.set_queue(queue)
    game.init()


def fetch_grid_size():
    global grid

    response = webconfig.get_data(client, '/grid')
    grid = {
        k: response[k] for k in ('width', 'height')
    }
