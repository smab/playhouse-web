import imp

def load(name, path, client):
    file, pathname, description = imp.find_module(name, path)
    mod = imp.load_module(name, file, pathname, description)

    return mod.create(client)

class Game:
    template_file = "default.html"
    template_vars = {
        'module_name': '<name not set>'
    }

    def __init__(self, client):
        self.client = client

    def init(self):
        pass

    def on_connect(self, handler):
        pass

    def on_message(self, handler, message):
        pass

    def on_close(self, handler):
        pass

    def validate(self, handler, msg): 
        pass 
