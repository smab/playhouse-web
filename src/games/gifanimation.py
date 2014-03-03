from PIL import Image
import time
import io

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
        'animation_file': 'animations/test2.gif',
    }

    def init(self):
      # self.spectators = []

        self.data = open(self.template_vars['animation_file'], 'rb').read()

    def on_connect(self, handler):
      # self.spectators.append(handler)
        lightgames.Game.on_connect(self, handler)
        try:
            gif = Image.open(io.BytesIO(self.data))
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
                        buffer += [{'x': x, 'y': y, 'change': {'rgb': (r,g,b)}}]
                        lightgames.send_msgs(self.connections, {'x':x, 'y':y, 'color':(r,g,b)})
                      # for handler in self.spectators:
                      #     lightgames.send_msg(handler, {'x':x, 'y':y, 'color':(r,g,b)})

                self.send_lamp_multi(buffer)
                time.sleep(dur/1000.0)

        except IOError:
            print("Couldn't open image")

  # def on_close(self, handler):
  #     self.spectators.remove(handler)

    def set_options(self, config):
        self.template_vars['cell_w'] = max(2,min(500,int(config['cell_w'])))
        self.template_vars['cell_h'] = max(2,min(500,int(config['cell_h'])))

        files = config['files']
        if 'animation_file' in files:
            fileinfo = files['animation_file'][0]
            if fileinfo['content_type'] != 'image/gif':
                return "Incorrect content type: %s" % fileinfo['content_type']

            self.data = fileinfo['body']
            self.template_vars['animation_file'] = fileinfo['filename']


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
