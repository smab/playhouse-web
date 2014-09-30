
import tornado.ioloop
import tornado.web 
import tornado.websocket 

import signal 

import manager 

class SimpleHandler(tornado.web.RequestHandler): 
    def get(self): 
        template_vars = {
            'stream_embedcode': manager.config['stream_embedcode'], 
        }
        self.render('idle.html', **template_vars) 


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
    except ValueError as e:
        print("Error loading config: %s" % e.args[0])


initialize() 

handlers = [(r'/', SimpleHandler)]
settings = {'template_path': 'templates', 'static_path': 'static'} 

application = tornado.web.Application(handlers, **settings) 
application.listen(manager.config['serverport']) 

loop = tornado.ioloop.IOLoop.instance() 

def on_shutdown(): 
    loop.stop() 

signal.signal(signal.SIGINT, lambda sig, frame: loop.add_callback_from_signal(on_shutdown)) 
loop.start() 


