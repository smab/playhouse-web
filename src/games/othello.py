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

    def game_over(self):
        # The game is over, see who won (or if the game is a tie) and notify
        # everyone of the result.
        scores = [0, 0, 0] # P1, P2, empty
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                player = self.board[y][x]
                scores[player] += 1

        winner = None
        if   scores[0] > scores[1]: winner = self.players[0]
        elif scores[0] < scores[1]: winner = self.players[1]

        lightgames.game_over(self, winner)

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

        def get_surrounding_beams(x,y, beam_val, terminal_val):
            beams = []
            for (dx,dy) in [(-1,-1), ( 0,-1), (+1,-1),
                            (-1, 0),          (+1, 0),
                            (-1,+1), ( 0,+1), (+1,+1)]:
                beam = search(x,y, dx,dy, lambda t: t == beam_val)
                if len(beam) > 0:
                    (lx,ly) = beam[-1]
                    lx += dx
                    ly += dy
                    if 0 <= ly < len(self.board)     and \
                       0 <= lx < len(self.board[ly]) and \
                       self.board[ly][lx] == terminal_val:
                        beams += [ beam ]
            return beams

        opponent  = 1 - self.player

        playerH   = self.players[self.player]
        opponentH = self.players[opponent]

        if playerH != handler:
            lightgames.reply_wrong_player(self, handler)
            return

        # playerH == handler
        x, y = coords['x'], coords['y']
        button_color = self.button_colors[self.player]

        beams = get_surrounding_beams(x,y, opponent, self.player)

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

            # Check if the board is full
            if all(all(i != 2 for i in j) for j in self.board):
                self.game_over()
                return

            # Check for if either player is out of legal moves
            def has_any_legal_moves(player):
                def has_legal_move_at(x,y, player):
                    if self.board[y][x] == 2 and \
                       len(get_surrounding_beams(x,y, 1 - player, player)) > 0:
                        print("%d has move at (%s,%s)" % (player, x, y))

                    return self.board[y][x] == 2 and \
                           len(get_surrounding_beams(x,y, 1 - player, player)) > 0

                return any(has_legal_move_at(vx,vy, player) \
                             for vx in range(len(self.board[0])) \
                             for vy in range(len(self.board)))

            if has_any_legal_moves(opponent):
                # Opponent has a play; switch player have the opponent play
                self.player = opponent
                lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
                lightgames.send_msg(opponentH, {'message':'Your turn!'})
                return

            # Opponent has to force-pass.
            # TODO: this should be indicated in the frontend somehow
            if has_any_legal_moves(self.player):
                lightgames.send_msg(playerH,   {'message':'Opponent has to pass; your turn again!'})
                lightgames.send_msg(opponentH, {'message':'Out of valid moves! You have to pass.'})
                return

            # Neither player has any legal move; game over
            self.game_over()
