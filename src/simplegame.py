import datetime
import functools

import tornado.ioloop

import lightgames 


def reply_wrong_player(game, handler):
    if handler in game.get_players():
        print("Wrong player")
        lightgames.send_msg(handler, {'error':'Not your turn!'})
    else:
        print("Spectator")
        lightgames.send_msg(handler, {'error':'You are not a player!'})

def game_over(game, winnerH, coords = frozenset()):
    if winnerH == None:
        lightgames.send_msgs(game.get_players(), {'state': 'gameover'})
        lightgames.send_msgs(game.connections,   {'message': 'The game tied'})
        print("The game tied")

    else:
        winner = game.get_players().index(winnerH)
        lightgames.send_msg(winnerH, {'state': 'gameover', 'message': 'You won!'})
        lightgames.send_msgs((p for p in game.get_players() if p != winnerH),
                          {'state': 'gameover', 'message': 'You lost!'})
        lightgames.send_msgs(game.get_spectators(), 
                          {'message': "Player %d won" % (winner + 1)})
        print("Player %d wins!" % winner)

    changes = []
    for (x,y) in coords:
        changes += [ { 'x': x, 'y': y,             'change': { 'alert': 'lselect' } },
                     { 'x': x, 'y': y, 'delay': 3, 'change': { 'alert': 'none'    } } ]
    game.send_lamp_multi(changes)

    game.player = None
    lightgames.set_timeout(datetime.timedelta(seconds = len(coords) + 5), game.reset)
    lightgames.set_timeout(datetime.timedelta(seconds = len(coords) + 5), functools.partial(alert_lamps, game))

def alert_lamps(game): 
    game.send_lamp_all({'alert': 'select'}) 


# A SimpleGame is a turnbased board game between two players who each may have 
# a color, score, and a timelimit. 
# Examples include Tic-tac-toe, Connect4, and Othello. 
class SimpleGame(lightgames.Game): 
    config_file = "simplegameconfig.html" 

    def __init__(self, client): 
        lightgames.Game.__init__(self, client) 

        # Default board, colors, and timelimits 
        self.template_vars['color_1']   = '#FF0000' 
        self.template_vars['color_2']   = '#0000FF'
        self.template_vars['timelimit'] = 20 
        self.template_vars['timeleft']  = self.template_vars['timelimit']
        self.template_vars['score_1']   = None 
        self.template_vars['score_2']   = None 

        # A handler for the timer and a handler that keeps track of the 
        # timelimit counter server side. 
        self.timer_counter = tornado.ioloop.PeriodicCallback(self.timelimit_counter, 1000)

    def init(self):
        super().init()

        self.queue.addplayer_callback = self.on_add_player
        self.queue.removeplayer_callback = self.on_remove_player
        self.queue.set_num_players(2)

    def reset(self): 
        """
        Sets up everything with timelimits, turn indications, etc. 

        If you override this, you likely want to invoke this method manually!
        """
        # Sets up the board and tries to fetch two new players. 
        self.game_started = False
        self.timer_counter.stop() 
        self.player = 0 
        self.tmp_player = None 
        self.player_passes = [0, 0] # refering to how many timelimit's they've triggered (in a row) 
        self.width  = self.template_vars['grid_x'] 
        self.height = self.template_vars['grid_y'] 
        self.board  = [[2 for x in range(self.width)] for y in range(self.height)]
        self.queue.remove_all_players()

        self.template_vars['timeleft'] = self.template_vars['timelimit']

        lg, tvars = lightgames, self.template_vars
        self.colors = [ lg.rgb_to_hsl(*lg.parse_color(tvars['color_1'])),
                        lg.rgb_to_hsl(*lg.parse_color(tvars['color_2'])),
                        lg.rgb_to_hsl(*lg.parse_color(tvars['color_empty'])) ]

        for h in self.connections:
            lightgames.send_msg(h, {'gamestate': 'reset'})

        self.sync_all()
        self.reset_lamp_all()
        self.queue.try_get_new_players()

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
        if None not in self.get_players(): 
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


    def get_player(self, idx):
        return self.get_players()[idx]

    def get_players(self):
        return self.queue.get_player_handlers()

    def get_spectators(self):
        """
        Generator for spectators, handy for use with `send_msg_many`.
        """
        for h in self.connections:
            if h not in self.get_players():
                yield h

    def on_add_player(self, player):
        handler = self.get_player(player)
        print("Add player: %s" % handler)

        print("Connection %s as player %d" % (handler, player))
        lightgames.send_msg(handler, { 
                            'state':   'playing',
                            'playerId': player+1, 
                            'message': 'You are player %d' % (player + 1) })
        self.sync(handler)

        if not self.game_started:
            # A player has been added. If this is the second player, 
            # we start the timer. 
            if handler in self.get_players() and None not in self.get_players(): 
                self.game_started = True
                if self.player == None: 
                    self.turnover(self.tmp_player) 
                else: 
                    self.turnover(self.player) 

    def on_remove_player(self, player):
        if self.game_started:
            lightgames.send_msg(self.get_player(1-player), { 
                                "message": "You are a spectator!", 
                                "error": "Your opponent left", 
                                "state": "gameover", 
            })
            self.reset()

    def on_enqueue(self, handler):
        super().on_enqueue(handler)

        self.queue.try_get_new_players()


    # Returns True if it is this player's turn 
    def correct_player(self, handler): 
        """
        Checks if this handler corresponds with the current player. Returns 
        true if that is the case, or sends an error to the client otherwise. 
        """
        if self.player == None:
            return False 
        elif handler != self.get_player(self.player): 
            reply_wrong_player(self, handler)
            return False 
        return True 

    def turnover(self, to_player=None): 
        """
        Changes the turn to to_player and starts the timelimit if specified. 
        If the timelimit was paused, this function will start it again. 
        """
        self.timer_counter.stop() 

        if self.player == None: 
            self.player = self.tmp_player 
            self.tmp_player = None 

        if self.template_vars['timeleft'] != None and self.template_vars['timeleft'] > 0: 
            # The turnover was not because of exceeded timelimit; reset the 
            # number of passes that player has done 
            self.player_passes[self.player] = 0 
            
        self.template_vars['timeleft'] = self.template_vars['timelimit'] 

        if to_player == None:  
            self.player = 1 - self.player 
        else: 
            self.player = to_player 

        lightgames.send_msg(self.get_player(self.player),   {'message':'Your turn!'}) 
        lightgames.send_msg(self.get_player(1-self.player), {'message':'Waiting on other player...'})

        self.timer_counter = tornado.ioloop.PeriodicCallback(self.timelimit_counter, 1000)
        self.sync_all() 
        if None not in self.get_players() and self.template_vars['timelimit'] != None: 
            self.timer_counter.start() 

    def pause_turn(self): 
        """
        Tells the client to pause the timelimit counter. This should be used 
        when doing animations. 
        """ 
        self.timer_counter.stop() 
        self.tmp_player = self.player 
        self.player = None 
        lightgames.send_msgs(self.connections, {'pause': True}) 

    def unpause_turn(self): 
        """
        Tells the client to start the timelimit counter again. 
        """ 
        if self.player == None: 
            self.player = self.tmp_player 
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
            lightgames.send_msgs(self.get_players(), {
                                "message": "You are a spectator!", 
                                "error": "Kicked due to inactivity", 
                                "state": "gameover", 
            })
            self.reset()
        else: 
            self.turnover() 

    def set_options(self, config):
        tvars = self.template_vars 
        tvars['color_1']   = config['color_1']
        tvars['color_2']   = config['color_2']
        if int(config['timelimit']) <= 0: 
            tvars['timelimit'] = None 
        else: 
            tvars['timelimit'] = int(config['timelimit'])
        return super().set_options(config) 


