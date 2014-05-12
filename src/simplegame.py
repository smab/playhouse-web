import datetime

import tornado.ioloop  

import lightgames 


# A SimpleGame is a turnbased board game between two players who each may have 
# a color, score, and a timelimit. 
# Examples include Tic-tac-toe, Connect4, and Othello. 
class SimpleGame(lightgames.Game): 
    config_file = "simplegameconfig.html" 

    def __init__(self, client): 
        lightgames.Game.__init__(self, client) 

        # Default board, colors, and timelimits 
        self.template_vars['grid_x'] = 3 
        self.template_vars['grid_y'] = 3 
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']
        self.template_vars['color_1'] = '#FF0000' 
        self.template_vars['color_2'] = '#0000FF'
        self.template_vars['timelimit'] = 20 
        self.template_vars['timeleft'] = self.template_vars['timelimit']
        self.template_vars['score_1'] = None 
        self.template_vars['score_2'] = None 

        # A handler for the timer and a handler that keeps track of the 
        # timelimit counter server side. 
        self.timer_counter = tornado.ioloop.PeriodicCallback(self.timelimit_counter, 1000)


    def reset(self): 
        """
        Sets up everything with timelimits, turn indications, etc. 

        If you override this, you likely want to invoke this method manually!
        """
        # Sets up the board and tries to fetch two new players. 
        self.timer_counter.stop() 
        self.player = 0 
        self.players = [None, None]  
        self.player_passes = [0, 0] # refering to how many timelimit's they've triggered (in a row) 
        self.width = self.template_vars['grid_x'] 
        self.height = self.template_vars['grid_y'] 
        self.board   = [[2 for x in range(self.width)] for y in range(self.height)]

        self.template_vars['timeleft'] = self.template_vars['timelimit']

        lg, vars = lightgames, self.template_vars
        self.colors = [ lg.rgb_to_hsl(*lg.parse_color(vars['color_1'])),
                        lg.rgb_to_hsl(*lg.parse_color(vars['color_2'])),
                        lg.rgb_to_hsl(*lg.parse_color(vars['color_empty'])) ]

        for h in self.connections:
            lightgames.send_msg(h, {'gamestate': 'reset'})

        self.try_get_new_players(2)

        self.sync_all()
        self.reset_lamp_all()

    def sync_turn(self, handler): 
        """
        Syncs turn-data (timelimit, score, current turn) 

        If you override this, you likely want to invoke this method manually!
        """
        msg = { 
            'turn': self.player, 
            'score_1': self.template_vars['score_1'], 
            'score_2': self.template_vars['score_2']
        }
        if None not in self.players: 
            msg['timeleft'] = self.template_vars['timeleft'] 
        lightgames.send_msg(handler, msg) 
        

    def sync(self, handler):  
        # TODO Should be implemented here in some kind of standard format to 
        # decrease code repetition between games 
        # Edit: Perhaps the light syncing should be implemented in lighgames.Game even, 
        # while the timelimit/score sync is here, and other game specific 
        # syncing is in that game's class. 
        self.set_description(handler)

        self.sync_turn(handler) 
        super().sync(handler) 

    def add_player(self, handler): 
        # A player has been added. If this is the second player, 
        # we start the timer. 
        super().add_player(handler) 
        if handler in self.players and None not in self.players: 
            self.turnover(self.player) 

    def on_close(self, handler):
        self.connections -= {handler} 
        if handler in self.players: 
            i = self.players.index(handler) 
            lightgames.send_msg(self.players[1-i], { "message": "You are a spectator!", 
                                                     "error": "Your opponent left", 
                                                     "state": "gameover", 
            })
            self.reset() 

    # Returns True if it is this player's turn 
    def correct_player(self, handler): 
        """
        Checks if this handler corresponds with the current player. Returns 
        true if that is the case, or sends an error to the client otherwise. 
        """
        if self.player == None:
            return False 
        elif handler != self.players[self.player]: 
            lightgames.reply_wrong_player(self, handler)
            return False 
        return True 

    def turnover(self, to_player=None): 
        """
        Changes the turn to to_player and starts the timelimit if specified. 
        If the timelimit was paused, this function will start it again. 
        """
        self.timer_counter.stop() 
        if self.template_vars['timeleft'] > 0: 
            # The turnover was not because of exceeded timelimit; reset the 
            # number of passes that player has done 
            self.player_passes[self.player] = 0 
            
        self.template_vars['timeleft'] = self.template_vars['timelimit'] 

        if to_player == None:  
            self.player = 1 - self.player 
        else: 
            self.player = to_player 

        lightgames.send_msg(self.players[self.player],   {'message':'Your turn!'}) 
        lightgames.send_msg(self.players[1-self.player], {'message':'Waiting on other player...'})

        self.timer_counter = tornado.ioloop.PeriodicCallback(self.timelimit_counter, 1000)
        self.sync_all() 
        if None not in self.players: 
            self.timer_counter.start() 

    def pause_turn(self): 
        """
        Tells the client to pause the timelimit counter. This should be used 
        when doing animations. 
        """ 
        self.timer_counter.stop() 
        lightgames.send_msgs(self.connections, {'pause': True}) 

    def unpause_turn(self): 
        """
        Tells the client to start the timelimit counter again. 
        """ 
        lightgames.send_msgs(self.connections, {'timeleft': self.template_vars['timeleft']})
        self.timer_counter.start() 

    def timelimit_counter(self): 
        """ 
        A serverside counter of how many seconds left. Is sent to the clients 
        when they connect. Should not be overriden.
        """
        self.template_vars['timeleft'] -= 1
        if self.template_vars['timeleft'] < 0: 
            self.timer_counter.stop() 
            self.timelimit_exceeded() 

    def timelimit_exceeded(self): 
        """
        The timelimit given to the player has exceeded. This function 
        counts the number of timelimit exceeded by each player, and 
        resets the game when one have exceeded three times in a row. 
        """ 
        self.player_passes[self.player] += 1 
        if self.player_passes[self.player] >= 3: 
            lightgames.send_msgs(self.players, { "message": "You are a spectator!", 
                                                 "error": "Kicked due to inactivity", 
                                                 "state": "gameover", 
            })
            self.reset()
        else: 
            self.turnover() 

    def set_options(self, config):  
        vars = self.template_vars 
        vars['color_1']     = config['color_1']
        vars['color_2']     = config['color_2']
        vars['timelimit']   = max(0, int(config['timelimit']))  
        super().set_options(config) 


