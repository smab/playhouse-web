import lightgames


def create(client):
    print("Creating connect-4 game")
    return Connect4(client)


class Connect4(lightgames.Game):
    template_file = "connect4.html"
    config_file   = "baseconfig.html"
    template_vars = {
        'module_name': 'Connect 4',
        'grid_x':      7,
        'grid_y':      6,
    }

    width, height = template_vars['grid_x'], template_vars['grid_y']

    colors = [0, 50000, 65000]

    def reset(self):
        print("New game!")
        print("Size: %d %d" % (self.template_vars['grid_x'], self.template_vars['grid_y']))
        self.width, self.height = self.template_vars['grid_x'], self.template_vars['grid_y']

        self.player  = 0
        self.players = [None, None]
        self.board   = [[2 for x in range(self.width)] for y in range(self.height)]

        for h in self.connections:
            lightgames.send_msg(h, {'gamestate': 'reset'})

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
        if self.player == None:
            lightgames.reply_wrong_player(self, handler)
            return

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

        if self.board[y][x] == 2 and (y == self.height - 1 or self.board[y + 1][x] != 2):
            player = self.player
            self.player = None

            self.board[y][x] = player

            def done():
                # Turn the final lamps on
                self.send_lamp(x, y, {'sat': 255, 'hue': hue, 'transitiontime': 10})
                lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'hue':hue, 'power':True, 'transitiontime':10, 'move':True})

                # Check if this move caused a win
                winner_lamps = set()
                for (dx,dy) in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                    lefts  = grab_ray((x,y), ( dx, dy))
                    rights = grab_ray((x,y), (-dx,-dy))

                    if len(lefts) + len(rights) - 1 >= 4:
                        winner_lamps.update(lefts)
                        winner_lamps.update(rights)

                if len(winner_lamps) > 0:
                    lightgames.game_over(self, playerH, lamps = winner_lamps)
                    return

                # Check for full board
                if all(all(i != 2 for i in j) for j in self.board):
                    lightgames.game_over(self, None)
                    self.reset()
                    return

                # Switch player
                self.player = 1 - player
                lightgames.send_msg(playerH,   {'message':'Waiting on other player...'})
                lightgames.send_msg(opponentH, {'message':'Your turn!'})

            # Perform piece-dropping animation
            coords = []
            for ty in range(0, y):
                coords += [ (x, ty) ]
            self.send_lamp_animation(coords, { 'sat': 255, 'hue': hue }, revert = True, callback = done)
            lightgames.send_msgs_animation(self.connections, coords, { 'hue':hue, 'power':True }, revert = True)

        else:
            lightgames.send_msg(playerH, {'error':'Invalid move!'})


    def set_options(self, config):
        def clamp(low, x, high):
            return max(low, min(high, x))

        m = 50
        vars = self.template_vars
        vars['grid_y']      = clamp(2, int(config['grid_y']),            m)
        vars['grid_x']      = clamp(2, int(config['grid_x']),            m)
        vars['cell_w']      = clamp(2, int(config['cell_w']),          500)
        vars['cell_h']      = clamp(2, int(config['cell_h']),          500)

        self.reset()

# vim: set sw=4:
