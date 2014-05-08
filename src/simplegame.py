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

        self.timer_handler = None 
        self.timer_counter = tornado.ioloop.PeriodicCallback(self.timelimit_counter, 1000, io_loop = None)


    def reset(self): 
        # Sets up the board and tries to fetch two new players. 
        self.player = 0 
        self.players = [None, None]  
        self.width = self.template_vars['grid_x'] 
        self.height = self.template_vars['grid_y'] 
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
        # Edit: Perhaps the light syncing should be implemented in lighgames.Game even, 
        # while the timelimit/score sync is here, and other game specific 
        # syncing is in that game's class. 
        self.set_description(handler)

        # If timelimit != timeleft, then two players are already playing and 
        # we must start the local timecounter. (by sending turnover) 
        # If not we can send turn and not start the local timecounter. 
        msg = { 'timeleft': self.template_vars['timeleft']}
        if self.template_vars['timeleft'] != self.template_vars['timelimit']:
            msg['turnover'] = self.player+1 
        else: 
            msg['turn'] = self.player+1 

        lightgames.send_msg(handler, msg)
        super().sync(handler) 

    def add_player(self, handler): 
        # A player has been added. 
        # If this is the second player, 
        # we start the timer. 
        super().add_player(handler) 
        if not None in self.players: 
            self.player = 1 - self.player  
            self.turnover() 

    # Returns True if it is this player's turn 
    def correctPlayer(self, handler): 
        if self.player == None or handler != self.players[self.player]: 
            lightgames.reply_wrong_player(self, handler)
            return False 
        return True 
    
    # Changes the turn between players. If a turn was paused, this function starts 
    # it again. 
    def turnover(self): 
        self.player = 1 - self.player
        lightgames.send_msg(self.players[self.player],   {'message':'Your turn!'}) 
        lightgames.send_msg(self.players[1-self.player], {'message':'Waiting on other player...'})

        # Send turnover if there is an opponent, else send turn
        if self.players[1] == None: 
            lightgames.send_msgs(self.connections, {'turn': self.player+1})
        else: 
            lightgames.send_msgs(self.connections, {'turnover': self.player+1})
            if self.template_vars['timelimit'] > 0: 
                if self.timer_handler != None: 
                    lightgames.remove_timeout(self.timer_handler) 
                    self.timer_counter.stop() 
                    self.template_vars['timeleft'] = self.template_vars['timelimit']


                self.timer_handler = lightgames.set_timeout(
                    datetime.timedelta(seconds=self.template_vars['timelimit']), 
                    self.timelimit_exceeded
                )
                self.timer_counter.start() 
    
    def pause_turn(self): 
        self.timer_counter.stop() 
        lightgames.send_msgs(self.connections, {'pause': True}) 
    def timelimit_counter(self): 
        # A serverside counter of how many seconds left. 
        # Is sent to the clients when they connect. 
        self.template_vars['timeleft'] -= 1
    def timelimit_exceeded(self): 
        """
        The timelimit given to the player has exceeded. This function 
        defines how to handle it. Feel free to override." 
        """ 
        self.turnover() 

    def set_options(self, config):  
        vars = self.template_vars 
        vars['color_1']     = config['color_1']
        vars['color_2']     = config['color_2']
        vars['timelimit']   = max(0, int(config['timelimit']))  
        super().set_options(config) 


    def set_description(self, handler): 
        # Override this in your game to add a description of your game. 
        pass 

