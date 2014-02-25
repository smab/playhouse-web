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
        template_vars = {'socket_addr': config['websocket_addr']}
        template_vars.update(game.template_vars)
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
        queue.on_message(self, message)
        game.on_message(self, message)

    def on_close(self): 
        print("Client disconnected (%s)" % self)
        if self in self.connections:
            queue.on_close(self)
            game.on_close(self)
            self.connections.remove(self)


class ConfigHandler(tornado.web.RequestHandler):
    def post(self):
        global config
        global client
        global game

        load_game = False
        cfg = tornado.escape.json_decode(self.request.body)
        print("Config: %s" % cfg)

        config.update(cfg)

        if 'lampdest' in cfg or 'lampport' in cfg:
            print("Connecting to lamp server (%s:%d)" % (config['lampdest'], config['lampport']))
            client = http.client.HTTPConnection(config['lampdest'], config['lampport'])
            load_game = True

        if 'game_name' in cfg:
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

        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode({"state": "success"}))


class GameConfigHandler(tornado.web.RequestHandler):
    def post(self):
        global game

        cfg = tornado.escape.json_decode(self.request.body)
        print("Config: %s" % cfg)

        game.set_options(cfg)

        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode({"state": "success"}))


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
    (r"/", MainHandler),
    (r"/websocket", CommunicationHandler), 
    (r"/config", configinterface.ConfigHandler),
], template_path='templates', debug=True)

if __name__ == "__main__":
    initialize()

    print("Starting web server (port %d)" % config['serverport'])
    application.listen(config['serverport'])
    tornado.ioloop.IOLoop.instance().start()
    


