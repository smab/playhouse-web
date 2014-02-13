import tornado.escape
import collections

queue = collections.deque()

def send_msg(handler, msg):
    if handler != None:
        handler.write_message(
            tornado.escape.json_encode(msg)
        )

class Queue:
    def on_connect(self, handler):
        queue.append(handler)
        send_msg(handler, {'message':'Your place in queue: %d' % self.size()})

    def size(self):
        return len(queue)

    def on_close(self, handler):
        queue.remove(handler)
        self.refresh()

    def refresh(self):
        i = 0
        for queuer in queue:
            i += 1
            send_msg(queuer, {'message':'Your place in queue: %d' % i})

    def get_first(self):
        if self.size() > 0:
            return queue.popleft()
        else:
            return None
