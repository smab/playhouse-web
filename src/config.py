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

import traceback

import lightgames
import manager


password = None


class GetException(Exception):
    def __init__(self, msg, response):
        super().__init__()
        self.msg = msg
        self.response = response

class ConfigException(Exception):
    def __init__(self, msg):
        super().__init__()
        self.msg = msg

def add_auth_cookie(headers):
    if manager.light_cookie and 'user' in manager.light_cookie:
        headers['Cookie'] = manager.light_cookie['user'].output(attrs=[], header='')
    return headers

def get_data(client, path):
    print("GET %s" % path)
    try: 
        client.request("GET", path, headers=add_auth_cookie({}))
    except ConnectionRefusedError as e: 
        print("ConnectionRefusedError: [Errno 111] Connection refused")
        raise ConfigException(e)

    json = client.getresponse().read().decode()
    print("GET %s response:" % path, json)
    try:
        response = tornado.escape.json_decode(json)
    except ValueError:
        print("ValueError: Did not get json from server when requesting %s" % path)
        print(json)
        raise GetException("<p>Did not get json from server. Is the IP and port correct? Check the output in console</p>", json)
    else:
        if response.get('state',None) == 'success':
            return response
        else:
            raise GetException("<p>Unexpected answer from lamp-server.</p>" +
                "<p>" + str(response) + "</p>" +
                "<p>Expected 'state':'success'</p>", json)

def update_config(cur_cfg, new_cfg, key):
    if key in new_cfg and cur_cfg[key] != new_cfg[key]:
        cur_cfg[key] = new_cfg[key]
        return True
    return False

def use_statusmessage(func):
    def new_func(self, *args, **kwargs):
        tvars = {
            'status':  self.get_argument('status', 'message'),
            'message': self.get_argument('msg', '')
        }
        return func(self, tvars, *args, **kwargs)
    return new_func

class RequestHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        if password is None:
            return "disabled"

        user_json = self.get_secure_cookie("user")
        if user_json:
            return tornado.escape.json_decode(user_json)
        else:
            return None


class ConfigHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect("/config/setup")


class ConfigLoginHandler(tornado.web.RequestHandler):
    @use_statusmessage
    @tornado.web.removeslash
    def get(self, tvars):
        tvars['next'] = self.get_argument("next", "/config")
        self.render('config_login.html', **tvars)

    def post(self):
        user = self.get_argument("username")
        pwd = self.get_argument("password",None)
        if user == 'admin' and pwd == password:
            self.set_current_user(user)
            self.redirect(self.get_argument("next"))
        else:
            self.set_current_user(None)
            self.redirect("login?next=%s&status=error&msg=%s" % (
                self.get_argument("next"), "Wrong username or password"))

    def set_current_user(self, user):
        if user:
            print("User %s logged in" % user)
            self.set_secure_cookie("user", tornado.escape.json_encode(user),
                expires_days=None)
        else:
            self.clear_cookie("user")


class SetupConfigHandler(RequestHandler): 
    @use_statusmessage
    @tornado.web.removeslash
    @tornado.web.authenticated 
    def get(self, tvars):
        def config(key):
            if key in manager.config:
                return manager.config[key]
            return None

        tvars['config'] = config
        tvars['connection_status'] = manager.client_status
        self.render("config_setup.html", **tvars)

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.body)

        cfg = {}
        for key in self.request.arguments.keys():
            cfg[key] = self.get_argument(key)

        cfg['lampport'] = int(cfg['lampport'])
        cfg['serverport'] = int(cfg['serverport'])
        cfg['configport'] = int(cfg['configport'])

        status = "message"
        msg = "Setup saved"
        if any([update_config(manager.config, cfg, x) for x in ['lampdest', 'lampport']]):
            manager.client = manager.connect_lampserver()
            try:
                manager.fetch_grid_size()
                manager.client_status = "connected"
                msg = "Connected to lampserver"
            except:
                traceback.print_exc()
                manager.client_status = "error"
                status = "error"
                msg = "Failed to connect to lampserver"

        if update_config(manager.config, cfg, 'serverport'):
            msg = 'Web server port change requires a restart'
        if update_config(manager.config, cfg, 'configport'):
            msg = 'Web server port change requires a restart'

        if manager.config['serverport'] == manager.config['configport']:
            msg = 'Warning: Game server port and config server port are the same'
            status = 'error'


        update_config(manager.config, cfg, 'stream_embedcode')

        if any([update_config(manager.config['idle'], cfg, x)
                for x in ['animation_directory', 'cycle_interval',
                          'transition_time', 'color_off']]):
            msg = 'Idle animation changed, requires reloading the game'

        manager.save_config()

        self.redirect("setup?status=%s&msg=%s" % (status, msg))



class BridgeConfigHandler(RequestHandler):
    bridges = {} 
    @use_statusmessage 
    @tornado.web.removeslash
    @tornado.web.authenticated
    def get(self, tvars):
        if BridgeConfigHandler.bridges == {}: 
            try:
                client = manager.connect_lampserver()
                response = get_data(client, "/bridges")
                BridgeConfigHandler.bridges = response['bridges']
            except ConfigException as e:
                tvars['status']  = "error"
                tvars['message'] = e.msg
            except GetException as e:
                self.write(e.msg)
                return 
        tvars['bridges'] = BridgeConfigHandler.bridges 
        self.render('config_bridges.html', **tvars) 

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.arguments)
        client = manager.connect_lampserver()
        headers = add_auth_cookie({'Content-Type': 'application/json'})

        data = self.request.arguments 
        if 'identify' in data: 
            if not 'select' in data:
                self.redirect("bridges?status=message&msg=%s" % "You need to select a bridge.")  
            request = {'alert': 'select'}
            request = tornado.escape.json_encode(request) 
            for mac in data['select']: 
                print("Identify POST:", "/bridges/"+mac.decode('utf-8')+"/lights/all", request) 
                client.request("POST", "/bridges/"+mac.decode('utf-8')+"/lights/all", request, headers)

                response = client.getresponse().read().decode() 
                print('Identify response:', response) 

                response = tornado.escape.json_decode(response) 
                if not response['state'] == 'success': 
                    print('Error when blinking', mac, response) 
                    break 
            else: 
                self.redirect('bridges') 
            self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize())      

        elif 'add' in data: 
            # Remove unneccesary whitespace and decode to utf-8 
            data['ip'] = data['ip'][0].strip().decode() 

            if data['ip'] != '': 
                request = {'ip': data['ip']}

                print('Add bridge:', request)
                json = tornado.escape.json_encode(request) 
                client.request("POST", "/bridges/add", json, headers) 

                response = client.getresponse().read().decode() 
                response = tornado.escape.json_decode(response)
                if response['state'] == 'success': 
                    BridgeConfigHandler.bridges.update(response['bridges']) 
                    print('Added bridge:', response['bridges']) 
                    self.redirect('bridges') 
                else: 
                    print("ERROR!", response) 
                    self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 
            else: 
                print('No IP specified') 
                self.redirect('bridges') 

        elif 'remove' in data: 
            if not 'select' in data:
                self.redirect("bridges?status=message&msg=%s" % "You need to select a bridge.")  
            for mac in data['select']: 
                print('Remove bridge', mac.decode()) 
                client.request("DELETE", "/bridges/"+mac.decode(), {}, headers)

                response = client.getresponse().read().decode() 
                print('Remove response:', response) 

                response = tornado.escape.json_decode(response) 
                if response['state'] == 'success': 
                    del BridgeConfigHandler.bridges[mac.decode()]
                    self.redirect("bridges") 
                else: 
                    print('Could not remove bridge.')
                    print(response['errorcode'], response['errormessage']) 
                    self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 

        # Set bridges to None, to force it to get them in get() 
        elif 'refresh' in data: 
            BridgeConfigHandler.bridges = {} 
            self.redirect('bridges') 

        elif 'newUsername' in data and 'mac' in data: 
            mac = data['mac'][0].decode() 
            print("New username to", mac)

            client.request(
                "POST", 
                "/bridges/" + mac + "/adduser", 
                tornado.escape.json_encode({}),
                headers
            ) 
            response = client.getresponse().read().decode() 
            response = tornado.escape.json_decode(response) 
            print(response) 
            if response['state'] == 'success': 
                BridgeConfigHandler.bridges[mac]['username'] = response['username'] 
                BridgeConfigHandler.bridges[mac]['valid_username'] = response['valid_username'] 
                if not response['valid_username']: 
                    BridgeConfigHandler.bridges[mac]['lights'] = -1 
                #self.write({'state': 'success'}) 
                #self.redirect('bridges') 
            else: 
                print(response['errorcode'], response['errormessage']) 
                #self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 
            self.write(response) 

        elif 'search' in data: 
            print('Search') 
            request = tornado.escape.json_encode({'auto_add': True})
            client.request('POST', '/bridges/search', request, headers) 

            response = client.getresponse().read().decode() 
            print(response) 
            response = tornado.escape.json_decode(response) 
            if response['state'] == 'success': 
                self.redirect("bridges?status=message&msg=%s" % "Server begun searching, refresh bridges (using the button) after 20 s.") 
            else: 
                print(response['errorcode'], response['errormessage']) 
                self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 
        else: 
            print('Unknown request. What did you do?') 
            self.redirect("bridges?status=message&msg=%s" % "Unknown request.") 


class GridConfigHandler(RequestHandler):
    grid = None
    bridges = None
    skipped = None
    activated = None
    changed = False

    def get_lights(self, client):
        if GridConfigHandler.bridges is None:
            response = get_data(client, '/bridges')
            GridConfigHandler.bridges = response['bridges']
        bridges = GridConfigHandler.bridges

        lights = []
        for mac in bridges:
            for light in range(bridges[mac]['lights']):
                lights.append({'mac':mac, 'lamp':light+1})

        return lights

    def sendRequest(self, light, change):
        headers = add_auth_cookie({'Content-Type': 'application/json'})
        request = tornado.escape.json_encode(
            [{'light' : light['lamp'],
              'change': change}]
        )

        print(">>> POST:", "/bridges/%s/lights" % light['mac'], request)
        manager.client.request("POST",
            "/bridges/%s/lights" % light['mac'], request, headers)

        response = manager.client.getresponse().read().decode()
        print('POST response:', response)

    @use_statusmessage
    @tornado.web.removeslash
    @tornado.web.authenticated
    def get(self, tvars):
        client = manager.connect_lampserver()
        tvars['activated'] = ''
        tvars['lamp'] = ''
        tvars['json_encode'] = tornado.escape.json_encode
        tvars['changed'] = GridConfigHandler.changed
        try:
            if GridConfigHandler.grid is None:
                response = get_data(client, '/grid')
                GridConfigHandler.grid = {
                    k: response[k] for k in ('width', 'height', 'grid')
                }
                GridConfigHandler.skipped = []
            grid = GridConfigHandler.grid

            lights = self.get_lights(client)
        except ConfigException as e:
            tvars['status']  = "error"
            tvars['message'] = e.msg
            tvars['skipped'] = []
            tvars['grid'] = { 'width':0, 'height':0, 'grid':[] }
            self.render('config_grid.html', **tvars)
            return
        except GetException as e:
            self.write(e.msg)
            return
        ingrid = [cell for row in grid['grid'] for cell in row if cell != None]

        free    = [c for c in lights if c not in ingrid
                    and c not in GridConfigHandler.skipped]
        invalid = [c for c in ingrid if c not in lights]

        if len(free) > 0 and not all([all(row) for row in grid['grid']]):
            if GridConfigHandler.activated is None:
                # choose and activate one of the free lights
                GridConfigHandler.activated = free[0]
            choosen = GridConfigHandler.activated
            tvars['activated'] = tornado.escape.json_encode(choosen)
            tvars['lamp'] = choosen

            # set color to white
            self.sendRequest(choosen,
                {'on':True, 'sat':0, 'hue':0, 'bri':255})

        tvars['free'] = free
        tvars['invalid'] = invalid
        tvars['skipped'] = GridConfigHandler.skipped
        tvars['grid'] = GridConfigHandler.grid
        self.render('config_grid.html', **tvars)

    @tornado.web.authenticated
    def post(self):
        headers = add_auth_cookie({'Content-Type': 'application/json'})

        args = self.request.arguments
        status,msg = ('message','')

        load_game = None

        if 'changesize' in args:
            if GridConfigHandler.grid is not None:
                size = self.get_argument('grid_size').split('x')

                if len(size) == 2 and size[0].isdigit() and size[1].isdigit():
                    w, h = int(size[0]), int(size[1])

                    newgrid = [[None for _ in range(w)] for _ in range(h)]

                    GridConfigHandler.grid['grid'] = newgrid
                    GridConfigHandler.grid['width'] = w
                    GridConfigHandler.grid['height'] = h

                    msg = "Grid size changed to %dx%d" % (w,h)
                    print(msg)
                    GridConfigHandler.changed = True
                else:
                    status,msg = ('error','Invalid size')
        elif 'clear' in args:
            if GridConfigHandler.grid is not None:
                w = GridConfigHandler.grid['width']
                h = GridConfigHandler.grid['height']

                newgrid = [[None for _ in range(w)] for _ in range(h)]

                GridConfigHandler.grid['grid'] = newgrid

                msg = "Grid cleared"
                GridConfigHandler.activated = None
                GridConfigHandler.changed = True
        elif 'placelamp' in args:
            coords = self.get_argument('coords').split(',')

            if GridConfigHandler.grid is not None and \
                len(coords) == 2 and coords[0].isdigit() and coords[1].isdigit():
                x,y = int(coords[0]), int(coords[1])

                if y >= GridConfigHandler.grid['height'] or \
                    x >= GridConfigHandler.grid['width']:
                    status,msg = ('error','Invalid position')
                else:
                    if GridConfigHandler.grid['grid'][y][x] != None:
                        lamp = GridConfigHandler.grid['grid'][y][x]
                        GridConfigHandler.grid['grid'][y][x] = None

                        # set color to red
                        self.sendRequest(lamp,
                            {'on':True, 'sat':255, 'hue':0, 'bri':255})

                        print('Lamp removed from %s' % coords)
                        msg = 'Lamp removed from %d,%d' % (x,y)
                        GridConfigHandler.changed = True
                    elif self.get_argument('lamp') == '':
                        status,msg = ('error','No activated lamp')
                    else:
                        GridConfigHandler.activated = None
                        try:
                            lamp = tornado.escape.json_decode(
                                self.get_argument('lamp'))
                            GridConfigHandler.grid['grid'][y][x] = lamp

                            # set color to blue
                            self.sendRequest(lamp,
                                {'on':True, 'sat':255, 'hue':45000, 'bri':255})

                            print('Lamp %s placed at %s' % (lamp, coords))
                            msg = 'Lamp placed at %d,%d' % (x,y)
                            GridConfigHandler.changed = True
                        except ValueError:
                            status,msg = ('error','Invalid lamp')
            else:
                status,msg = ('error','Invalid position')
        elif 'skip' in args:
            skip_name = self.get_argument('skip_name', 'skip')
            try:
                if skip_name == 'skip':
                    GridConfigHandler.activated = None
                    lamp = tornado.escape.json_decode(
                        self.get_argument('lamp'))
                    GridConfigHandler.skipped.append(lamp)
                    self.sendRequest(lamp, {'on':False})  # turn off
                    msg = 'Skipped lamp %s%%23%s' % (lamp['mac'], lamp['lamp'])
                else:
                    skip_data = skip_name.split('#')
                    skip_lamp = { 'mac': skip_data[0], 'lamp':int(skip_data[1]) }

                    GridConfigHandler.skipped.remove(skip_lamp)
                    msg = 'Unkipped lamp %s%%23%s' % (skip_lamp['mac'], skip_lamp['lamp'])
            except ValueError:
                status,msg = ('error','Invalid lamp')
        elif 'save' in args:
            request = tornado.escape.json_encode(
                GridConfigHandler.grid['grid']
            )

            print(">>> POST:", "/grid", request)
            manager.client.request('POST', '/grid', request, headers)
            response = manager.client.getresponse().read().decode()
            response = tornado.escape.json_decode(response)
            print('POST response:', response)

            if response['state'] == 'success':
                msg = 'Grid saved'
                manager.grid['width'] = GridConfigHandler.grid['width']
                manager.grid['height'] = GridConfigHandler.grid['height']
                GridConfigHandler.changed = False
            else:
                status,msg = ('error','Saving failed!')
        elif 'refresh' in args:
            GridConfigHandler.grid = None
            GridConfigHandler.bridges = None
            GridConfigHandler.activated = None
            GridConfigHandler.changed = False
        elif 'off' in args:
            load_game = 'off'
        elif 'test' in args:
            load_game = 'diagnostics'
        else:
            status,msg = ('error','Unknown request')

        if load_game:
            manager.config['game_name'] = load_game
            try:
                manager.load_game()
                msg = 'Game changed to: %s' % load_game
            except Exception as e:
                msg = 'Loading failed: %s' % e
                status = 'error'
                traceback.print_exc()

        self.redirect('grid?status=%s&msg=%s' % (status,msg))


class GameConfigHandler(RequestHandler):
    @use_statusmessage
    @tornado.web.removeslash
    @tornado.web.authenticated
    def get(self, tvars):
        tvars.update({
            'config_file': lightgames.Game.config_file,
            'game_name':   manager.config['game_name'],
            'game_list':   lightgames.get_games(manager.config['game_path'])
        })

        tvars.update(lightgames.Game.template_vars)  # Game defaults
        if manager.game != None:
            tvars.update(manager.game.template_vars)
            tvars['config_file'] = manager.game.config_file
        if 'title' not in tvars:
            tvars['title'] = tvars.get('module_name', "Untitled game")

        tvars['vars'] = tvars
        self.render('config_game.html', **tvars)

    @tornado.web.authenticated
    def post(self):
        backup = manager.config.copy()

        cfg = {}
        for key in self.request.arguments.keys():
            cfg[key] = self.get_argument(key)

        print("Config: %s" % cfg)

        cfg['files'] = self.request.files

        load_game = False

        update_config(manager.config, cfg, 'game_name')
        if 'game_name' in cfg:
            load_game = True

        status = "message"
        if load_game:
            print("Changing or restarting game")
            try:
                manager.client = manager.connect_lampserver()
                manager.load_game()
                msg = "Game changed"
                if backup['game_name'] == manager.config['game_name']:
                    msg = "Game restarted"
            except Exception as e:
                manager.config = backup
                msg = "Loading failed: %s" % e
                status = "error"
                traceback.print_exc()
        else:
            ret = manager.game.set_options(cfg)
            if ret is None:
                msg = "Settings saved"
            else:
                status = "error"
                msg = ret

        manager.save_config()

        self.redirect("game?status=%s&msg=%s" % (status, msg))
