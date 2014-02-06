import tornado.escape

import random


class Game:
    def __init__(self, client):
        self.client = client
        self.init()

    def init(self):
        pass

    def on_connect(self, handler):
        pass

    def on_message(self, handler, message):
        pass

    def on_close(self, handler):
        pass

    def validate(self, msg): 
        pass 


class Paint(Game):
    playerColors = {}

    board = [[-1, -1, -1],
             [-1, -1, -1],
             [-1, -1, -1]]

    def init(self):
        buffer = []
        for y in range(3):
            for x in range(3):
                buffer += [{'x':x, 'y':y, 'change':{'sat':0, 'hue':0, 'bri':0}}]
        self.client.request("POST", "/lights", tornado.escape.json_encode(buffer))
        print(self.client.getresponse().read().decode())
    
    def on_connect(self, handler):
        self.playerColors[handler] = (
            random.randint(0,255), 
            random.randint(0,255), 
            random.randint(0,255)
        )
        print("Player %s, color %s" % (handler, self.playerColors[handler]))

        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                if self.board[y][x] != -1:
                    handler.write_message(
                        tornado.escape.json_encode(
                            {'x':x, 'y':y, 'color':self.board[y][x]}
                        )
                    )

    def on_message(self, handler, message):
        if self.validate(message): 
            coords, _ = message.split(" ") 
            x, y = coords.split("-") 
            x = int(x)
            y = int(y)
            color = self.playerColors[handler]
            
            self.board[y][x] = color
            for handler in self.playerColors:
                handler.write_message(
                    tornado.escape.json_encode(
                        {'x':x, 'y':y, 'color':color}
                    )
                )

            json = {'x': x, 'y': y, 'change': {'rgb': color}}        
            json = tornado.escape.json_encode([json]) 
            print("json:", json)
            
            headers = {'Content-Type': 'application/json'}
            self.client.request("POST", "/lights", json, headers) 

            # Print response 
            print(self.client.getresponse().read().decode())

    def on_close(self, handler):
        if handler in self.playerColors:
            del self.playerColors[handler]

    def validate(self, msg): 
        return True 





