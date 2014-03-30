import http.client
import ssl

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
light_pwd = None
light_cookie = None

client = None
client_status = None
game = None
queue = queue.Queue()

connections = []


def connect_lampserver(print_msg=True):
    if print_msg:
        print("Connecting to lamp server (%s:%d)" %
            (config['lampdest'], config['lampport']))

    if config.get('ssl', False):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(config['certfile'])
        conn = http.client.HTTPSConnection(
            config['lampdest'], config['lampport'], context=context)
    else:
        conn = http.client.HTTPConnection(config['lampdest'], config['lampport'])

    if light_pwd is not None:
        authenticate(conn)

    return conn


def authenticate(conn):
    global light_cookie

    print("Authenticating...")
    conn.request("POST", "/authenticate",
        body='{"username":"web", "password":"%s"}' % light_pwd)
    res = conn.getresponse()
    print(res.read())

    light_cookie = http.cookies.BaseCookie()
    for cookie in res.headers.get_all("Set-Cookie", []):
      light_cookie.load(cookie)

    lightgames.light_cookie = light_cookie


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

    try:
        response = webconfig.get_data(client, '/grid')
        grid = {
            k: response[k] for k in ('width', 'height')
        }
    except webconfig.GetException as e:
        return e.response
    return None
