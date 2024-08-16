import threading
from fastapi import FastAPI
from long_func import long_flow

app = FastAPI()

class Runner(threading.Thread):
    """Contains a lock and an event. The main thread waits for the event to
       be set, acquires the lock, and runs the long function (long_func).
       The event will be set only if the lock is unlocked.
    """
    def __init__(self, long_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.long_func = long_func
        self.event = threading.Event()
        self.event.clear()
        self.lock = threading.Lock()
        self.exit_req = False

    def run(self):
        """Waits for the event to be set, acquires the lock, and runs the
           long function (self.long_func). The timeout allows self.exit_req
           to be polled periodically in case the thread needs to exit
        """
        print("starting thread")
        self.exit_req = False
        while self.exit_req == False:
            # check for exit request every 1s
            if self.event.wait(timeout=1):
                self.event.clear()
                # check for lock again to be safe?
                if self.lock.acquire(blocking=False):
                    self.long_func()
                    self.lock.release()

    def request_start(self):
        """Tell the thread to start running if it's not already running"""
        if self.is_running():
            return False
        else:
            self.event.set()
            return True

    def request_exit(self):
        """Set self.exit_req = True. The main loop will exit after the next
           wait timeout or after the next execution of long_func().
           This assumes that the thread never needs to be restarted
        """
        self.exit_req = True

    def is_running(self):
        """If the lock is locked, then the process is running"""
        return self.lock.locked()

flow_runner = Runner(long_flow)

@app.on_event("startup")
def start_thread():
    global flow_runner
    flow_runner.start()

@app.get("/start")
def start_flow():
    global flow_runner
    status = flow_runner.request_start()
    return { "result": status }

@app.get("/status")
def get_status():
    global flow_runner
    status = flow_runner.is_running()
    return { "running": status }


@app.post("/exit")
def exit_flow():
    global flow_runner
    flow_runner.request_exit()

