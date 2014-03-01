import tornado.ioloop
import tornado.web
import tornado.websocket

import http.client

import lightgames
import queue
import config as configinterface 

client = None
headers = {
    'Content-Type': 'application/json', 
}

# TODO Move to separate file, or fix so that 
# the configinterface also can get this 
config = {
    'game_name': 'default',
    'game_path': ['src/games'],

    'lampdest': 'localhost',
    'lampport': 4711,

    'serverport': 8080
}
config['websocket_addr'] = 'localhost:%d' % config['serverport']
game = None
queue = queue.Queue()


class MainHandler(tornado.web.RequestHandler): 
    def get(self):
        template_vars = { 'socket_addr': config['websocket_addr'] }

        template_vars.update(lightgames.Game.template_vars)  # Game defaults
        template_vars.update(game.template_vars)
        if 'title' not in template_vars:
            template_vars['title'] = template_vars.get('module_name', "Untitled game")

        self.render(game.template_file, **template_vars)


class CommunicationHandler(tornado.websocket.WebSocketHandler):
    connections = []

    def open(self):
        print("Client connected (%s)" % self)
        queue.on_connect(self)
        game.on_connect(self)
        self.connections += [self]

    def on_message(self, message):
        print("Received message:", message)
        obj = tornado.escape.json_decode(message)
        queue.on_message(self, obj)
        game.on_message(self, obj)

    def on_close(self):
        print("Client disconnected (%s)" % self)
        if self in self.connections:
            queue.on_close(self)
            game.on_close(self)
            self.connections.remove(self)


# TODO: Move to config.py?
class GameConfigHandler(tornado.web.RequestHandler):
    global config

    def get(self):
        global game
        template_vars = {
            'config_file': game.config_file,
            'game_name':   config['game_name'],
            'game_path':   tornado.escape.json_encode(config['game_path']),
            'game_list':   lightgames.get_games(config['game_path'])
        }

        template_vars.update(lightgames.Game.template_vars)  # Game defaults
        template_vars.update(game.template_vars)
        if 'title' not in template_vars:
            template_vars['title'] = template_vars.get('module_name', "Untitled game")

        template_vars['vars'] = template_vars;
        self.render('gameconfig.html', **template_vars)

    def post(self):
        global game
        cfg = {}
        for key,val in self.request.arguments.items():
            cfg[key] = self.get_argument(key)

        print("Config: %s" % cfg)

        load_game = False

        if 'game_name' in cfg and config['game_name']!=cfg['game_name']:
            config['game_name'] = cfg['game_name']
            load_game = True

        if load_game:
            print("Changing or restarting game")
            if game != None:
                game.destroy()
            queue.clear()

            for conn in CommunicationHandler.connections:
                conn.close()
            CommunicationHandler.connections = []

            game = lightgames.load(config["game_name"], config["game_path"], client)
            game.set_queue(queue)
            game.init()
        else:
            game.set_options(cfg)

        self.redirect("game")

def initialize():
    global config
    global client
    global game

    with open('config.json', 'r') as file:
        cfg = tornado.escape.json_decode(file.read())

    config.update(cfg)

    print("Connecting to lamp server (%s:%d)" % (config['lampdest'], config['lampport']))
    client = http.client.HTTPConnection(config['lampdest'], config['lampport'])

    game = lightgames.load(config["game_name"], config["game_path"], client)
    game.set_queue(queue)
    game.init()


application = tornado.web.Application([
    (r"/",            MainHandler),
    (r"/websocket",   CommunicationHandler),
    (r"/config",      configinterface.ConfigHandler),
    (r"/config/game", GameConfigHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': 'static'})
], template_path='templates', debug=True)

if __name__ == "__main__":
    initialize()

    print("Starting web server (port %d)" % config['serverport'])
    application.listen(config['serverport'])
    tornado.ioloop.IOLoop.instance().start()


