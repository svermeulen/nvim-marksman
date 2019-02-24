
import threading
from marksman.util.ReadWriteLock import ReadWriteLock, ReadLock, WriteLock

class ReadWriteLockableValue:
    def __init__(self, initialValue):
        self.value = initialValue
        readWriteLock = ReadWriteLock()
        self.readLock = ReadLock(readWriteLock)
        self.writeLock = WriteLock(readWriteLock)

    def getValue(self):
        with self.readLock:
            return self.value

    def setValue(self, value):
        with self.writeLock:
            self.value = value
