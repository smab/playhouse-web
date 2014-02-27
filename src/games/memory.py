import tornado.escape
import random
import itertools

import lightgames


def create(client):
    print("Creating memory game")
    return Memory(client)


def send_msg(handler, msg):
    if handler != None:
        handler.write_message(tornado.escape.json_encode(msg))


class Memory(lightgames.Game):
    template_file = "memory.html"
    template_vars = {
        'module_name': 'Memory',
        'title':       'Memory',
        'grid_x':      6,
        'grid_y':      4,
        'cell_w':      74,
        'cell_h':      74,
    }

    width, height = template_vars['grid_x'], template_vars['grid_y']

    hues = itertools.cycle([5000, 15000, 25000, 35000, 45000, 55000, 65000])

    connections = []
    players = [None, None]
    scores  = [0, 0]
    player = 0
    active_tiles = []

    board = None


    def reset(self):
        print("New game!")
        self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0 })

        # Reset game state
        self.player = 0
        self.players = [None, None]
        self.scores  = [0, 0]

        coords = [(x,y) for x in range(self.width) for y in range(self.height)]
        random.shuffle(coords)

        # Sign determines whether tile is visible (negative = not visible),
        # magnitude determines hue.
        self.board = [[0 for x in range(self.width)] for y in range(self.height)]
        while len(coords) > 0:
            hue = next(self.hues)
            (x1,y1) = coords.pop()
            (x2,y2) = coords.pop()
            self.board[y1][x1] = -hue
            self.board[y2][x2] = -hue

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(self.height):
            for x in range(self.width):
                powered = self.board[y][x] >= 0
                hue     = self.board[y][x] if powered else 0
                send_msg(handler, {'x':x, 'y':y, 'hue':hue, 'power':powered})

    def sync_delta(self):
        print("Syncing delta...")

    def init(self):
        self.reset()

    def destroy(self):
        for h in self.connections:
            send_msg(h, {'message':"The game got destroyed!"})

        self.players = [None, None]
        self.connections = []

    def on_connect(self, handler):
        self.connections += [handler]

        player = -1
        if self.players[0] == None:
            self.players[0] = handler
            player = 0
        elif self.players[1] == None:
            self.players[1] = handler
            player = 1

        print("Connection %s as player %d" % (handler, player))
        if player == -1:
            send_msg(handler, {'message':'You are a spectator!'})
        else:
            send_msg(handler, {'message':'You are player %d' % (player+1)})

        # Sync board
        self.sync(handler)

    def on_message(self, handler, message):
        playerH   = self.players[self.player]
        opponentH = self.players[1 - self.player]

        message = tornado.escape.json_decode(message)

        if 'x' in message:
            if opponentH == handler:
                print("Wrong player")
                send_msg(handler, {'error':'Not your turn!'})

            elif playerH != handler:
                print("Spectator")
                send_msg(handler, {'error':'You are not a player!'})

            else: # playerH == handler
                x, y   = message['x'], message['y']

                if self.board[y][x] < 0:
                    self.board[y][x] *= -1
                    self.active_tiles.append((x,y))

                    self.send_lamp(x, y, {'sat': 255, 'hue': self.board[y][x]})
                    for h in self.connections:
                        send_msg(h, {'x':x, 'y':y, 'hue':self.board[y][x], 'power':True})

                    # Each player toggles two tiles per turn
                    if len(self.active_tiles) == 2:
                        (x1,y1) = self.active_tiles[0]
                        (x2,y2) = self.active_tiles[1]
                        color1  = self.board[y1][x1]
                        color2  = self.board[y2][x2]

                        if color1 == color2:
                            self.scores[self.player] += 1
                            # Guessed correctly; player gets to keep going

                        else:
                            self.board[y1][x1] *= -1
                            self.board[y2][x2] *= -1

                            for h in self.connections:
                                send_msg(h, {'x':x1, 'y':y1, 'hue':0, 'power':False, 'delay':2000})
                                send_msg(h, {'x':x2, 'y':y2, 'hue':0, 'power':False, 'delay':2000})

                            self.send_lamp(x1, y1, {'sat': 0, 'hue': 0})
                            self.send_lamp(x2, y2, {'sat': 0, 'hue': 0})

                            # Switch over to opponent
                            send_msg(playerH, {'message':'Waiting on other player...'})
                            send_msg(opponentH, {'message':'Your turn!'})
                            self.player = 1 - self.player

                        self.active_tiles = []

                    if all(all(hue >= 0 for hue in row) for row in self.board):
                        winner = -1
                        if self.scores[0] > self.scores[1]:
                            winner = 0
                        elif self.scores[0] < self.scores[1]:
                            winner = 1

                        print("Game over; winner: %d" % winner)
                        if winner == -1:
                            for h in self.connections:
                                send_msg(h, {'message':"The game tied"})
                        else:
                            for h in self.connections:
                                send_msg(h, {'message':"Player %d won!" % (winner + 1)})

                        self.reset()
                        return

                else:
                    send_msg(playerH, {'error':'Invalid move!'})


    def on_close(self, handler):
        if handler in self.connections:
            self.connections.remove(handler)

        if self.players[0] == handler:
            self.players[0] = None
        elif self.players[1] == handler:
            self.players[1] = None

# vim: set sw=4:
