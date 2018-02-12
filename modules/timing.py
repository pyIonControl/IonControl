import time


class timing:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        self.start = time.clock()

    def __exit__(self, type, value, traceback):
        duration = time.clock() - self.start
        print("Execution time {}: {}".format(self.message, duration))
