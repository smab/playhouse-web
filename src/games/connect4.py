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

import simplegame 
import lightgames

def create(client):
    print("Creating connect-4 game")
    return Connect4(client)


class Connect4(simplegame.SimpleGame):
    template_file = "connect4.html"
    config_file   = "simplegameconfig.html" 

    def __init__(self, client):
        super().__init__(client) 

        self.template_vars['module_name'] = 'Connect4' 
        self.template_vars['title'] = 'Connect4' 
        self.template_vars['grid_x'] = 7 
        self.template_vars['grid_y'] = 6 
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']


    def sync(self, handler):
        super().sync(handler) 
        print("Syncing %s" % handler)
        for y in range(self.height):
            for x in range(self.width):
                hsl     = self.colors[self.board[y][x]]
                powered = self.board[y][x] != 2
                lightgames.send_msg(handler, {'x':x, 'y':y, 'hsl':hsl, 'power':powered, 'move':True})


    @lightgames.validate_xy
    def on_message(self, handler, message):
        if not self.correct_player(handler): 
            return 

        playerH   = self.get_player(self.player)

        x, y = message['x'], message['y']
        hsl  = self.colors[self.player]
        hue  = lightgames.to_lamp_hue(hsl)

        def grab_ray(pos, delta, player):
            x, y   = pos
            dx, dy = delta
            res    = set()

            def within_bounds(x,y):
                return 0 <= x < self.width and 0 <= y < self.height
            while within_bounds(x,y) and self.board[y][x] == player:
                res.add((x,y))
                x,y = x + dx, y + dy

            return res

        if self.board[y][x] == 2 and (y == self.height - 1 or self.board[y + 1][x] != 2):
            player = self.player
            self.pause_turn()   # Pause the timecounter 
            self.board[y][x] = player

            def done():
                # Turn the final lamps on
                self.send_lamp(x, y, {'sat': 255, 'hue': hue, 'transitiontime': 10, 'bri': 255})
                lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'hsl':hsl, 'power':True, 'transitiontime':10, 'move':True})

                # Check if this move caused a win
                winner_lamps = set()
                for (dx,dy) in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                    lefts  = grab_ray((x,y), ( dx, dy), player)
                    rights = grab_ray((x,y), (-dx,-dy), player)

                    if len(lefts) + len(rights) - 1 >= 4:
                        winner_lamps.update(lefts)
                        winner_lamps.update(rights)

                if len(winner_lamps) > 0:
                    simplegame.game_over(self, playerH, coords = winner_lamps)
                    return

                # Check for full board
                if all(all(i != 2 for i in j) for j in self.board):
                    simplegame.game_over(self, None)
                    self.reset()
                    return

                # Switch player
                self.player = player # Set it back. May cause problems? Probably not.  
                self.turnover() 

            # Perform jaw-dropping animation
            coords = []
            for ty in range(0, y):
                coords += [ (x, ty) ]
            self.send_lamp_animation(coords, { 'sat': 255, 'hue': hue }, revert = True, callback = done)
            lightgames.send_msgs_animation(self.connections, coords, { 'hsl':hsl, 'power':True }, revert = True)

        else:
            lightgames.send_msg(playerH, {'error':'Invalid move!'})


    def set_description(self, handler):
        message ='<p><p><b>Name:</b> Connect4</p><p><b>Players:</b> 2</p><p><b>Rules & Goals:</b> Each player takes turns to drop their coloured circles from the top straight down in a chosen column. The first player to connect four circles vertically, horizontally or diagonally wins the game.</p></p>'
        lightgames.send_msg(handler, {'rulemessage': (message)})


# vim: set sw=4:
