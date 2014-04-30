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
    #template_vars = {
    #    'module_name': 'GIF Animation',
    #    'grid_x': 3,
    #    'grid_y': 3,
    #    'animation_file': 'animations/test3x3.gif',
    #    'playgif': False,
    #    'center_hor': False,
    #    'center_vert': False,
    #    'offset_hor': 0,
    #    'offset_vert': 0,
    #    'transition_time': 4,
    #    'off_color': '#000000',
    #}

    def init(self):
        self.template_vars['module_name'] = 'GIF Animation'
        self.template_vars['animation_file'] = 'animations/test3x3.gif' 
        self.template_vars['playgif'] = False 
        self.template_vars['center_hor'] = False 
        self.template_vars['center_vert'] = False 
        self.template_vars['offset_hor'] = 0 
        self.template_vars['offset_vert'] = 0 
        self.template_vars['transition_time'] = 4 
        
        self.play = False
        self.data = open(self.template_vars['animation_file'], 'rb').read()

        self.grid = lightgames.get_grid_size()
        self.template_vars['grid_x'], self.template_vars['grid_y'] = self.grid

        self.center_hor = self.template_vars['center_hor']
        self.center_vert = self.template_vars['center_vert']
        self.transition_time = self.template_vars['transition_time']
        self.offset_x = self.template_vars['offset_hor']
        self.offset_y = self.template_vars['offset_vert']
        self.transp_color = (0,0,0)

        # keep track of if anything that changed how the image is displayed has changed
        # needed to reset lamps when changing gif or grid offset
        self.changed_display = False
        # keep track of if the animation file has changed
        self.changed_gif = False


    @gen.engine
    def play_animation(self):
        self.reset_lamp_all()
        self.play = True

        while self.play:
            try:
                gif = Image.open(io.BytesIO(self.data))
                (width, height) = gif.size
                #self.template_vars['grid_x'] = width
                #self.template_vars['grid_y'] = height

                # Reset lamps if GIF file has changed
                # since it might be of different dimensions
                if self.changed_gif:
                    self.reset_lamp_all()
                    self.changed_gif = False
                i = 0
                for frame in ImageSequence(gif):
                    # reset lamps when display settings has changed
                    if self.changed_display:
                        self.reset_lamp_all()
                        self.changed_display = False
                    # Break if animation turned off.
                    # Change this accordingly to wait for animation
                    # to finish before turning off/changing animation
                    if not self.play:
                        break
                    tt = self.transition_time
                    i = i+1
                    rgb_im = gif.convert("RGB")
                    # duration of frame is in milliseconds
                    dur = gif.info['duration']
                    buffer = []
                    for y in range(0, min(height,self.grid[1])):
                        for x in range(0, min(width,self.grid[0])):

                            # center the image horizontally
                            x_im = x_grid = x
                            if self.center_hor and width > self.grid[0]:
                                x_im = int( (width - self.grid[0])/2 + x)
                            elif self.center_hor and width < self.grid[0]:
                                x_grid = int( (self.grid[0] - width)/2 + x)
                            # center the image vertically
                            y_im = y_grid = y 
                            if self.center_vert and height > self.grid[1]:
                                y_im = int( (height - self.grid[1])/2 + y)
                            elif self.center_vert and height < self.grid[0]:
                                y_grid = int( (self.grid[0] - height)/2 + y)
                            # offset image horizontally
                            if self.offset_x != 0 and width <= self.grid[0]:
                                x_grid += self.offset_x
                            elif self.offset_x != 0 and width > self.grid[0]:
                                x_im -= self.offset_x
                            # offset image vertically
                            if self.offset_y != 0 and height <= self.grid[1]:
                                y_grid += self.offset_y
                            elif self.offset_y != 0 and height > self.grid[1]:
                                y_im -= self.offset_y

                            # check boundaries that might be off after offset
                            if (0 <= x_im < width
                            and 0 <= x_grid < self.grid[0]
                            and 0 <= y_im < height
                            and 0 <= y_grid < self.grid[1]):
                                r, g, b = rgb_im.getpixel((x_im, y_im))
                                if (r, g, b) != self.transp_color:
                                    buffer += [{'x': x_grid, 'y': y_grid, \
                                                'change': {'rgb': (r,g,b), 'transitiontime':tt, 'on': True}}]
                                    lightgames.send_msgs(self.connections, \
                                                {'x':x_grid, 'y':y_grid, 'color':(r,g,b), 'power':True})
                                else:
                                    buffer += [{'x': x_grid, 'y': y_grid, 'change': {'on': False}}]
                                    lightgames.send_msgs(self.connections, \
                                                {'x':x_grid, 'y':y_grid, 'color':(r,g,b), 'power':False})

                    # only send if theres a lamp to be changed
                    if buffer:
                        self.send_lamp_multi(buffer)
                    yield gen.Task(IOLoop.instance().add_timeout, time.time() + (dur/1000.0))
            except IOError:
                print("Couldn't open image")

        self.send_lamp_all({ 'on': False })

    def set_options(self, config):
        #self.template_vars['cell_w'] = max(2,min(500,int(config['cell_w'])))
        #self.template_vars['cell_h'] = max(2,min(500,int(config['cell_h'])))

        files = config['files']
        if 'animation_file' in files:
            fileinfo = files['animation_file'][0]
            if fileinfo['content_type'] != 'image/gif':
                return "Incorrect content type: %s" % fileinfo['content_type']

            self.data = fileinfo['body']
            self.template_vars['animation_file'] = fileinfo['filename']
            self.changed_gif = True

        if 'center_hor' in config:
            if config['center_hor'] != self.center_hor:
                self.changed_display = True
                if config['center_hor'] == 'true':
                    self.center_hor = True
                else:
                    self.center_hor = False
            self.template_vars['center_hor'] = self.center_hor # remove later

        if 'center_vert' in config:
            if config['center_vert'] != self.center_vert:
                self.changed_display = True
                if config['center_vert'] == 'true':
                    self.center_vert = True
                else:
                    self.center_vert = False
            self.template_vars['center_vert'] = self.center_vert # remove later

        if 'offset_hor' in config:
            try:
                offsx = int(config['offset_hor'])
                if offsx != self.offset_x:
                    self.changed_display = True
                self.template_vars['offset_hor'] = offsx # remove later
                self.offset_x = offsx
            except ValueError:
                print("Couldn't convert string to int")

        if 'offset_vert' in config:
            try:
                offsy = int(config['offset_vert'])
                if offsy != self.offset_y:
                    self.changed_display = True
                self.template_vars['offset_vert'] = offsy # remove later
                self.offset_y = offsy
            except ValueError:
                print("Couldn't convert string to int")

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

        # Taken from http://code.activestate.com/recipes/266466/
        # Edited for Python 3
        def HTMLColorToRGB(colorstring):
            """ convert #RRGGBB to an (R, G, B) tuple """
            colorstring = colorstring.strip()
            if colorstring[0] == '#': colorstring = colorstring[1:]
            if len(colorstring) != 6:
                raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
            r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
            r, g, b = [int(n, 16) for n in (r, g, b)]
            return (r, g, b)

        if 'color_empty' in config:
            try:
                self.transp_color = HTMLColorToRGB(config['color_empty'])
                self.template_vars['color_empty'] = config['color_empty']
            except ValueError:
                print("Couldn't convert HTML color to RGB")


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

