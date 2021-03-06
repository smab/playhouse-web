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
import time
from tornado import gen
from tornado.ioloop import IOLoop

def create(client):
    print("Creating Diagnostics tool")
    return Diagnostics(client)

class Diagnostics(lightgames.Game):
    config_file = "diagnosticsconfig.html"
    template_vars = {
        'module_name': 'Diagnostics tool',
        'run': True,
        'delay': 500
    }

    def init(self):
        self.on = self.template_vars['run']
        self.grid = lightgames.get_grid_size()
        print(self.grid)
        self.delay = self.template_vars['delay']
        self.reset_lamp_all()
        if self.on:
            self.run()

    def destroy(self):
        super().destroy()
        self.on = False

    @gen.engine
    def run(self):
        self.on = True
        while self.on:
            width, height = lightgames.get_grid_size()
            for x in range(width+1):
                if self.on == False:
                    break
                changes = []
                for y in range(height):
                    if x != width:
                        changes += [{'x': x,'y': y,'change': {'sat':255, 'transitiontime':0}}]
                    if x != 0:
                        changes += [{'x': x-1,'y': y,'change': {'sat':0, 'transitiontime':0}}]
                self.send_lamp_multi(changes)
                yield gen.Task(IOLoop.instance().add_timeout, time.time() + (self.delay/1000.0))

            for y in range(height+1):
                if self.on == False:
                    break
                changes = []
                for x in range(width):
                    if y != height:
                        changes += [{'x': x,'y': y,'change': {'sat':255, 'transitiontime':0}}]
                    if y != 0:
                        changes += [{'x': x,'y': y-1,'change': {'sat':0, 'transitiontime':0}}]
                self.send_lamp_multi(changes)
                yield gen.Task(IOLoop.instance().add_timeout, time.time() + (self.delay/1000.0))


    def set_options(self, config):
        if 'delay' in config:
            try:
                d = int(config['delay'])
                self.template_vars['delay'] = d
                self.delay = d
            except ValueError:
                print("Couldn't convert string to int")

        if 'run' in config:
            if config['run'] == 'on' and self.on == False:
                self.run()
            elif config['run'] == 'off':
                self.on = False
            self.template_vars['run'] = self.on
