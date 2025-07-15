import datetime

# logger class that supports verbose mode
class Logger:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def log(self, tag, message):
        
        if self.verbose:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] [{tag}] {message}")