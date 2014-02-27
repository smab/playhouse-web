import tornado.escape

import lightgames


def create(client):
    print("Creating connect-4 game")
    return Connect4(client)


def send_msg(handler, msg):
    if handler != None:
        handler.write_message(tornado.escape.json_encode(msg))


class Connect4(lightgames.Game):
    template_file = "connect4.html"
    template_vars = {
        'module_name': 'Connect 4',
        'title':       'Connect 4',
        'grid_x':  7, 'grid_y':  6,
        'cell_w': 74, 'cell_h': 74,
    }

    width, height = template_vars['grid_x'], template_vars['grid_y']

    colors      = [0, 50000, 65000]

    connections = []
    players     = [None, None]
    player      = 0
    board       = None

    def reset(self):
        print("New game!")
        self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0 })

        self.player  = 0
        self.players = [None, None]
        self.board   = [[2 for x in range(self.width)] for y in range(self.height)]

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(self.height):
            for x in range(self.width):
                hue     = self.colors[self.board[y][x]]
                powered = self.board[y][x] != 2
                send_msg(handler, {'x':x, 'y':y, 'hue':hue, 'power':powered})

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
                x, y = message['x'], message['y']
                hue = self.colors[self.player]

                def grab_ray(pos, delta):
                    x, y   = pos
                    dx, dy = delta
                    res    = set()

                    def within_bounds(x,y):
                        return 0 <= x < self.width and 0 <= y < self.height

                    while within_bounds(x,y) and self.board[y][x] == self.player:
                        res.add((x,y))
                        x,y = x + dx, y + dy
                    return res

                if self.board[y][x] == 2 and (y == self.height - 1 or
                                              self.board[y + 1][x] != 2):
                    self.board[y][x] = self.player

                    self.send_lamp(x, y, {'sat': 255, 'hue': hue})
                    for h in self.connections:
                        send_msg(h, {'x':x, 'y':y, 'hue':hue, 'power':True})

                    send_msg(playerH, {'message':'Waiting on other player...'})
                    send_msg(opponentH, {'message':'Your turn!'})

                    # Check if this move caused a win
                    winner_lamps = set()
                    for (dx,dy) in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                        lefts  = grab_ray((x,y), ( dx, dy))
                        rights = grab_ray((x,y), (-dx,-dy))

                        if len(lefts) + len(rights) - 1 >= 4:
                            winner_lamps.update(lefts)
                            winner_lamps.update(rights)

                    if len(winner_lamps) > 0:
                        send_msg(playerH, {'message':'You won!'})
                        send_msg(opponentH, {'message':'You lost!'})
                        for h in self.connections:
                            if h != playerH and h != opponentH:
                                send_msg(h, {'message':"Player %d won" % (self.player+1)})
                        print("Player %d wins!" % self.player)
                        self.reset()
                        return

                    # Check for full board
                    if all(all(i != 2 for i in j) for j in self.board):
                        print("The game tied")
                        for h in self.connections:
                            send_msg(h, {'message':"The game tied"})
                        self.reset()
                        return

                    self.player = 1 - self.player

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
