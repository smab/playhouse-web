from PIL import Image
from tornado import gen
from tornado.ioloop import IOLoop
import time
import io

import lightgames

def create(client):
    print("Creating GIF animation")
    return GifAnimation(client)

class GifAnimation(lightgames.Game):
    config_file = "gifconfig.html"
    template_file = "gifanimation.html"
    template_vars = {
        'module_name': 'GIF Animation',
        'grid_x': 3,
        'grid_y': 3,
        'animation_file': 'animations/test3x3.gif',
        'playgif': False,
        'center': False,
        'transition_time': 4
    }

    def init(self):
        self.play = False
        self.data = open(self.template_vars['animation_file'], 'rb').read()

        self.grid = lightgames.get_grid_size()
        self.template_vars['grid_x'], self.template_vars['grid_y'] = self.grid

        self.center = self.template_vars['center']
        self.transition_time = self.template_vars['transition_time']


    @gen.engine
    def play_animation(self):
        self.play = True

        while self.play == True:
            try:
                gif = Image.open(io.BytesIO(self.data))
                (width, height) = gif.size
                #self.template_vars['grid_x'] = width
                #self.template_vars['grid_y'] = height
                i = 0
                for frame in ImageSequence(gif):
                    if self.play == False:
                        break
                    tt = self.transition_time
                    i = i+1
                    rgb_im = gif.convert("RGB")
                    dur = gif.info['duration']
                    buffer = []
                    for y in range(0, min(height,self.grid[1])):
                        for x in range(0, min(width,self.grid[0])):

                            # center the image
                            x_im = x_grid = x
                            if(self.center and width > self.grid[0]):
                                x_im = int( (width - self.grid[0])/2 + x)
                            elif(self.center and width < self.grid[0]):
                                x_grid = int( (self.grid[0] - width)/2 + x)

                            r, g, b = rgb_im.getpixel((x_im, y))
                            buffer += [{'x': x_grid, 'y': y, 'change': {'rgb': (r,g,b), 'transitiontime':tt}}]
                            lightgames.send_msgs(self.connections, {'x':x_grid, 'y':y, 'color':(r,g,b)})

                    self.send_lamp_multi(buffer)
                    yield gen.Task(IOLoop.instance().add_timeout, time.time() + (dur/1000.0))
            except IOError:
                print("Couldn't open image")

        self.send_lamp_all({ 'on': False })

    def set_options(self, config):
        self.template_vars['cell_w'] = max(2,min(500,int(config['cell_w'])))
        self.template_vars['cell_h'] = max(2,min(500,int(config['cell_h'])))

        files = config['files']
        if 'animation_file' in files:
            fileinfo = files['animation_file'][0]
            if fileinfo['content_type'] != 'image/gif':
                return "Incorrect content type: %s" % fileinfo['content_type']

            self.data = fileinfo['body']
            self.template_vars['animation_file'] = fileinfo['filename']

        if 'center' in config:
            if config['center'] == 'true':
                self.center = True
            else:
                self.center = False
            self.template_vars['center'] = self.center

        if 'transitiontime' in config:
            try:
                tt = int(config['transitiontime'])
                self.template_vars['transition_time'] = tt
                self.transition_time = tt
            except ValueError:
                print("Couldn't convert string to int")

        if 'playgif' in config:
            if config['playgif'] == 'on' and self.play == False:
                self.play_animation()
            elif config['playgif'] == 'off':
                self.play = False
            self.template_vars['playgif'] = self.play


class ImageSequence:
    def __init__(self, im):
        self.im = im
    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError # end of sequence

