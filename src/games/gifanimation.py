import tornado.escape

from PIL import Image
import time

import lightgames

def create(client):
    print("Creating GIF animation")
    return GifAnimation(client)

class GifAnimation(lightgames.Game):
    config_file = "gifconfig.html"
    template_file = "gifanimation.html"
    template_vars = {
        'module_name': 'GIF Animation',
        'grid_x': 3,
        'grid_y': 3,
        'cell_w': 64,
        'cell_h': 64,
        'color_empty': '#f0f0f0'
    }

    def init(self):
        self.spectators = []


    def on_connect(self, handler):
        self.spectators.append(handler)
        try:
            gif = Image.open("animations/test2.gif")
            (width, height) = gif.size
            i = 0
            for frame in ImageSequence(gif):
                i = i+1
                rgb_im = gif.convert("RGB")
                dur = gif.info['duration']
                buffer = []
                for y in range(0, height):
                    for x in range(0, width):
                        r, g, b = rgb_im.getpixel((x, y))
                        buffer += {'x': x, 'y': y, 'change': {'rgb': (r,g,b)}}
                        for handler in self.spectators:
                            handler.write_message(
                                tornado.escape.json_encode(
                                    {'x':x, 'y':y, 'color':(r,g,b)}
                                )
                            )

                buffer = tornado.escape.json_encode([buffer])
                headers = {'Content-Type': 'application/json'}
                self.client.request("POST", "/lights", buffer, headers)

                # Print response
                print(self.client.getresponse().read().decode())
                time.sleep(dur/1000.0)
        except IOError:
            print("Couldn't open image")

    def on_close(self, handler):
        self.spectators.remove(handler)


class ImageSequence:
    def __init__(self, im):
        self.im = im
    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError # end of sequence

# v Just for testing v
if __name__ == "__main__":
    try:
        gif = Image.open("animations/test2.gif")
        print("The size of the Image is: ")
        print(gif.format, gif.size, gif.mode)
        (width, height) = gif.size
        i = 0
        for frame in ImageSequence(gif):
            i = i+1
            rgb_im = gif.convert("RGB")
            print("========== FRAME", i, "==========")
            print("Frame duration:", gif.info['duration'])
            for y in range(0, height):
                for x in range(0, width):
                    r, g, b = rgb_im.getpixel((x, y))
                    print(x, y, ":", "R", r, "\tG", g, "\tB", b)
    except IOError:
        print("Couldn't open image")
