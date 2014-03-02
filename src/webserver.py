import tornado.ioloop
import tornado.web
import tornado.websocket

import http.client
import uuid

import lightgames
import manager
import config as configinterface

headers = {
    'Content-Type': 'application/json',
}


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        template_vars = {}
        template_vars.update(lightgames.Game.template_vars)  # Game defaults
        template_vars.update(manager.game.template_vars)
        if 'title' not in template_vars:
            template_vars['title'] = template_vars.get('module_name', "Untitled game")

        self.render('game/' + manager.game.template_file, **template_vars)


class CommunicationHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("Client connected (%s)" % self)
        manager.queue.on_connect(self)
        manager.game.on_connect(self)
        manager.connections += [self]

    def on_message(self, message):
        print("Received message:", message)
        obj = tornado.escape.json_decode(message)

        if   'queueaction' in obj: manager.queue.on_message(self, obj)
        elif 'gameaction'  in obj: manager.game.on_message(self, obj)
        else: print("## warn: no receiver for message!")

    def on_close(self):
        print("Client disconnected (%s)" % self)
        if self in manager.connections:
            manager.queue.on_close(self)
            manager.game.on_close(self)
            manager.connections.remove(self)


def initialize():
    with open('config.json', 'r') as file:
        cfg = tornado.escape.json_decode(file.read())

    manager.config.update(cfg)

    print("Connecting to lamp server (%s:%d)" % (manager.config['lampdest'], manager.config['lampport']))
    manager.client = http.client.HTTPConnection(manager.config['lampdest'], manager.config['lampport'])

    manager.load_game()


application = tornado.web.Application([
    (r"/",               MainHandler),
    (r"/websocket",      CommunicationHandler),
    (r"/config",         configinterface.ConfigHandler),
    (r"/config/login",   configinterface.ConfigLoginHandler),
    ("/config/setup",    configinterface.SetupConfigHandler), 
    (r"/config/game",    configinterface.GameConfigHandler),
    (r"/config/bridges", configinterface.BridgeConfigHandler),
    (r"/static/(.*)",    tornado.web.StaticFileHandler, {'path': 'static'})
], template_path='templates',
   cookie_secret=str(uuid.uuid4()),
   login_url="login",
   debug=True)

if __name__ == "__main__":
    initialize()

    print("Starting web server (port %d)" % manager.config['serverport'])
    application.listen(manager.config['serverport'])
    tornado.ioloop.IOLoop.instance().start()


