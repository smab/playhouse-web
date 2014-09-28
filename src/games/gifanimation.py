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

    def init(self):
        self.template_vars['module_name'] = 'GIF Animation'
        self.template_vars['title'] = 'GIF Animation' 
        self.template_vars['animation_file'] = 'animations/test3x3.gif' 
        self.template_vars['playgif'] = False 
        self.template_vars['center_hor'] = False 
        self.template_vars['center_vert'] = False 
        self.template_vars['offset_hor'] = 0 
        self.template_vars['offset_vert'] = 0 
        self.template_vars['transition_time'] = 4 
        self.template_vars['color_off'] = '#000000'
        
        self.play = False
        self.data = open(self.template_vars['animation_file'], 'rb')

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

        self.gif_animator = lightgames.GIFAnimation(self)

    def destroy(self):
        super().destroy()
        self.play = False
        self.gif_animator.cancel()
        self.gif_animator.close()

    def play_animation(self):
        self.reset_lamp_all()
        self.play = True

        try:
            #for y in range(0, min(height,self.grid[1])):
                #for x in range(0, min(width,self.grid[0])):
                    ## center the image horizontally
                    #x_im = x_grid = x
                    #if self.center_hor and width > self.grid[0]:
                        #x_im = int( (width - self.grid[0])/2 + x)
                    #elif self.center_hor and width < self.grid[0]:
                        #x_grid = int( (self.grid[0] - width)/2 + x)
                    ## center the image vertically
                    #y_im = y_grid = y
                    #if self.center_vert and height > self.grid[1]:
                        #y_im = int( (height - self.grid[1])/2 + y)
                    #elif self.center_vert and height < self.grid[0]:
                        #y_grid = int( (self.grid[0] - height)/2 + y)
                    ## offset image horizontally
                    #if self.offset_x != 0 and width <= self.grid[0]:
                        #x_grid += self.offset_x
                    #elif self.offset_x != 0 and width > self.grid[0]:
                        #x_im -= self.offset_x
                    ## offset image vertically
                    #if self.offset_y != 0 and height <= self.grid[1]:
                        #y_grid += self.offset_y
                    #elif self.offset_y != 0 and height > self.grid[1]:
                        #y_im -= self.offset_y

            self.data.seek(0)
            self.gif_animator.run_animation(
                self.data, bounds=self.grid, offset=(self.offset_x, self.offset_y),
                transitiontime=self.transition_time, transparentcolor=self.transp_color)
        except IOError:
            print("Couldn't open image")

    def set_options(self, config):
        files = config['files']
        if 'animation_file' in files:
            fileinfo = files['animation_file'][0]
            if fileinfo['content_type'] != 'image/gif':
                return "Incorrect content type: %s" % fileinfo['content_type']

            self.data = io.BytesIO(fileinfo['body'])
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

        if 'color_off' in config:
            try:
                self.transp_color = lightgames.HTMLColorToRGB(config['color_off'])
                self.template_vars['color_off'] = config['color_off']
            except ValueError:
                print("Couldn't convert HTML color to RGB")

        if 'playgif' in config:
            if config['playgif'] == 'on':
                self.play_animation()
            elif config['playgif'] == 'off':
                self.gif_animator.cancel()
                self.play = False
            self.template_vars['playgif'] = self.play

        return super().set_options(config)

