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


def create(client):
    print("Turning off lamps")
    return Off(client)


class Off(lightgames.Game):
    """A 'game' used to easily turn off the lights when not needed"""

    template_file = "off.html"
    template_vars = { 'module_name': 'Off',
			'color_1': '#FF0000',
			'color_2': '#FF0000',
			'color_empty': '#FF0000',
			'timelimit': 0,
			'score_1': 0,
			'score_2': 0
		       	}


    def __init__(self, client):
        super().__init__(client)

        self.template_vars['grid_x'] = 18
        self.template_vars['grid_y'] = 3

        self.template_vars['color_correct'] = '#FFFFFF'
        self.template_vars['color_almost']  = '#FFFFFF'

        self.template_vars['colors'] = [ '#FF0000',
                                         '#00FF00',
                                         '#0000FF',
                                         '#FFFF00',
                                         '#FF00FF' ]
    def reset(self):
        self.send_lamp_all({ "on": False })

