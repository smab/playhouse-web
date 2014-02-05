import tornado.ioloop
import tornado.web
import tornado.websocket

import http.client

import games


lampdest, lampport = "smab.csc.kth.se", 4711
lampdest, lampport = "localhost", 8080 # For local testing 

client = http.client.HTTPConnection(lampdest, lampport)
headers = {
    'Content-Type': 'application/json', 
    'Accept': '*/*', 
}

# The port which this server listens on 
# Don't forget to change any websockets also (e.g in index.html)  
serverport = 8080 

game = games.Paint(client)


class MainHandler(tornado.web.RequestHandler): 
    def post(self):
        # For easy debugging, here you can respond like a lampserver 
        print("POST: ", self.request.body) 
        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode({"state": "success"})) 

    def get(self):
        self.render('../templates/index.html')     


class CommunicationHandler(tornado.websocket.WebSocketHandler): 
    def open(self): 
        print("Client connected") 
        game.on_connect(self)

    def on_message(self, message): 
        print("Recived message:", message)
        
        # The message needs validation so that no 
        # cheating or DOS can happen
        if validate(message):
            game.on_message(self, message)

    def on_close(self): 
        game.on_close(self)
        pass 

# Perhaps put this in a separate module 
# containing game-specific code? 
def validate(msg): 
    return True


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/websocket", CommunicationHandler), 
    (r"/lights", MainHandler), # For debugging 
])

if __name__ == "__main__":
    application.listen(serverport)
    tornado.ioloop.IOLoop.instance().start()



