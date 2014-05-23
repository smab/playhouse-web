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

import tornado.ioloop
import tornado.web
import tornado.websocket

import manager


BRIDGES = {
    "bridges": {
        "001788182e78": {
            "ip": "130.237.228.58:80", 
            "username": "a0e48e11876b8971eb694151aba16ab", 
            "valid_username": True, 
            "lights": 3
        }, 
        "001788182c73": {
            "ip": "130.237.228.213:80", 
            "username": "1c9cdb15142f458731745fe11189ab3", 
            "valid_username": True, 
            "lights": 3
        }, 
        "00178811f9c2": {
            "ip": "130.237.228.161:80", 
            "username": "24f99ac4b92c8af22ea52ec3d6c3e37", 
            "valid_username": True, 
            "lights": 3
        }
    }
}

GRID = {
    "width": 3,
    "height": 3,
    "grid": [
        [None, {"mac":"00178811f9c2","lamp":1}, None],
        [None, None, None],
        [{"mac":"001758182c73","lamp":2}, None, None]
    ]
}

class MainHandler(tornado.web.RequestHandler): 
    def get(self, path):
        print("GET %s:" % path, self.request.body)
        self.set_header("Content-Type", "application/json")
        response = {"state": "success"}
        if path == "/bridges":
            response.update(BRIDGES)
        elif path == "/grid":
            response.update(GRID)
        self.write(tornado.escape.json_encode(response)) 
    def post(self, path):
        # For easy debugging, here you can respond like a lampserver 
        print("POST %s:" % path, self.request.body)
        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode({"state": "success"})) 

def init_http():
    application = tornado.web.Application([
        (r"(.*)", MainHandler) # For debugging
    ])

    try:
        with open(manager.CONFIG_FILE, 'r') as file:
            config = tornado.escape.json_decode(file.read())
            manager.config.update(config)
    except FileNotFoundError:
        print("Config file %s not found, using defaults" % manager.CONFIG_FILE)

    print("Starting dummy lamp server (port %d)" % manager.config['lampport'])
    application.listen(manager.config['lampport'])

if __name__ == "__main__":
    init_http()

    tornado.ioloop.IOLoop.instance().start()
