import queue
import lightgames


config = {
    'game_name': 'default',
    'game_path': ['src/games'],

    'lampdest': 'localhost',
    'lampport': 4711,

    'serverport': 8080
}
client = None
game = None
queue = queue.Queue()

connections = []


def load_game():
    global game
    global client
    global connections

    if game != None:
        game.destroy()
    queue.clear()

    for conn in connections:
        conn.close()
    connections = []

    game = lightgames.load(config["game_name"], config["game_path"], client)
    game.set_queue(queue)
    game.init()
