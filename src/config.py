import tornado.web

import http.client

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


class RequestHandler(tornado.web.RequestHandler):
    def get_current_user(self):
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

# TODO 
class SetupConfigHandler(RequestHandler): 
    @tornado.web.authenticated 
    def get(self): 
        self.render("config_setup.html") 

class BridgeConfigHandler(RequestHandler):
    client = None
    #response = response # To use the example
    @tornado.web.authenticated
    def get(self):
        self.client = http.client.HTTPConnection(
            manager.config['lampdest'], manager.config['lampport']
        )
        self.client.request("GET", "/bridges");

        try:
            self.response = tornado.escape.json_decode(
                self.client.getresponse().read().decode()
            )
        except ValueError:
            print("ValueError: Did not get json from server when requesting /bridges")
            self.write("<p>Did not get json from server. Is the IP and port correct?</p>")
        else:
            if 'state' in self.response and self.response['state'] == 'success':
                self.data = self.response['bridges']
                print("config, GET /bridges:", self.data)
                self.render('config_bridges.html', bridges=self.data)
            else:
                self.write("<p>Unexpected answer from lamp-server.</p>")
                self.write("<p>" + str(self.response) + "</p>")
                self.write("<p>Expected 'state':'success'</p>")

    @tornado.web.authenticated
    def post(self):
        print('POST', self.request.body)

        # TODO: Stuff here. Do the changes the user requests

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
        cfg = {}
        for key,val in self.request.arguments.items():
            cfg[key] = self.get_argument(key)

        print("Config: %s" % cfg)

        cfg['files'] = self.request.files

        load_game = False

        if 'game_name' in cfg and manager.config['game_name']!=cfg['game_name']:
            manager.config['game_name'] = cfg['game_name']
            load_game = True

        status = "message"
        if load_game:
            print("Changing or restarting game")
            manager.load_game()
            msg = "Game changed"
        else:
            ret = manager.game.set_options(cfg)
            if ret == None:
                msg = "Settings saved"
            else:
                status = "error"
                msg = ret

        self.redirect("game?status=%s&msg=%s" % (status, msg))
