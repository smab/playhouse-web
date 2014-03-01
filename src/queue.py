import collections

import lightgames

class Queue:
    def __init__(self):
        self.queue = collections.deque()

    def on_connect(self, handler):
        lightgames.send_msg(handler, {'queuepos':0})

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
            lightgames.send_msg(queuer, {'queuepos':i})

    def on_message(self, handler, msg):
        try:
            action = msg['queueaction']
            if action == 0:
                self.queue.remove(handler)
                self.refresh()
                lightgames.send_msg(handler, {'queuepos':0})
            if action == 1:
                self.queue.append(handler)
                lightgames.send_msg(handler, {'queuepos':self.size()})
        except KeyError:
            pass

    def get_first(self):
        if self.size() > 0:
            player = self.queue.popleft()
            self.refresh()
            lightgames.send_msg(player, {'queuepos':0})
            return player
        else:
            return None

    def clear(self):
        for queuer in self.queue:
            lightgames.send_msg(queuer, {'queuepos':0})
        self.queue.clear()
