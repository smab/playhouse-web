import simplegame 
import lightgames


def create(client):
    print("Creating m,n,k-game")
    return MnkGame(client)


class MnkGame(simplegame.SimpleGame):
    config_file = "mnkconfig.html"
    template_file = "mnkgame.html"

    winning_req   = 3
    colors        = [         0,      45000, 65000]
    button_colors = ["player_1", "player_2",    ""]
    
    def __init__(self, client): 
        super().__init__(client) 
        self.template_vars['module_name'] = 'm,n,k-game' 
        self.template_vars['title'] = 'Tic-tac-toe'
        self.template_vars['grid_x'] = 3 
        self.template_vars['grid_y'] = 3 
        self.template_vars['winner_req'] = self.winning_req 
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y'] 

    def sync(self, handler):
        super().sync(handler) 
        print("Syncing %s" % handler)
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

        # Check it's the correct player 
        if not self.correct_player(handler):
            return 
        
        playerH   = self.players[self.player]
        opponentH = self.players[1 - self.player]
        
        x, y = coords['x'], coords['y']
        button_color = self.button_colors[self.player]

        if self.board[y][x] != 2:
            # Tile already occupied
            lightgames.send_msg(playerH, {'error':'Invalid move!'})

        else:
            # Tile unoccupied; perform the move
            self.board[y][x] = self.player
            lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'color':button_color})

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
            self.turnover() 

    def set_options(self, config):
        vars = self.template_vars
        vars['winner_req']  = max(2, int(config['winner_req']))

        self.winning_req = vars['winner_req']

        # Update title
        is_tic_tac_toe = (vars['grid_x'] == 3 and vars['grid_y'] == 3 
                                              and self.winning_req == 3)
        vars['title'] = 'Tic-tac-toe' if is_tic_tac_toe \
                                      else '%d-in-a-row' % self.winning_req

        super().set_options(config) 


    def set_description(self, handler):
        rules = '<p><b>Name: '+self.template_vars['title']+'</b></p><p><b>Players:</b> 2</p><p><b>Description:</b> The goal of this game is to, on a ' + str(self.template_vars['grid_x'])+ ' by ' + str(self.template_vars['grid_y']) + ' grid, connect ' + str(self.template_vars['winner_req']) + ' dots. Each player takes turn to place a dot anywhere on the grid where there is not already another dot and the first player to get '+ str(self.template_vars['winner_req']) +' dots in a row horizontally, vertically or diagonally wins the game. </p>'
        lightgames.send_msg(handler, {'rulemessage': (rules)})


