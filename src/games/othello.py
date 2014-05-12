import simplegame 
import lightgames


def create(client):
    print("Creating Othello game")
    return Othello(client)

class Othello(simplegame.SimpleGame):
    template_file = "mnkgame.html"

    colors        = [         0,      45000, 65000]
    button_colors = ["player_1", "player_2",    ""]

    def __init__(self, client): 
        super().__init__(client) 

        self.template_vars['module_name'] = 'Othello' 
        self.template_vars['title'] = 'Othello' 
        self.template_vars['grid_x'] = 8
        self.template_vars['grid_y'] = 8 
        self.template_vars['score_1'] = 2
        self.template_vars['score_2'] = 2 
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']

    def reset(self):
        super().reset() 

        # Set the start pattern 
        mx = (self.width  // 2) - 1
        my = (self.height // 2) - 1
        self.board[my][mx+1] = self.board[my+1][mx  ] = 0
        self.board[my][mx  ] = self.board[my+1][mx+1] = 1
        self.template_vars['score_1'] = 2
        self.template_vars['score_2'] = 2 
        self.sync_all() 

    def sync(self, handler):
        super().sync(handler) 
        self.set_description(handler)
        print("Syncing %s" % handler)
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                button_color = self.button_colors[self.board[y][x]]
                lightgames.send_msg(handler, {'x':x, 'y':y, 'color':button_color})

    def count_score(self): 
        scores = [0, 0, 0] # P1, P2, empty
        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                player = self.board[y][x]
                scores[player] += 1
        return [scores[0], scores[1]] 

    def game_over(self):
        # The game is over, see who won (or if the game is a tie) and notify
        # everyone of the result.
        scores = self.count_score() 
        if   scores[0] > scores[1]: winner = self.players[0]
        elif scores[0] < scores[1]: winner = self.players[1]
        else: winner = None 

        lightgames.game_over(self, winner)

    def on_message(self, handler, coords):
        def search(x, y, dx, dy, pred):
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
        
        # Check that it is the correct player 
        if not self.correct_player(handler): 
            return 

        opponent  = 1 - self.player
        playerH   = self.players[self.player]
        opponentH = self.players[opponent]

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
            
            # Update current score 
            self.template_vars['score_1'], self.template_vars['score_2'] = self.count_score() 

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
                self.turnover() 
                return

            # Opponent has to force-pass.
            # TODO: this should be indicated in the frontend somehow
            if has_any_legal_moves(self.player):
                self.turnover(self.player) 
                lightgames.send_msg(playerH,   {'message':'Opponent has to pass; your turn again!'})
                lightgames.send_msg(opponentH, {'message':'Out of valid moves! You have to pass.'})
                return

            # Neither player has any legal move; game over
            self.game_over()


    def set_description(self, handler):
        message = '<p><p><b>Name:</b> Othello</p><p><b>Players:</b> 2</p><p><b>Rules & Goals:</b> Each player takes turns placing their disks. Disks may only be placed so that at least one of the opposing players disks is between the placed disk and another of the placers disks. If a player manages to place their disk so that there is a straigh line (it may run diagonally) between the placed disk and another of the players disks, all the disks belonging to the other player that is inbetween them gets turned into the placers colour. In the end, when the board has been filled, the player with the most disks win.</p></p>'
        lightgames.send_msg(handler,   {'rulemessage': (message)})


