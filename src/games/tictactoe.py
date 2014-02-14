import tornado.escape

import lightgames


def create(client):
    print("Creating tic-tac-toe game")
    return TicTacToe(client)


def send_msg(handler, msg):
    if handler != None:
        handler.write_message(
            tornado.escape.json_encode(msg)
        )


class TicTacToe(lightgames.Game):
    template_file = "tictactoe.html"
    template_vars = {
        'module_name': 'Tic-Tac-Toe',
        'grid_x': 3,
        'grid_y': 3
    }

    colors = [0, 45000, 65000]
    button_colors = ["red", "blue", ""]

    connections = []
    players = [None, None]
    player = 0
    board = None

    def reset(self):
        print("New game!")

        buffer = []
        for y in range(3):
            for x in range(3):
                buffer += [{'x':x, 'y':y, 'change':{'sat':0, 'hue':0, 'bri':0}}]
        self.client.request("POST", "/lights", tornado.escape.json_encode(buffer))
        print(self.client.getresponse().read().decode())

        self.player = 0
        self.players = [None, None]

        self.board = [[2, 2, 2],
                      [2, 2, 2],
                      [2, 2, 2]]

        #for handler in self.connections:
        #    self.sync(handler)

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(3):
            for x in range(3):
                button_color = self.button_colors[self.board[y][x]]
                handler.write_message(
                    tornado.escape.json_encode(
                        {'x':x, 'y':y, 'color':button_color}
                    )
                )

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
        playerH = self.players[self.player]
        opponentH = self.players[1-self.player]

        if opponentH == handler:
            print("Wrong player")
            send_msg(handler, {'error':'Not your turn!'})
        elif playerH != handler:
            print("Spectator")
            send_msg(handler, {'error':'You are not a player!'})
        else: # playerH == handler
            coords = tornado.escape.json_decode(message)
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
                for configuration in [[(y, 0), (y, 1), (y, 2)],
                                      [(0, x), (1, x), (2, x)],
                                      [(0, 0), (1, 1), (2, 2)],
                                      [(0, 2), (1, 1), (2, 0)]]:
                    if all(self.board[i][j] == self.player for i, j in configuration):
                        winner_lamps.update(configuration)
                
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

        if self.players[0] == handler:
            self.players[0] = None
        elif self.players[1] == handler:
            self.players[1] = None
