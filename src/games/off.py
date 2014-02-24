import tornado.escape

import lightgames


def create(client):
    print("Turning off lamps")
    return Off(client)


class Off(lightgames.Game):
    """A 'game' used to easily turn off the lights when not needed"""
    def reset(self):
        buffer = []
        for y in range(3): # TODO Get these variables from the server 
            for x in range(3):
                buffer += [{'x':x, 'y':y, 'change':{ "on":False }}]
        self.client.request("POST", "/lights", tornado.escape.json_encode(buffer))
        print(self.client.getresponse().read().decode())

    def init(self):
        self.reset()



