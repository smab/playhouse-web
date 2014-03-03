import lightgames


def create(client):
    print("Creating connect-4 game")
    return Connect4(client)


class Connect4(lightgames.Game):
    template_file = "connect4.html"
    template_vars = {
        'module_name': 'Connect 4',
        'grid_x':      7,
        'grid_y':      6,
    }

    width, height = template_vars['grid_x'], template_vars['grid_y']

    colors = [0, 50000, 65000]

    def reset(self):
        print("New game!")

        self.player  = 0
        self.players = [None, None]
        self.board   = [[2 for x in range(self.width)] for y in range(self.height)]

        self.try_get_new_players(2)
        self.sync_all()
        self.reset_lamp_all()

    def sync(self, handler):
        print("Syncing %s" % handler)
        for y in range(self.height):
            for x in range(self.width):
                hue     = self.colors[self.board[y][x]]
                powered = self.board[y][x] != 2
                lightgames.send_msg(handler, {'x':x, 'y':y, 'hue':hue, 'power':powered})

    def on_message(self, handler, message):
        playerH   = self.players[self.player]
        opponentH = self.players[1 - self.player]

        if playerH != handler:
            lightgames.reply_wrong_player(self, handler)
            return

        # playerH == handler
        x, y = message['x'], message['y']
        hue  = self.colors[self.player]

        def grab_ray(pos, delta):
            x, y   = pos
            dx, dy = delta
            res    = set()

            def within_bounds(x,y):
                return 0 <= x < self.width and 0 <= y < self.height

            while within_bounds(x,y) and self.board[y][x] == self.player:
                res.add((x,y))
                x,y = x + dx, y + dy

            return res

        if self.board[y][x] == 2 and (y == self.height - 1 or
                                        self.board[y + 1][x] != 2):
            self.board[y][x] = self.player

            self.send_lamp(x, y, {'sat': 255, 'hue': hue})
            lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'hue':hue, 'power':True})

            lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
            lightgames.send_msg(opponentH, {'message':'Your turn!'})

            # Check if this move caused a win
            winner_lamps = set()
            for (dx,dy) in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                lefts  = grab_ray((x,y), ( dx, dy))
                rights = grab_ray((x,y), (-dx,-dy))

                if len(lefts) + len(rights) - 1 >= 4:
                    winner_lamps.update(lefts)
                    winner_lamps.update(rights)

            if len(winner_lamps) > 0:
                lightgames.send_msg(playerH,                {'message':'You won!'})
                lightgames.send_msg(opponentH,              {'message':'You lost!'})
                lightgames.send_msgs(self.get_spectators(), {'message':"Player %d won" % (self.player+1)})

                print("Player %d wins!" % self.player)
                self.reset()
                return

            # Check for full board
            if all(all(i != 2 for i in j) for j in self.board):
                print("The game tied")
                lightgames.send_msgs(self.connections, {'message':"The game tied"})
                self.reset()
                return

            # Switch player
            self.player = 1 - self.player

        else:
            lightgames.send_msg(playerH, {'error':'Invalid move!'})

# vim: set sw=4:
