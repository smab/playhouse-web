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
        self.queue.append(handler)
        send_msg(handler, {'queue':self.size()})

    def size(self):
        return len(self.queue)

    def on_close(self, handler):
        self.queue.remove(handler)
        self.refresh()

    def refresh(self):
        i = 0
        for queuer in self.queue:
            i += 1
            send_msg(queuer, {'queue':i})

    def on_message(self, handler, message):
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
