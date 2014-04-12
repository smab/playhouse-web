import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket

import uuid
import traceback

import lightgames
import manager
import config as configinterface


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        gamesession = self.get_cookie("gamesession")
        if gamesession == None:
            gamesession = str(uuid.uuid4())
            self.set_cookie("gamesession", gamesession)

        template_vars = {
                'stream_embedcode': manager.config['stream_embedcode'],
                'socketport': manager.config['serverport']
            }
        template_vars.update(lightgames.Game.template_vars)  # Game defaults
        template_vars.update(manager.game.template_vars)
        if 'title' not in template_vars:
            template_vars['title'] = template_vars.get('module_name', "Untitled game")
        template_vars['gamesession'] = gamesession

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
    config_file = manager.CONFIG_FILE
    try:
        with open(config_file, 'r') as file:
            cfg = tornado.escape.json_decode(file.read())

        if 'light_pwd' in cfg:
            manager.light_pwd = cfg['light_pwd']
            del cfg['light_pwd']
        if 'config_pwd' in cfg:
            configinterface.password = cfg['config_pwd']
            del cfg['config_pwd']

        manager.config.update(cfg)
    except FileNotFoundError:
        print("Config file '%s' not found" % config_file)

    try:
        manager.client = manager.connect_lampserver()

        status = manager.check_client_status()
        print("Connection status: %s" % manager.client_status)
        if status:
            manager.fetch_grid_size()
            print("Grid: %dx%d" % (manager.grid['height'], manager.grid['width']))
        else:
            print("Error: Couldn't connect to lampserver")
    except:
        traceback.print_exc()
        print("Error: Couldn't connect to lampserver")

    try:
        manager.load_game()
    except:
        traceback.print_exc()
        print("Error: Failed to load game")


def init_http():
    game_app = tornado.web.Application([
        (r"/",                 MainHandler),
        (r"/websocket",        CommunicationHandler)
    ], template_path='templates',
       static_path='static',
       debug=True)

    config_app = tornado.web.Application([
        (r"/config/?",         configinterface.ConfigHandler),
        (r"/config/login/?",   configinterface.ConfigLoginHandler),
        (r"/config/setup/?",   configinterface.SetupConfigHandler),
        (r"/config/game/?",    configinterface.GameConfigHandler),
        (r"/config/bridges/?", configinterface.BridgeConfigHandler),
        (r"/config/grid/?",    configinterface.GridConfigHandler)
    ], template_path='templates',
       static_path='static',
       cookie_secret=str(uuid.uuid4()),
       login_url="login",
       debug=True)

    if manager.config['serverport'] == manager.config['configport']:
        print('Warning: Game server port and config server port are the same')
        print('Warning: Game server not started')
    else:
        print("Starting game web server (port %d)" % manager.config['serverport'])
        game_app.listen(manager.config['serverport'])

    print("Starting config web server (port %d)" % manager.config['configport'])
    if manager.config.get('config_ssl', None):
        print("Using SSL")
        config_server = tornado.httpserver.HTTPServer(config_app, ssl_options={
            "certfile": manager.config['config_certfile'],
            "keyfile": manager.config['config_keyfile']
        })
    else:
        config_server = tornado.httpserver.HTTPServer(config_app)
    config_server.listen(manager.config['configport'])


if __name__ == "__main__":
    initialize()

    init_http()

    tornado.ioloop.IOLoop.instance().start()


