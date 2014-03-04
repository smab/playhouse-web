import lightgames


def create(client):
    print("Creating Othello game")
    return Othello(client)


class Othello(lightgames.Game):
    template_file = "mnkgame.html"
    template_vars = {
        'module_name': 'othello',
        'title':       'Othello',
        'grid_x':      8,
        'grid_y':      8,
        'color_1':    '#33F',
        'color_2':    '#F33',
    }

    colors        = [         0,      45000, 65000]
    button_colors = ["player_1", "player_2",    ""]

    def reset(self):
        print("New game!")

        self.player  = 0
        self.players = [None, None]
        self.board   = [[2 for _ in range(self.template_vars['grid_x'])]
                           for _ in range(self.template_vars['grid_y'])]

        self.board[3][4] = self.board[4][3] = 0
        self.board[3][3] = self.board[4][4] = 1

        self.try_get_new_players(2)
        self.sync_all()
        self.reset_lamp_all()

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                button_color = self.button_colors[self.board[y][x]]
                lightgames.send_msg(handler, {'x':x, 'y':y, 'color':button_color})

    def on_message(self, handler, coords):
        def search(x, y, dx, dy, pred):
            val = self.board[y][x]
            lamps = []
            x += dx
            y += dy
            while 0 <= y < len(self.board) and \
                  0 <= x < len(self.board[y]):
                if pred(self.board[y][x]):
                    lamps += [(x,y)]
                else:
                    break
                x += dx
                y += dy
            return lamps

        playerH   = self.players[self.player]
        opponentH = self.players[1 - self.player]

        opponent = 1 - self.player

        if playerH != handler:
            lightgames.reply_wrong_player(self, handler)
            return

        # playerH == handler
        x, y = coords['x'], coords['y']
        button_color = self.button_colors[self.player]

        beams = []
        for (dx,dy) in [(-1,-1), ( 0,-1), (+1,-1),
                        (-1, 0),          (+1, 0),
                        (-1,+1), ( 0,+1), (+1,+1)]:
            beam = search(x,y, dx,dy, lambda t: t == opponent)
            if len(beam) > 0:
                (lx,ly) = beam[-1]
                lx += dx
                ly += dy
                if 0 <= ly < len(self.board) and \
                   0 <= lx < len(self.board[ly]) and \
                   self.board[ly][lx] == self.player:
                    beams += [ beam ]

        if self.board[y][x] != 2 or len(beams) == 0:
            # Tile already occupied, or toggles no bricks
            lightgames.send_msg(playerH, {'error':'Invalid move!'})

        else:
            # Tile unoccupied; perform the move
            self.board[y][x] = self.player
            lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'color':button_color})
            self.send_lamp(x, y, {'sat':255, 'hue':self.colors[self.player]})

            for beam in beams:
                for (px,py) in beam:
                    self.board[py][px] = self.player
                    lightgames.send_msgs(self.connections, {'x':px, 'y':py, 'color':button_color})
                    self.send_lamp(px, py, {'sat':255, 'hue':self.colors[self.player]})

            lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
            lightgames.send_msg(opponentH, {'message':'Your turn!'})

            # Check if the board is full
            if all(all(i != 2 for i in j) for j in self.board):
                scores = [0, 0]
                for y in range(len(self.board)):
                    for x in range(len(self.board[y])):
                        player = self.board[y][x]
                        scores[player] += 1

                winner = -1
                if   self.scores[0] > self.scores[1]: winner = 0
                elif self.scores[0] < self.scores[1]: winner = 1

                print("Game over; winner: %d" % winner)
                if winner == -1:
                    lightgames.send_msgs(self.connections, {'message':"The game tied"})
                else:
                    lightgames.send_msgs(self.connections, {'message':"Player %d won!" % (winner + 1)})

                self.reset()
                return

            # Switch player
            self.player = 1 - self.player
