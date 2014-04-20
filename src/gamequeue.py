import collections
import traceback

import lightgames

class Queue:
    def __init__(self):
        self.queue = collections.deque()
        self.sessions = dict()

    def on_connect(self, handler):
        lightgames.send_msg(handler, {'queuepos':0})

    def size(self):
        return len(self.queue)

    def on_close(self, handler):
        try:
            for key,val in self.sessions.items():
                if handler == val:
                    self.sessions[key] = None
                    break

            self.refresh()
        except ValueError:
            traceback.print_exc()

    def refresh(self):
        i = 0
        for queuer in self.queue:
            i += 1
            lightgames.send_msg(self.sessions[queuer], {'queuepos':i})

    enqueue_callback = None

    def on_message(self, handler, msg):
        try:
            action = msg['queueaction']
            session = msg['session']

            if self.sessions.get(session) != None and self.sessions.get(session) != handler:
                lightgames.send_msg(self.sessions[session], {'queuepos':0})
            self.sessions[session] = handler

            if action == 0:
                del self.sessions[session]
                self.queue.remove(session)
                self.refresh()
                lightgames.send_msg(handler, {'queuepos':0})

            if action == 1:
                if session in self.queue: # disconnected client rejoins
                    pos = 0
                    # no index function :( find position with loop instead
                    for e in self.queue:
                        pos += 1
                        if session == e:
                            break
                    lightgames.send_msg(handler, {'queuepos':pos})
                else: # new client
                    self.queue.append(session)
                    lightgames.send_msg(handler, {'queuepos':self.size()})
                    if self.enqueue_callback != None:
                        self.enqueue_callback(handler)

        except KeyError:
            traceback.print_exc()

    def get_first(self):
        player = None
        # find first connected client
        while player==None and self.size() > 0:
            session = self.queue.popleft()
            player = self.sessions[session]
            del self.sessions[session]
        if player == None:
            return None

        self.refresh()
        lightgames.send_msg(player, {'queuepos':0})
        return player

    def clear(self):
        for queuer in self.queue:
            lightgames.send_msg(self.sessions[queuer], {'queuepos':0})
        self.queue.clear()
        self.sessions.clear()
