import tornado.escape
import random

import lightgames


def create(client):
    print("Creating paint game")
    return Paint(client)


class Paint(lightgames.Game):
    config_file = "paintconfig.html"
    template_file = "paint.html"
    template_vars = {
        'module_name': 'Paint',
        'grid_x': 15,
        'grid_y': 10,
    }


    def init(self):
        self.playerColors = {}
        self.board = [[-1 for _ in range(self.template_vars['grid_x'])] 
            for _ in range(self.template_vars['grid_y'])]

        self.send_lamp_all({ 'on': True, 'sat':0, 'hue':0, 'bri':0 })

    def on_connect(self, handler):
        self.playerColors[handler] = (
            random.randint(0,255), 
            random.randint(0,255), 
            random.randint(0,255)
        )
        print("Connection %s, color %s" % (handler, self.playerColors[handler]))

        for y in range(len(self.board)):
            for x in range(len(self.board[y])):
                if self.board[y][x] != -1:
                    handler.write_message(
                        tornado.escape.json_encode(
                            {'x':x, 'y':y, 'color':self.board[y][x]}
                        )
                    )

    def on_message(self, handler, message):
        coords = tornado.escape.json_decode(message)
        x = coords['x']
        y = coords['y']
        color = self.playerColors[handler]

        if x<0 or x>=self.template_vars['grid_x'] or \
            y<0 or y>=self.template_vars['grid_y']:
            print('error: out of bounds!')
            return

        self.board[y][x] = color
        for handler in self.playerColors:
            handler.write_message(
                tornado.escape.json_encode(
                    {'x':x, 'y':y, 'color':color}
                )
            )

        self.send_lamp(x, y, { 'rgb': color })

    def on_close(self, handler):
        if handler in self.playerColors:
            del self.playerColors[handler]

    def set_options(self, config):
        m = 50;
        self.template_vars['grid_y'] = max(2,min(m,int(config['grid_y'])))
        self.template_vars['grid_x'] = max(2,min(m,int(config['grid_x'])))
        self.template_vars['cell_w'] = max(2,min(500,int(config['cell_w'])))
        self.template_vars['cell_h'] = max(2,min(500,int(config['cell_h'])))
        self.template_vars['color_empty'] = config['color_empty']

        self.init()
