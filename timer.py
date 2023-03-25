import time


class Timer:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.start = 0

    def start_timer(self):
        self.start = time.time()

    def check_timer(self):
        if time.time() - self.start > self.interval:
            self.callback()
            self.start_timer()
