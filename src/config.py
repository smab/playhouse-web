import tornado.ioloop
import tornado.web

import http.client
import time 
import traceback

import lightgames
import manager


# An example response.
response = {
    "state": "success",
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
            "lights": 'aoeu'
        }
    }
}


class GetException(Exception):
    def __init__(self, msg):
        self.msg = msg

def get_data(client, path):
    print("GET %s" % path)
    client.request("GET", path);

    json = client.getresponse().read().decode()
    print("GET %s response:" % path, json)
    try:
        response = tornado.escape.json_decode(json)
    except ValueError:
        print("ValueError: Did not get json from server when requesting %s" % path)
        print(json)
        raise GetException("<p>Did not get json from server. Is the IP and port correct? Check the output in console</p>")
    else:
        if response.get('state',None) == 'success':
            return response
        else:
            raise GetException("<p>Unexpected answer from lamp-server.</p>" +
                "<p>" + str(response) + "</p>" +
                "<p>Expected 'state':'success'</p>")

def update_config(cur_cfg, new_cfg, key):
    if key in new_cfg and cur_cfg[key] != new_cfg[key]:
        cur_cfg[key] = new_cfg[key]
        return True
    return False

def use_statusmessage(func):
    def new_func(self, *args, **kwargs):
        vars = {
            'status':  self.get_argument('status', 'message'),
            'message': self.get_argument('msg', '')
        }
        return func(self, vars, *args, **kwargs)
    return new_func

class RequestHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        if 'disable_login' in manager.config and manager.config['disable_login']:
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
    @tornado.web.removeslash
    def get(self):
        self.render('config_login.html', next=self.get_argument("next", "/config"))

    def post(self):
        self.set_current_user("test")
        self.redirect(self.get_argument("next"))

    def set_current_user(self, user):
        if user:
            print("User %s logged in" % user)
            self.set_secure_cookie("user", tornado.escape.json_encode(user), expires_days=None)
        else:
            self.clear_cookie("user")


class SetupConfigHandler(RequestHandler): 
    @use_statusmessage
    @tornado.web.removeslash
    @tornado.web.authenticated 
    def get(self, vars):
        def config(key):
            if key in manager.config:
                return manager.config[key]
            return None

        vars['config'] = config
        self.render("config_setup.html", **vars)

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.body)

        cfg = {}
        for key,val in self.request.arguments.items():
            cfg[key] = self.get_argument(key)

        cfg['lampport'] = int(cfg['lampport'])
        cfg['serverport'] = int(cfg['serverport'])

        status = "message"
        msg = "Setup saved"
        if update_config(manager.config, cfg, 'lampdest') or \
            update_config(manager.config, cfg, 'lampport'):
            manager.client = manager.connect_lampserver()
            manager.fetch_grid_size()
            msg = "Reconnected to lampserver"

        update_config(manager.config, cfg, 'serverport')
        update_config(manager.config, cfg, 'stream_embedcode')

        self.redirect("setup?status=%s&msg=%s" % (status, msg))



class BridgeConfigHandler(RequestHandler):
    bridges = None 
    @tornado.web.removeslash
    @tornado.web.authenticated
    def get(self):
        if BridgeConfigHandler.bridges == None: 
            try:
                client = manager.connect_lampserver()
                response = get_data(client, "/bridges")
                BridgeConfigHandler.bridges = response['bridges']
            except GetException as e:
                self.write(e.msg)
                return

        self.render('config_bridges.html', bridges=BridgeConfigHandler.bridges)

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.arguments)
        client = manager.connect_lampserver()
        headers = {'Content-Type': 'application/json'}

        data = self.request.arguments 
        if 'identify' in data and 'select' in data:
            request = {'alert': 'select'}
            request = tornado.escape.json_encode(request) 
            for mac in data['select']: 
                print("Identify POST:", "/bridges/"+mac.decode('utf-8')+"/lights/all", request) 
                client.request("POST", "/bridges/"+mac.decode('utf-8')+"/lights/all", request, headers)
                time.sleep(1.5) 

                response = client.getresponse().read().decode() 
                print('Identify response:', response) 

                response = tornado.escape.json_decode(response) 
                if response['state'] != 'success': 
                    print('Error when blinking', mac, response) 

        elif 'add' in data: 
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
                else: 
                    print("ERROR!", response) 
            else: 
                print('No IP specified') 

        elif 'remove' in data and 'select' in data: 
            for mac in data['select']: 
                print('Remove bridge', mac.decode()) 
                client.request("DELETE", "/bridges/"+mac.decode(), {}, headers)
                time.sleep(1.5) 

                response = client.getresponse().read().decode() 
                print('Remove response:', response) 

                response = tornado.escape.json_decode(response) 
                if response['state'] == 'success': 
                    del BridgeConfigHandler.bridges[mac.decode()]
                else: 
                    print('Could not remove bridge.')
                    print(response['errorcode'], response['errormessage']) 

        # Set bridges to None, to force it to get them in get() 
        elif 'refresh' in data: 
            BridgeConfigHandler.bridges = None 

        elif 'search' in data: 
            print('Search') 
            client.request('GET', '/bridges/search', {}, headers) 

            response = client.getresponse().read().decode() 
            print(response) 
            response = tornado.escape.json_decode(response) 
            if response['state'] == 'success': 
                time.sleep(20)  
                client.request('GET', '/bridges/search/result', {}, headers) 

                response = client.getresponse().read().decode() 
                response = tornado.escape.json_decode(response) 
                print('BridgeConfig search response', response) 
                if response['state'] == 'success': 
                    BridgeConfigHandler.bridges.update(response['bridges']) 
                else: 
                    print(response['errorcode'], response['errormessage']) 
            else: 
                print(response['errorcode'], response['errormessage']) 
        else: 
            print('Unknown request. What did you do?') 
            
        self.redirect("bridges")


class GridConfigHandler(RequestHandler):
    grid = None
    bridges = None
    changed = False

    headers = {'Content-Type': 'application/json'}

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
    def get(self, vars):
        client = manager.connect_lampserver()
        try:
            if GridConfigHandler.grid == None:
                response = get_data(client, '/grid')
                GridConfigHandler.grid = {
                    k: response[k] for k in ('width', 'height', 'grid')
                }
            grid = GridConfigHandler.grid

            lights = self.get_lights(client)
        except GetException as e:
            self.write(e.msg)
            return
        ingrid = [cell for row in grid['grid'] for cell in row if cell != None]

        free    = [c for c in lights if c not in ingrid]
        invalid = [c for c in ingrid if c not in lights]

        vars['activated'] = ''
        if len(free) > 0:
            # choose and activate one of the free lights
            choosen = free[0]
            vars['activated'] = tornado.escape.json_encode(choosen)

            request = tornado.escape.json_encode(
                [{'light': choosen['lamp'], 'change':{'on':True,'bri':0}}]
            )

            print(">>> POST:", "/bridges/%s/lights" % choosen['mac'], request)
            manager.client.request("POST",
                "/bridges/%s/lights" % choosen['mac'], request, self.headers)

            response = manager.client.getresponse().read().decode()
            print('POST response:', response)

        vars['free'] = free
        vars['invalid'] = invalid
        vars['grid'] = GridConfigHandler.grid
        vars['json_encode'] = tornado.escape.json_encode
        vars['changed'] = GridConfigHandler.changed
        self.render('config_grid.html', **vars)

    @tornado.web.authenticated
    def post(self):
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
            else:
                status,msg = ('error','Invalid size')
        elif 'placelamp' in args:
            coords = self.get_argument('coords').split(',')

            if len(coords) == 2 and coords[0].isdigit() and coords[1].isdigit():
                y,x = int(coords[0]), int(coords[1])

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
        elif 'save' in args:
            request = tornado.escape.json_encode(
                GridConfigHandler.grid['grid']
            )

            print(">>> POST:", "/grid", request)
            manager.client.request('POST', '/grid', request, self.headers)
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
    def get(self, vars):
        vars.update({
            'config_file': lightgames.Game.config_file,
            'game_name':   manager.config['game_name'],
            'game_list':   lightgames.get_games(manager.config['game_path'])
        })

        vars.update(lightgames.Game.template_vars)  # Game defaults
        if manager.game != None:
            vars.update(manager.game.template_vars)
            vars['config_file'] = manager.game.config_file
        if 'title' not in vars:
            vars['title'] = vars.get('module_name', "Untitled game")

        vars['vars'] = vars;
        self.render('config_game.html', **vars)

    @tornado.web.authenticated
    def post(self):
        backup = manager.config.copy()

        cfg = {}
        for key,val in self.request.arguments.items():
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

        self.redirect("game?status=%s&msg=%s" % (status, msg))
