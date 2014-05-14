import random
import itertools
import time
from tornado import gen
from tornado.ioloop import IOLoop

import simplegame 
import lightgames


def create(client):
    print("Creating memory game")
    return Memory(client)


class Memory(simplegame.SimpleGame):
    template_file = "memory.html"
    config_file   = "memoryconfig.html"

    #hues = itertools.cycle([5000, 15000, 25000, 35000, 45000, 55000, 65000])
    hues = itertools.cycle([5000, 15000, 25000, 45000, 55000, 65000, 75000])

    def __init__(self, client): 
        super().__init__(client) 
        self.template_vars['module_name'] = 'Memory'
        self.template_vars['title'] = 'Memory' 
        self.template_vars['grid_x'] = 8
        self.template_vars['grid_y'] = 6
        self.template_vars['score_1'] = 0 
        self.template_vars['score_2'] = 0 
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']


    def reset(self):
        # Unfortunatly we generate two seperate boards and trashes one
        super().reset() 

        self.scores  = [0, 0]
        self.active_tiles = []

        coords = [(x,y) for x in range(self.width) for y in range(self.height)]
        random.shuffle(coords)

        # Sign determines whether tile is visible (negative = not visible),
        # magnitude determines hue.
        self.board = [[0 for x in range(self.width)] for y in range(self.height)]
        while len(coords) > 0:
            hue = next(self.hues)
            (x1,y1) = coords.pop()
            (x2,y2) = coords.pop()
            self.board[y1][x1] = -hue
            self.board[y2][x2] = -hue


    def sync(self, handler):
        super().sync(handler) 
        print("Syncing %s" % handler)
        for y in range(self.height):
            for x in range(self.width):
                powered = self.board[y][x] >= 0
                hue     = self.board[y][x] if powered else 0
                lightgames.send_msg(handler, {'x':x, 'y':y, 'hue':hue, 'power':powered})

    @gen.engine
    def on_message(self, handler, message):
        # Checks that it's the correct player. 
        if not self.correct_player(handler):
            return

        playerH   = self.get_player(self.player)
        #opponentH = self.get_player(1 - self.player)

        x, y = message['x'], message['y']

        if self.board[y][x] < 0:
            self.board[y][x] *= -1
            self.active_tiles.append((x,y))

            self.send_lamp(x, y, {'sat': 255, 'hue': self.board[y][x]})
            lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'hue':self.board[y][x], 'power':True})

            # Each player toggles two tiles per turn
            if len(self.active_tiles) == 2:
                (x1,y1) = self.active_tiles[0]
                (x2,y2) = self.active_tiles[1]
                color1  = self.board[y1][x1]
                color2  = self.board[y2][x2]

                if color1 == color2:
                    self.scores[self.player] += 1
                    self.template_vars['score_1'], self.template_vars['score_2'] = self.scores
                    # Guessed correctly; player gets to keep going
                    yield gen.Task(IOLoop.instance().add_timeout, time.time() + 1)
                    self.turnover(self.player) 

                else:
                    self.board[y1][x1] *= -1
                    self.board[y2][x2] *= -1

                    lightgames.send_msgs(self.connections,
                            {'x':x1, 'y':y1, 'hue':0, 'power':False, 'delay':2000})
                    lightgames.send_msgs(self.connections,
                            {'x':x2, 'y':y2, 'hue':0, 'power':False, 'delay':2000})

                    self.send_lamp(x1, y1, {'sat': 0, 'hue': 0})
                    self.send_lamp(x2, y2, {'sat': 0, 'hue': 0})

                    # Switch over to opponent. Since there is a delay we do not use SimpleGame's turnover. 
                    #lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
                    #tmp = 1 - self.player                    
                    #self.player = None 
                    self.pause_turn() 
                    yield gen.Task(IOLoop.instance().add_timeout, time.time() + 2)
                    #self.player = tmp
                    #lightgames.send_msg(opponentH, {'message':'Your turn!'})
                    self.turnover() 


                self.active_tiles = []

            # Check if the board is full
            if all(all(hue >= 0 for hue in row) for row in self.board):
                winner = None
                if   self.scores[0] > self.scores[1]: winner = self.get_player(0)
                elif self.scores[0] < self.scores[1]: winner = self.get_player(1)

                simplegame.game_over(self, winner)
                return

        else:
            lightgames.send_msg(playerH, {'error':'Invalid move!'})


    def set_options(self, config):

        def is_even(n): return n % 2 == 0
        if not is_even(int(config['grid_x']) * int(config['grid_y'])):
            return "Bad grid size: must have even number of bricks"
        
        # Since these variables are expected in super-methods we have to add 
        # them here. A bit ugly. Could also be added as a hidden element in 
        # the templates if that is prettier. 
        config['color_1'] = '#CCCCCC' 
        config['color_2'] = '#CCCCCC' 
        return super().set_options(config) 


    def set_description(self, handler):
        message = '<p><p><b>Name:</b> Memory</p><p><b>Players:</b> 2</p><p><b>Rules & Goals:</b> Each player takes turns flipping over a card. If a player manages to flip over two identical cards that player recieve one point, and the cards stay revealed. When all the cards have been revealed the game is over and the player with highest score wins.</p></p>'
        lightgames.send_msg(handler, {'rulemessage': (message)})

# vim: set sw=4:
