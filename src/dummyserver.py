import tornado.ioloop
import tornado.web
import tornado.websocket


class MainHandler(tornado.web.RequestHandler): 
    def post(self):
        # For easy debugging, here you can respond like a lampserver 
        print("POST: ", self.request.body) 
        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode({"state": "success"})) 


application = tornado.web.Application([
    (r".*", MainHandler) # For debugging
])

if __name__ == "__main__":
    with open('config.json', 'r') as file:
        config = tornado.escape.json_decode(file.read())

    print("Starting dummy lamp server (port %d)" % config['lampport'])
    application.listen(config['lampport'])
    tornado.ioloop.IOLoop.instance().start()


