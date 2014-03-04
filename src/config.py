import tornado.ioloop
import tornado.web

import http.client
import time 

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


def update_config(cur_cfg, new_cfg, key):
    if key in new_cfg and cur_cfg[key] != new_cfg[key]:
        cur_cfg[key] = new_cfg[key]
        return True
    return False


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
        self.redirect("config/setup")


class ConfigLoginHandler(tornado.web.RequestHandler):
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
    @tornado.web.authenticated 
    def get(self): 
        def config(key):
            if key in manager.config:
                return manager.config[key]
            return None

        template_vars = {
            'config':  config,
            'status':  self.get_argument("status", ""),
            'message': self.get_argument("msg", "")
        }
        self.render("config_setup.html", **template_vars)

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
            manager.connect_lampserver()
            msg = "Reconnected to lampserver"

        update_config(manager.config, cfg, 'serverport')
        update_config(manager.config, cfg, 'stream_embedcode')

        self.redirect("setup?status=%s&msg=%s" % (status, msg))



class BridgeConfigHandler(RequestHandler):
    bridges = None 
    @tornado.web.authenticated
    def get(self):
        if BridgeConfigHandler.bridges == None: 
            client = http.client.HTTPConnection(
                manager.config['lampdest'], manager.config['lampport']
            )
            print("BridgeConfig GET /bridges")
            client.request("GET", "/bridges");

            json = client.getresponse().read().decode()
            try:
                response = tornado.escape.json_decode(json)
            except ValueError:
                print("ValueError: Did not get json from server when requesting /bridges")
                print(json) 
                self.write("<p>Did not get json from server. Is the IP and port correct? Check the output in console</p>")
            else:
                if response['state'] == 'success':
                    data = response['bridges']
                    print("BridgeConfig response:", data)
                    BridgeConfigHandler.bridges = data 
                    self.render('config_bridges.html', bridges=data)
                else:
                    self.write("<p>Unexpected answer from lamp-server.</p>")
                    self.write("<p>" + str(response) + "</p>")
                    self.write("<p>Expected 'state':'success'</p>")
        else: 
            self.render('config_bridges.html', bridges=BridgeConfigHandler.bridges) 

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.arguments)
        client = http.client.HTTPConnection(
            manager.config['lampdest'], manager.config['lampport']
        )
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


class GameConfigHandler(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        template_vars = {
            'config_file': manager.game.config_file,
            'game_name':   manager.config['game_name'],
            'game_path':   tornado.escape.json_encode(manager.config['game_path']),
            'game_list':   lightgames.get_games(manager.config['game_path']),
            'status':      self.get_argument("status", ""),
            'message':     self.get_argument("msg", "")
        }

        template_vars.update(lightgames.Game.template_vars)  # Game defaults
        template_vars.update(manager.game.template_vars)
        if 'title' not in template_vars:
            template_vars['title'] = template_vars.get('module_name', "Untitled game")

        template_vars['vars'] = template_vars;
        self.render('config_game.html', **template_vars)

    @tornado.web.authenticated
    def post(self):
        backup = manager.config.copy()

        cfg = {}
        for key,val in self.request.arguments.items():
            cfg[key] = self.get_argument(key)

        if 'game_path' in cfg:
            cfg['game_path'] = tornado.escape.json_decode(cfg['game_path'])

        print("Config: %s" % cfg)

        cfg['files'] = self.request.files

        load_game = False

        if update_config(manager.config, cfg, 'game_name') or \
            update_config(manager.config, cfg, 'game_path'):
            load_game = True

        status = "message"
        if load_game:
            print("Changing or restarting game")
            try:
                manager.load_game()
                msg = "Game changed"
            except Exception as e:
                manager.config = backup
                msg = "Loading failed: %s" % e
                status = "error"
        else:
            ret = manager.game.set_options(cfg)
            if ret == None:
                msg = "Settings saved"
            else:
                status = "error"
                msg = ret

        self.redirect("game?status=%s&msg=%s" % (status, msg))
