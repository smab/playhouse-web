import tornado.escape

import lightgames


def create(client):
    print("Creating m,n,k-game")
    return MnkGame(client)


def send_msg(handler, msg):
    if handler != None:
        handler.write_message(msg)


class MnkGame(lightgames.Game):
    template_file = "mnkgame.html"
    template_vars = {
        'module_name': 'm,n,k-game',
        'grid_x': 3,
        'grid_y': 3
    }
    # note: concept/idea
    options = {
        'winner_req':('integer', 'Stones in a row required to win'),
        'size':('(integer, integer)', 'Grid size')
    }

    winning_req = 3
    colors = [0, 45000, 65000]
    button_colors = ["red", "blue", ""]

    connections = []        # connections to sync the board with
    players = [None, None]  # current players
    player = 0
    board = None

    def reset(self):
        print("New game!")

        if self.template_vars['grid_x'] == 3 and \
           self.template_vars['grid_y'] == 3 and self.winning_req == 3:
            self.template_vars['title'] = 'Tic-tac-toe'
        else:
            self.template_vars['title'] = '%d-in-a-row' % self.winning_req

        buffer = []
        for y in range(3):
            for x in range(3):
                buffer += [{'x':x, 'y':y, 'change':{'sat':0, 'hue':0, 'bri':0}}]
        self.client.request("POST", "/lights", tornado.escape.json_encode(buffer))
        print(self.client.getresponse().read().decode())

        # stop syncing previous players
        for h in self.players:
            if h != None:
                self.connections.remove(h)

        self.player = 0
        self.players = [None, None]
        self.board = [[2 for _ in range(self.template_vars['grid_x'])]
            for _ in range(self.template_vars['grid_y'])]

        # try to get two new players from queue
        self.add_player(self.queue.get_first())
        self.add_player(self.queue.get_first())

        for handler in self.connections:
            self.sync(handler)

    def add_player(self, handler):
        print("Add player: %s" % handler)

        player = -1
        if handler != None:
            if handler not in self.connections:
                self.connections += [handler]

            if None in self.players:
                player = self.players.index(None)
                self.players[player] = handler

            assert player != -1

            print("Connection %s as player %d" % (handler, player))
            send_msg(handler, {'message':'You are player %d' % (player+1)})

        return player

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                button_color = self.button_colors[self.board[y][x]]
                handler.write_message(
                    {'x':x, 'y':y, 'color':button_color}
                )

    def init(self):
        self.reset()

    def destroy(self):
        for h in self.connections:
            send_msg(h, {'message':"The game got destroyed!"})

        self.players = [None, None]
        self.connections = []

    def on_connect(self, handler):
        if handler not in self.connections:
            self.connections += [handler]

        spectator = True
        if None in self.players:
            top = self.queue.get_first()
            self.add_player(top)
            spectator = top != handler

        if spectator:
            send_msg(handler, {'message':'You are a spectator!'})

        # Sync board
        self.sync(handler)

    def on_message(self, handler, message):
        playerH = self.players[self.player]
        opponentH = self.players[1-self.player]

        coords = tornado.escape.json_decode(message)
        if 'action' not in coords or coords['action'] != 'gameaction':
            # assume queueaction
            if handler not in self.players:
                self.on_connect(handler)
            return

        if playerH != handler:
            if opponentH == handler:
                print("Wrong player")
                send_msg(handler, {'error':'Not your turn!'})
            else:
                print("Spectator")
                send_msg(handler, {'error':'You are not a player!'})
        else: # playerH == handler
            x = coords['x']
            y = coords['y']
            button_color = self.button_colors[self.player]

            if self.board[y][x] == 2:
                self.board[y][x] = self.player
                for h in self.connections:
                    send_msg(h, {'x':x, 'y':y, 'color':button_color})

                send_msg(playerH, {'message':'Waiting on other player...'})
                send_msg(opponentH, {'message':'Your turn!'})

                color = self.colors[self.player]
                json = {'x': x, 'y': y, 'change': {'sat':255, 'hue': color}}
                json = tornado.escape.json_encode([json])
                #print("json:", json)

                headers = {'Content-Type': 'application/json'}
                self.client.request("POST", "/lights", json, headers)

                # Print response
                print(self.client.getresponse().read().decode())

                winner_lamps = set()

                directions = [(0,1), (1,0), (1,1), (1,-1)]
                for direction in directions:
                    def search(cx, cy, direction):
                        lamps = []
                        for i in range(self.winning_req-1):
                            cx += direction[0]
                            cy += direction[1]
                            if cx >= 0 and cy >= 0 and \
                                cy < len(self.board) and cx < len(self.board[cy]) and \
                                self.board[cy][cx] == self.player:
                                lamps += [(cx, cy)]
                            else:
                                break
                        return lamps

                    lamps = [(x,y)] + search(x, y, direction) + \
                            search(x, y, (-direction[0], -direction[1]))
                    if len(lamps) >= self.winning_req:
                        winner_lamps.update(lamps)

                if len(winner_lamps) > 0:
                    send_msg(playerH, {'message':'You won!'})
                    send_msg(opponentH, {'message':'You lost!'})
                    for h in self.connections:
                        if h != playerH and h != opponentH:
                            send_msg(h, {'message':"Player %d won" % (self.player+1)})
                    print("Player %d wins!" % self.player)
                    self.reset()
                    return
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

        if handler in self.players:
            player = self.players.index(handler)
            self.players[player] = None

            # try to replace the player with one from the queue
            self.add_player(self.queue.get_first())


    def set_options(self, config):
        self.winning_req = config['winner_req']
        self.template_vars['grid_y'] = config['size'][0]
        self.template_vars['grid_x'] = config['size'][1]

        self.reset()
