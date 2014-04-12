import tornado.ioloop
import tornado.web

import time
import traceback

import lightgames
import manager


password = None


class GetException(Exception):
    def __init__(self, msg, response):
        self.msg = msg
        self.response = response

def add_auth_cookie(headers):
    if manager.light_cookie and 'user' in manager.light_cookie:
        headers['Cookie'] = manager.light_cookie['user'].output(attrs=[], header='')
    return headers

def get_data(client, path):
    print("GET %s" % path)
    try: 
        client.request("GET", path, headers=add_auth_cookie({}))
    except ConnectionRefusedError: 
        print("ConnectionRefusedError: [Errno 111] Connection refused")
        raise GetException("<p>ConnectionRefusedError: [Errno 111] Connection refused</p>")

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
        if password == None:
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
        if update_config(manager.config, cfg, 'lampdest') or \
            update_config(manager.config, cfg, 'lampport'):
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
            except GetException as e:
                self.write(e.msg)
                return 
             
            tvars['bridges'] = BridgeConfigHandler.bridges 
            self.render('config_bridges.html', **tvars)
        else: 
            tvars['bridges'] = BridgeConfigHandler.bridges 
            self.render('config_bridges.html', **tvars) 

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.arguments)
        client = manager.connect_lampserver()
        headers = add_auth_cookie({'Content-Type': 'application/json'})

        data = self.request.arguments 
        if 'identify' in data and 'select' in data:
            request = {'alert': 'select'}
            request = tornado.escape.json_encode(request) 
            for mac in data['select']: 
                print("Identify POST:", "/bridges/"+mac.decode('utf-8')+"/lights/all", request) 
                client.request("POST", "/bridges/"+mac.decode('utf-8')+"/lights/all", request, headers)

                response = client.getresponse().read().decode() 
                print('Identify response:', response) 

                response = tornado.escape.json_decode(response) 
                if response['state'] == 'success': 
                    pass
                else: 
                    print('Error when blinking', mac, response) 
                    self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 
            self.redirect('bridges') 

        elif 'add' in data: 
            # Remove unneccesary whitespace and decode to utf-8 
            data['ip'] = data['ip'][0].strip().decode() 
            data['username'] = data['username'][0].strip().decode() 

            if data['ip'] != '': 
                request = {'ip': data['ip']}
                if data['username'] != '': 
                    request['username'] = data['username'] 

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

        elif 'remove' in data and 'select' in data: 
            for mac in data['select']: 
                print('Remove bridge', mac.decode()) 
                client.request("DELETE", "/bridges/"+mac.decode(), {}, headers)

                response = client.getresponse().read().decode() 
                print('Remove response:', response) 

                response = tornado.escape.json_decode(response) 
                if response['state'] == 'success': 
                    del BridgeConfigHandler.bridges[mac.decode()]
                else: 
                    print('Could not remove bridge.')
                    print(response['errorcode'], response['errormessage']) 
                    self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 
            self.redirect('bridges') 

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
                self.write({'state': 'success'}) 
            else: 
                response['errormessage'] = response['errormessage'].capitalize(); 
                self.write(response) 

        elif 'search' in data: 
            print('Search') 
            request = tornado.escape.json_encode({'auto_add': True})
            client.request('POST', '/bridges/search', request, headers) 

            response = client.getresponse().read().decode() 
            print(response) 
            response = tornado.escape.json_decode(response) 
            if response['state'] == 'success': 
                self.redirect("bridges?status=message&msg=%s" % "Server begun searching, refresh bridges (using the button) after 20 s") 
            else: 
                print(response['errorcode'], response['errormessage']) 
                self.redirect("bridges?status=error&msg=%s" % response['errormessage'].capitalize()) 
        else: 
            print('Unknown request. What did you do?') 


class GridConfigHandler(RequestHandler):
    grid = None
    bridges = None
    skipped = None
    changed = False

    def get_lights(self, client):
        if GridConfigHandler.bridges == None:
            response = get_data(client, '/bridges')
            GridConfigHandler.bridges = response['bridges']
        bridges = GridConfigHandler.bridges

        lights = []
        for mac in bridges:
            for light in range(bridges[mac]['lights']):
                lights.append({'mac':mac, 'lamp':light+1})

        return lights

    @use_statusmessage
    @tornado.web.removeslash
    @tornado.web.authenticated
    def get(self, tvars):
        headers = add_auth_cookie({'Content-Type': 'application/json'})

        client = manager.connect_lampserver()
        try:
            if GridConfigHandler.grid == None:
                response = get_data(client, '/grid')
                GridConfigHandler.grid = {
                    k: response[k] for k in ('width', 'height', 'grid')
                }
                GridConfigHandler.skipped = []
            grid = GridConfigHandler.grid

            lights = self.get_lights(client)
        except GetException as e:
            self.write(e.msg)
            return
        ingrid = [cell for row in grid['grid'] for cell in row if cell != None]

        free    = [c for c in lights if c not in ingrid
                    and c not in GridConfigHandler.skipped]
        invalid = [c for c in ingrid if c not in lights]

        tvars['activated'] = ''
        tvars['lamp'] = ''
        if len(free) > 0 and not all([all(row) for row in grid['grid']]):
            # choose and activate one of the free lights
            choosen = free[0]
            tvars['activated'] = tornado.escape.json_encode(choosen)
            tvars['lamp'] = choosen

            request = tornado.escape.json_encode(
                [{'light' : choosen['lamp'],
                  'change': {'on':True, 'sat':0, 'hue':0, 'bri':255}}]
            )

            print(">>> POST:", "/bridges/%s/lights" % choosen['mac'], request)
            manager.client.request("POST",
                "/bridges/%s/lights" % choosen['mac'], request, headers)

            response = manager.client.getresponse().read().decode()
            print('POST response:', response)

        tvars['free'] = free
        tvars['invalid'] = invalid
        tvars['skipped'] = GridConfigHandler.skipped
        tvars['grid'] = GridConfigHandler.grid
        tvars['json_encode'] = tornado.escape.json_encode
        tvars['changed'] = GridConfigHandler.changed
        self.render('config_grid.html', **tvars)

    @tornado.web.authenticated
    def post(self):
        headers = add_auth_cookie({'Content-Type': 'application/json'})

        args = self.request.arguments
        status,msg = ('message','')

        if 'changesize' in args:
            size = self.get_argument('grid_size').split('x')

            if len(size) == 2 and size[0].isdigit() and size[1].isdigit():
                h, w = int(size[0]), int(size[1])

                newgrid = [[None for _ in range(w)] for _ in range(h)]

                GridConfigHandler.grid['grid'] = newgrid
                GridConfigHandler.grid['width'] = w
                GridConfigHandler.grid['height'] = h

                msg = "Grid size changed to %dx%d" % (h,w)
                print(msg)
                GridConfigHandler.changed = True
            else:
                status,msg = ('error','Invalid size')
        elif 'placelamp' in args:
            coords = self.get_argument('coords').split(',')

            if len(coords) == 2 and coords[0].isdigit() and coords[1].isdigit():
                y,x = int(coords[0]), int(coords[1])

                if y >= GridConfigHandler.grid['height'] or \
                    x >= GridConfigHandler.grid['width']:
                    status,msg = ('error','Invalid position')
                else:
                    if GridConfigHandler.grid['grid'][y][x] != None:
                        GridConfigHandler.grid['grid'][y][x] = None
                        print('Lamp removed from %s' % coords)
                        msg = 'Lamp removed from %d,%d' % (y,x)
                        GridConfigHandler.changed = True
                    elif self.get_argument('lamp') == '':
                        status,msg = ('error','No activated lamp')
                    else:
                        try:
                            lamp = tornado.escape.json_decode(
                                self.get_argument('lamp'))
                            GridConfigHandler.grid['grid'][y][x] = lamp
                            print('Lamp %s placed at %s' % (lamp, coords))
                            msg = 'Lamp placed at %d,%d' % (y,x)
                            GridConfigHandler.changed = True
                        except ValueError:
                            status,msg = ('error','Invalid lamp')
            else:
                status,msg = ('error','Invalid position')
        elif 'skip' in args:
            skip_name = self.get_argument('skip_name', 'skip')
            try:
                if skip_name == 'skip':
                        lamp = tornado.escape.json_decode(
                            self.get_argument('lamp'))
                        GridConfigHandler.skipped.append(lamp)
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
            GridConfigHandler.changed = False
        elif 'off' in args:
            manager.config['game_name'] = 'off'
            try:
                manager.load_game()
                msg = 'Game changed to: off'
            except Exception as e:
                msg = 'Loading failed: %s' % e
                status = 'error'
                traceback.print_exc()
        else:
            status,msg = ('error','Unknown request')

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
            if ret == None:
                msg = "Settings saved"
            else:
                status = "error"
                msg = ret

        manager.save_config()

        self.redirect("game?status=%s&msg=%s" % (status, msg))
