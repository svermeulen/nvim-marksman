
import threading

class LockableValue:
    def __init__(self, initialValue):
        self.value = initialValue
        self.lock = threading.Lock()

    # Only use this for immutable values
    def getValue(self):
        with self.lock:
            return self.value

    def setValue(self, value):
        with self.lock:
            self.value = value
