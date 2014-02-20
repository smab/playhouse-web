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

class ConfigHandler(tornado.web.RequestHandler): 
    client = None 
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
                "lights": 3
            }
        }
    }
    bridges = [
        [1, '001788182e78', '130.237.228.58:80', 'a0e48e11876b8971eb694151aba16ab', True, 3], 
        [2, '001788182c73', '130.237.228.213:80', '1c9cdb15142f458731745fe11189ab3', True, 3],
        [3, '00178811f9c2', '130.237.228.161:80', '24f99ac4b92c8af22ea52ec3d6c3e37', True, 3]
    ]
        
    def get(self):         
        self.render('config.html', bridges=self.bridges) 
        #with open('config.json', 'r') as file: 
        #    cfg = tornado.escape.json_decode(file.read()) 

        #config.update(cfg) 

        #self.client = http.client.HTTPConnection(config['lampdest'], config['lampport'])
        #self.client.request("GET", "/bridges"); 
        #print(client.getresponse().read().decode()) 

    def post(self): 
        pass 





