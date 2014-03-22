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
grid = {'width':-1, 'height':-1}
client = None
client_status = None
game = None
queue = queue.Queue()

connections = []


def connect_lampserver(print_msg=True):
    if print_msg:
        print("Connecting to lamp server (%s:%d)" % (config['lampdest'], config['lampport']))
    return http.client.HTTPConnection(config['lampdest'], config['lampport'])


def check_client_status():
    global client
    global client_status

    client_status = "error"
    try:
        client.request("GET", "/status");
        response = client.getresponse()
        if response.status == 200:
            client_status = "connected"
        response.read()
        return True
    except:
        client = connect_lampserver(False)

    return False


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
