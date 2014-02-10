import tornado.ioloop
import tornado.web
import tornado.websocket

import http.client

import lightgames


client = None
headers = {
    'Content-Type': 'application/json', 
    'Accept': '*/*', 
}

config = {
    'game_name': 'default',
    'game_path': ['src/games'],

    'lampdest': 'localhost',
    'lampport': 4711,

    'serverport': 8080
}
config['websocket_addr'] = 'localhost:%d' % config['serverport']
game = None


class MainHandler(tornado.web.RequestHandler): 
    def get(self):
        template_vars = {'socket_addr': config['websocket_addr']}
        template_vars.update(game.template_vars)
        self.render(game.template_file, **template_vars)


class CommunicationHandler(tornado.websocket.WebSocketHandler): 
    def open(self): 
        print("Client connected") 
        game.on_connect(self)

    def on_message(self, message): 
        print("Received message:", message)
        game.on_message(self, message)

    def on_close(self): 
        game.on_close(self)
        pass 


def initialize():
    global config
    global game

    with open('config.json', 'r') as file:
        cfg = tornado.escape.json_decode(file.read())

    config.update(cfg)

    print("Connecting to lamp server (%s:%d)" % (config['lampdest'], config['lampport']))
    client = http.client.HTTPConnection(config['lampdest'], config['lampport'])

    game = lightgames.load(config["game_name"], config["game_path"], client)
    game.init()


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/websocket", CommunicationHandler), 
], template_path='templates')

if __name__ == "__main__":
    initialize()

    print("Starting web server (port %d)" % config['serverport'])
    application.listen(config['serverport'])
    tornado.ioloop.IOLoop.instance().start()
