import random
import itertools

import lightgames


def create(client):
    print("Creating memory game")
    return Memory(client)


class Memory(lightgames.Game):
    template_file = "memory.html"
    config_file   = "baseconfig.html"
    template_vars = {
        'module_name': 'Memory',
        'grid_x':      6,
        'grid_y':      4,
    }

    width, height = template_vars['grid_x'], template_vars['grid_y']
    hues = itertools.cycle([5000, 15000, 25000, 35000, 45000, 55000, 65000])

    active_tiles = []


    def reset(self):
        print("New game!")

        # Reset game state
        self.player = 0
        self.players = [None, None]
        self.scores  = [0, 0]

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

        self.try_get_new_players(2)
        self.sync_all()
        self.reset_lamp_all()
      # # try to get two new players from queue
      # self.add_player(self.queue.get_first())
      # self.add_player(self.queue.get_first())

      # for handler in self.connections:
      #     self.sync(handler)

      # self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0 })

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(self.height):
            for x in range(self.width):
                powered = self.board[y][x] >= 0
                hue     = self.board[y][x] if powered else 0
                lightgames.send_msg(handler, {'x':x, 'y':y, 'hue':hue, 'power':powered})

    def on_message(self, handler, message):
        playerH   = self.players[self.player]
        opponentH = self.players[1 - self.player]

        if playerH != handler:
            lightgames.reply_wrong_player(self, handler)
            return

        # playerH == handler
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
                    # Guessed correctly; player gets to keep going

                else:
                    self.board[y1][x1] *= -1
                    self.board[y2][x2] *= -1

                    lightgames.send_msgs(self.connections,
                            {'x':x1, 'y':y1, 'hue':0, 'power':False, 'delay':2000})
                    lightgames.send_msgs(self.connections,
                            {'x':x2, 'y':y2, 'hue':0, 'power':False, 'delay':2000})

                    self.send_lamp(x1, y1, {'sat': 0, 'hue': 0})
                    self.send_lamp(x2, y2, {'sat': 0, 'hue': 0})

                    # Switch over to opponent
                    lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
                    lightgames.send_msg(opponentH, {'message':'Your turn!'})
                    self.player = 1 - self.player

                self.active_tiles = []

            # Check if the board is full
            if all(all(hue >= 0 for hue in row) for row in self.board):
                winner = None
                if   self.scores[0] > self.scores[1]: winner = self.players[0]
                elif self.scores[0] < self.scores[1]: winner = self.players[1]

                lightgames.game_over(self, winner)
                return

        else:
            lightgames.send_msg(playerH, {'error':'Invalid move!'})

# vim: set sw=4:
