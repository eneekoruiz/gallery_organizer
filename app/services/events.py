import queue

class EventStreamManager:
    def __init__(self):
        self.listeners = []
        
    def listen(self):
        q = queue.Queue(maxsize=20)
        self.listeners.append(q)
        return q
        
    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                pass
            except Exception:
                del self.listeners[i]

    def remove(self, q):
        try:
            self.listeners.remove(q)
        except ValueError:
            pass

sse_manager = EventStreamManager()
