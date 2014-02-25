import tornado.web 

import http.client 



# Direct copy of defaults from webserver.py
# TODO Maybe move it to a separate file? 
config = {
    'game_name': 'default',
    'game_path': ['src/games'],

    'lampdest': 'localhost',
    'lampport': 4711,

    'serverport': 8080
}

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


class ConfigHandler(tornado.web.RequestHandler): 
    client = None 
    #response = response # To use the example 
    def get(self):  
        self.client = http.client.HTTPConnection(
            config['lampdest'], config['lampport']
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
                self.render('config.html', bridges=self.data) 
            else: 
                self.write("<p>Unexpected answer from lamp-server.</p>")
                self.write("<p>" + str(self.response) + "</p>") 
                self.write("<p>Expected 'state':'success'</p>") 

    def post(self): 
        print('POST', self.request.body) 
        self.render('config.html', bridges=self.data) 

        # TODO: Stuff here. Do the changes the user requests 





