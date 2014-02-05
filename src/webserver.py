import tornado.ioloop
import tornado.web
import tornado.websocket

import http.client 

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

# Blue and red 
playerColors = [46920, 0] 


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

    def on_message(self, message): 
        print("Recived message:", message)
        
        # The message needs validation so that no 
        # cheating or DOS can happen
        if validate(message):
            # On second thought, everything here should also be in 
            # the game-specific code since the message from the client 
            # is also game-specific 
            coords, player = message.split(" ") 
            x, y = coords.split("-") 
            
            json = {"x": int(x), "y": int(y)}

            change = {}
            change["on"] = True
            change["hue"] = playerColors[int(player)]

            json["change"] = change
            
            json = tornado.escape.json_encode([json]) 
            print("json:", json)
            
            client.request("POST", "/lights", json, headers) 
            #response = client.getresponse().read()  

            # Print response 
            #print(client.getresponse().read().decode())

    def on_close(self): 
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



