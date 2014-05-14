import collections
import traceback

import lightgames

class Queue:
    def __init__(self):
        self.queue = collections.deque()
        self.sessions = dict()
        self.players = [] # player sessions

        self.enqueue_callback = None
        self.addplayer_callback = None
        self.removeplayer_callback = None


    # Event handlers
    def on_connect(self, handler):
        lightgames.send_msg(handler, {'queuepos':0})

    def on_close(self, handler):
        try:
            for key,val in self.sessions.items():
                if handler == val:
                    if key in self.players:
                        self.remove_player(self.players.index(key))
                    else:
                        self.sessions[key] = None
                    break

            self.refresh()
        except ValueError:
            traceback.print_exc()

    def on_message(self, handler, msg):
        try:
            action = msg['queueaction']
            session = msg['session']

            if self.sessions.get(session) != None and self.sessions.get(session) != handler:
                lightgames.send_msg(self.sessions[session], {'queuepos':0,'state':'spectating'})
            self.sessions[session] = handler

            if action == 0:
                if session in self.players:
                    self.remove_player(self.index(session))
                else:
                    del self.sessions[session]
                    self.queue.remove(session)
                self.refresh()
                lightgames.send_msg(handler, {'queuepos':0})

            if action == 1:
                if session in self.queue: # disconnected client rejoins
                    pos = self.index(session)
                    if session in self.players: # player rejoins
                        if self.addplayer_callback != None:
                            self.addplayer_callback(pos)
                    else:
                        lightgames.send_msg(handler, {'queuepos':pos+1})
                else: # new client
                    self.queue.append(session)
                    lightgames.send_msg(handler, {'queuepos':self.size()})
                    if self.enqueue_callback != None:
                        self.enqueue_callback(handler)

        except KeyError:
            traceback.print_exc()


    # Player methods
    def try_get_new_players(self):
        pos = 0
        for idx in range(len(self.players)):
            # find an active queuer that isn't a player and set as player
            while self.players[idx] is None and pos < self.size():
                session = self.queue[pos]

                # check if active
                if self.sessions[session] is None:
                    # remove disconnected client
                    self.queue.remove(session)
                    del self.sessions[session]
                    continue

                # check if not playing
                if session not in self.players:
                    self.players[idx] = session
                    if self.addplayer_callback is not None:
                        self.addplayer_callback(idx)
                pos += 1

        self.refresh()

    def set_num_players(self, num):
        self.players = [None for _ in range(num)]

    def remove_all_players(self):
        for idx in range(len(self.players)):
            self.remove_player(idx)

    def remove_player(self, idx):
        session = self.players[idx]
        if session is not None:
            del self.sessions[session]
            self.queue.remove(session)
            self.players[idx] = None
            if self.removeplayer_callback is not None:
                self.removeplayer_callback(idx)

    def get_player_handlers(self):
        return [ self.sessions.get(session) for session in self.players ]


    # Queue methods
    def refresh(self):
        i = 0
        for queuer in self.queue:
            i += 1
            if queuer not in self.players:
                lightgames.send_msg(self.sessions[queuer], {'queuepos':i})

    def index(self, session):
        pos = 0
        # no index function :( find position with loop instead
        for e in self.queue:
            if session == e:
                break
            pos += 1
        return pos

    def clear(self):
        for queuer in self.queue:
            lightgames.send_msg(self.sessions[queuer], {'queuepos':0})
        self.queue.clear()
        self.sessions.clear()
        self.players = [ None for _ in self.players ]

    def size(self):
        return len(self.queue)
