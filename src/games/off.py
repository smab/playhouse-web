import lightgames


def create(client):
    print("Turning off lamps")
    return Off(client)


class Off(lightgames.Game):
    """A 'game' used to easily turn off the lights when not needed"""

    template_vars = { 'module_name': 'Off' }

    def reset(self):
        self.send_lamp_all({ "on": False })

