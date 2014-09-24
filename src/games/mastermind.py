# Playhouse: Making buildings into interactive displays using remotely controllable lights.
# Copyright (C) 2014  John Eriksson, Arvid Fahlström Myrman, Jonas Höglund,
#                     Hannes Leskelä, Christian Lidström, Mattias Palo, 
#                     Markus Videll, Tomas Wickman, Emil Öhman.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import lightgames
import simplegame
import random
from collections import Counter


def create(client):
    print("Creating Mastermind game")
    return Mastermind(client)

class Mastermind(simplegame.SimpleGame):
    template_file = "mastermind.html"

    colors  = None

    columns = [ None, None ]
    row     = 0
    hiddens = [ None, None ]

    def __init__(self, client):
        super().__init__(client)

        self.template_vars['module_name'] = 'Mastermind'
        self.template_vars['title'] = 'Mastermind'
        self.template_vars['grid_x'] = 12
        self.template_vars['grid_y'] = 3

        self.template_vars['color_correct'] = '#FFFFFF'
        self.template_vars['color_almost']  = '#00FFFF'

        self.template_vars['color_1'] = '#FF0000'
        self.template_vars['color_2'] = '#00FF00'
        self.template_vars['color_3'] = '#0000FF'
        self.template_vars['color_4'] = '#FFFF00'
        self.template_vars['color_5'] = '#FF00FF'

        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']

    def reset(self):
        super().reset()

        for y in range(self.height):
            for x in range(self.width):
                self.board[y][x] = 0

        lg, tvars = lightgames, self.template_vars
        self.colors = [ lg.rgb_to_hsl(*lg.parse_color(color)) for color in
                        [ '#000000', tvars['color_correct'], tvars['color_almost'],
                          tvars['color_1'], tvars['color_2'], tvars['color_3'], tvars['color_4'], tvars['color_5'] ] ]

        self.columns = [ 0, self.width - 1 ]
        self.row  = 0
      # self.hiddens = [ [ random.randint(3, len(self.colors)) for y in range(self.height) ] for player in [0, 1] ]
        self.hiddens = [ [ 3, 4, 5 ] for player in [0, 1 ] ]
        self.reset_lamp_all()
        self.sync_all()

    def sync(self, handler):
        super().sync(handler)
        self.set_description(handler)
        print("Syncing %s" % handler)

        self.update_flasher()

        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                hsl = self.colors[self.board[y][x]]
                hue = lightgames.to_lamp_hue(hsl)
                lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'hsl':hsl, 'power':self.board[y][x] != 0})
              # self.send_lamp(x, y, {'sat':255, 'hue':hue})

    def update_flasher(self):
        if None in self.get_players() or self.columns[0] == None \
                                      or self.columns[0] > self.columns[1]:
            # If we don't have a current game, reset flashing status for everyone
            lightgames.send_msgs(self.connections, {'x':None, 'y':None, 'flashing':True})
            return

        playerH = self.get_player(self.player)
        x = self.columns[self.player]
        y = self.row

        lightgames.send_msgs(self.connections, {'x':None, 'y':None, 'flashing':True})
        lightgames.send_msg(playerH, {'x':x, 'y':y, 'flashing':True})

    def on_turnover(self):
        self.update_flasher()

    def on_message(self, handler, msg):
        if not self.correct_player(handler):
            return

        opponent  = 1 - self.player
        playerH   = self.get_player(self.player)
        opponentH = self.get_player(opponent)

        choice = msg['choice']

        x = self.columns[self.player]
        y = self.row

        if not (3 <= choice < len(self.colors)):
            print("Test: %d %d" % (choice, len(self.colors)))
            lightgames.send_msg(playerH, {'error':'Invalid choice!'})

        elif self.board[y][x] != 0:
            lightgames.send_msg(playerH, {'error':'You have already made a guess there!'})

        else:
            # "Tile" unoccupied; register the guess
            self.board[y][x] = choice

            hsl = self.colors[choice]
            hue = lightgames.to_lamp_hue(hsl)

            lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'hsl':hsl, 'power':True})
            self.send_lamp(x, y, {'sat':255, 'hue':hue})

            self.row += 1
            self.update_flasher()

            # Check for full column
            guess  = [self.board[y_][x] for y_ in range(self.height)]
            hidden = self.hiddens[self.player]

            if all(v != 0 for v in guess):
                counts = Counter(hidden)
                corrects, almosts = 0, 0

                for i in range(self.height):
                    if guess[i] == hidden[i]:
                        corrects += 1
                        counts[guess[i]] -= 1
                    elif counts[guess[i]] > 0:
                        counts[guess[i]] -= 1
                        almosts += 1

                if corrects == self.height:
                    # player won
                    simplegame.game_over(self, playerH)
                    return

                # player didn't win--provide response
                d = +1 if self.player == 0 else -1 # the direction the player is progressing

                for y_ in range(corrects):
                    self.board[y_           ][x + d] = 1
                for y_ in range(almosts):
                    self.board[y_ + corrects][x + d] = 2

                changes = []
                for y_ in range(self.height):
                    v = self.board[y_][x + d]
                    hsl = self.colors[v]
                    hue = lightgames.to_lamp_hue(hsl)
                    if v != 0: changes += [{'x':x, 'y':y, 'change': {'sat':255, 'hue':hue}}]
                    lightgames.send_msgs(self.connections, {'x':x + d, 'y':y_, 'hsl':hsl, 'power':v != 0})
                self.send_lamp_multi(changes)

                self.columns[self.player] += d * 2

                # Check if last turn and last player
                if self.columns[0] > self.columns[1]:
                    simplegame.game_over(self, None)
                    return

                self.row = 0
                self.turnover()


    def set_description(self, handler):
        message = '<p><p><b>Name:</b> Mastermind</p><p><b>Players:</b> 2</p><p><b>Rules & Goals:</b> The rules in this variant vary slightly from those of standard Mastermind. The game starts with each player choosing a 3-color code from a pool of 6 colors. Both players then tries to guess what code the other player chose. After every turn, players receive feedback indicating how many of the colors they guess correctly. Blue means the color in that location is correct, red that the color exists in another location, and black the the color is not in the code. The player who finds the correct code in the fewest guesses wins. </p></p>'
        lightgames.send_msg(handler, {'rulemessage': (message)})

