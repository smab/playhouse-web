import tornado.escape
import collections

def send_msg(handler, msg):
    if handler != None:
        handler.write_message(
            tornado.escape.json_encode(msg)
        )

class Queue:
    def __init__(self):
        self.queue = collections.deque()

    def on_connect(self, handler):
        send_msg(handler, {'queuepos':0})

    def size(self):
        return len(self.queue)

    def on_close(self, handler):
        try:
            self.queue.remove(handler)
            self.refresh()
        except ValueError:
            pass

    def refresh(self):
        i = 0
        for queuer in self.queue:
            i += 1
            send_msg(queuer, {'queuepos':i})

    def on_message(self, handler, message):
        msg = tornado.escape.json_decode(message)
        try:
            action = msg['queueaction']
            if action == 0:
                self.queue.remove(handler)
                self.refresh()
                send_msg(handler, {'queuepos':0})
            if action == 1:
                self.queue.append(handler)
                send_msg(handler, {'queuepos':self.size()})
        except KeyError:
            pass

    def get_first(self):
        if self.size() > 0:
            player = self.queue.popleft()
            self.refresh()
            return player
        else:
            return None

    def clear(self):
        self.queue.clear()
