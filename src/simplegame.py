import lightgames 


# A SimpleGame is a turnbased board game between two players who each may have 
# a color, score, and a timelimit. 
# Examples include Tic-tac-toe, Connect4, and Othello. 
class SimpleGame(lightgames.Game): 
    def __init__(self, client): 
        lightgames.Game.__init__(self, client) 

        # Default board, colors, and timelimits 
        self.template_vars['grid_x'] = 3 
        self.template_vars['grid_y'] = 3 
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']
        self.template_vars['color_1'] = '#FF0000' 
        self.template_vars['color_2'] = '#0000FF'
        self.template_vars['timelimit'] = 20 


    def reset(self): 
        # Sets up the board and tries to fetch two new players. 
        self.player = 0 
        self.players = [None, None]  
        self.board   = [[2 for x in range(self.width)] for y in range(self.height)]

        lg, vars = lightgames, self.template_vars
        self.colors = [ lg.rgb_to_hsl(*lg.parse_color(vars['color_1'])),
                        lg.rgb_to_hsl(*lg.parse_color(vars['color_2'])),
                        lg.rgb_to_hsl(*lg.parse_color(vars['color_empty'])) ]

        for h in self.connections:
            lightgames.send_msg(h, {'gamestate': 'reset'})

        self.try_get_new_players(2)
        self.sync_all()
        self.reset_lamp_all()

    def sync(self, handler):  
        # TODO Should be implemented here in some kind of standard format to 
        # decrease code repetition between games 
        pass 

    # Returns True if it is this player's turn 
    def correctPlayer(self, handler): 
        if self.player == None or handler != self.players[self.player]: 
            lightgames.reply_wrong_player(self, handler)
            return False 
        return True 
    
    # Changes the turn between players 
    def turnover(self): 
        self.player = 1 - self.player
        lightgames.send_msg(self.players[self.player],   {'message':'Your turn!'})
        lightgames.send_msg(self.players[1-self.player], {'message':'Waiting on other player...'})
            
    def set_options(self, config):  
        def clamp(low, x, high):
            return max(low, min(high, x))

        m = 50
        vars = self.template_vars
        vars['grid_x'] = clamp(2, int(config['grid_x']),   m)
        vars['grid_y'] = clamp(2, int(config['grid_y']),   m)
        vars['cell_w'] = clamp(2, int(config['cell_w']), 500)
        vars['cell_h'] = clamp(2, int(config['cell_h']), 500)

        vars['color_1']     = config['color_1']
        vars['color_2']     = config['color_2']
        vars['color_empty'] = config['color_empty']

        #vars['timelimit']   = clamp(0, int(config['timelimit'])) 

        self.reset() 

    def set_description(self, handler): 
        pass 

