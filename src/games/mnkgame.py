import lightgames


def create(client):
    print("Creating m,n,k-game")
    return MnkGame(client)


class MnkGame(lightgames.Game):
    config_file = "mnkconfig.html"
    template_file = "mnkgame.html"
    template_vars = {
        'module_name': 'm,n,k-game',
        'title':       'Tic-tac-toe',
        'grid_x':      3,
        'grid_y':      3,
        'winner_req':  3,
        'color_1':    '#FF3333',
        'color_2':    '#3333FF',
    }
    # note: concept/idea
    options = {
        'winner_req': ('integer',            'Stones in a row required to win'),
        'size':       ('(integer, integer)', 'Grid size')
    }

    winning_req   = 3
    colors        = [         0,      45000, 65000]
    button_colors = ["player_1", "player_2",    ""]

    def reset(self):        
        print("New game!")
        
        self.player  = 0
        self.players = [None, None]
        self.board   = [[2 for _ in range(self.template_vars['grid_x'])]
                           for _ in range(self.template_vars['grid_y'])]

        self.try_get_new_players(2)
        self.sync_all()
        self.reset_lamp_all()

    def sync(self, handler):
        print("Syncing %s" % handler)
        #Send the game description
        self.set_description(handler)
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                button_color = self.button_colors[self.board[y][x]]
                lightgames.send_msg(handler, {'x':x, 'y':y, 'color':button_color})

    def search_winner_lamps(self, x, y):
        def search(cx, cy, dx, dy):
            lamps = []
            for _ in range(self.winning_req-1):
                cx += dx
                cy += dy
                if cx >= 0 and cy >= 0 and \
                    cy < len(self.board) and cx < len(self.board[cy]) and \
                    self.board[cy][cx] == self.player:
                    lamps += [(cx, cy)]
                else:
                    break
            return lamps

        winner_lamps = set()

        directions = [(0,1), (1,0), (1,1), (1,-1)]
        for (dx,dy) in directions:
            lamps = [(x,y)] + search(x, y,  dx,  dy) \
                            + search(x, y, -dx, -dy)

            if len(lamps) >= self.winning_req:
                winner_lamps.update(lamps)

        return winner_lamps


    def on_message(self, handler, coords):
        playerH   = self.players[self.player]
        opponentH = self.players[1 - self.player]
        
        if playerH != handler:
            lightgames.reply_wrong_player(self, handler)
            return

        # playerH == handler
        x, y = coords['x'], coords['y']
        button_color = self.button_colors[self.player]

        if self.board[y][x] != 2:
            # Tile already occupied
            lightgames.send_msg(playerH, {'error':'Invalid move!'})

        else:
            # Tile unoccupied; perform the move
            self.board[y][x] = self.player
            lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'color':button_color})

            lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
            lightgames.send_msg(opponentH, {'message':'Your turn!'})

            self.send_lamp(x, y, {'sat':255, 'hue':self.colors[self.player]})

            # Check whether this was a winning move for the current player
            winner_lamps = self.search_winner_lamps(x, y)
            if len(winner_lamps) > 0:
                lightgames.game_over(self, playerH)
                return

            # Check if the board is full
            if all(all(i != 2 for i in j) for j in self.board):
                lightgames.game_over(self, None)
                return

            # Switch player
            self.player = 1 - self.player


    def set_options(self, config):
        def clamp(low, x, high):
            return max(low, min(high, x))

        m = 50
        vars = self.template_vars
        vars['grid_y']      = clamp(2, int(config['grid_y']),            m)
        vars['grid_x']      = clamp(2, int(config['grid_x']),            m)
        vars['cell_w']      = clamp(2, int(config['cell_w']),          500)
        vars['cell_h']      = clamp(2, int(config['cell_h']),          500)

        # Make sure that it's not possible to configure completely impossible
        # games.
        grid_max = max(vars['grid_x'], vars['grid_x'])
        vars['winner_req']  = clamp(2, int(config['winner_req']), grid_max)

        vars['color_1']     = config['color_1']
        vars['color_2']     = config['color_2']
        vars['color_empty'] = config['color_empty']

        self.winning_req = vars['winner_req']

        # Update title
        is_tic_tac_toe = (vars['grid_x'] == 3 and vars['grid_y'] == 3 
                                              and self.winning_req == 3)
        vars['title'] = 'Tic-tac-toe' if is_tic_tac_toe \
                                      else '%d-in-a-row' % self.winning_req

        self.reset()


    def set_description(self, handler):
        rules = '<p><b>Name: '+self.template_vars['title']+'/b></p><p><b>Players:</b> 2</p><p><b>Description:</b> The goal of this game is to, on a ' + str(self.template_vars['grid_x'])+ ' by ' + str(self.template_vars['grid_y']) + ' grid, connect ' + str(self.template_vars['winner_req']) + ' dots. Each player takes turn to place a dot anywhere on the grid where there is not already another dot and the first player to get '+ str(self.template_vars['winner_req']) +' dots in a row horizontally, vertically or diagonally wins the game </p>'

        lightgames.send_msg(handler, {'rulemessage': (rules)})
