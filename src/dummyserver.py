import tornado.ioloop
import tornado.web
import tornado.websocket


response = {
    "state": "success", 
    "bridges": {
        "001788182e78": {
            "ip": "130.237.228.58:80", 
            "username": "a0e48e11876b8971eb694151aba16ab", 
            "valid_username": True, 
            "lights": 3
        }, 
        "001788182c73": {
            "ip": "130.237.228.213:80", 
            "username": "1c9cdb15142f458731745fe11189ab3", 
            "valid_username": True, 
            "lights": 3
        }, 
        "00178811f9c2": {
            "ip": "130.237.228.161:80", 
            "username": "24f99ac4b92c8af22ea52ec3d6c3e37", 
            "valid_username": True, 
            "lights": 'aoeu'
        }
    }
}


class MainHandler(tornado.web.RequestHandler): 
    def get(self): 
        print("GET:", self.request.body) 
        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode(response)) 
    def post(self):
        # For easy debugging, here you can respond like a lampserver 
        print("POST:", self.request.body) 
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


