
import threading

class ReadWriteLock:
    """ A lock object that allows many simultaneous "read locks", but
    only one "write lock." """

    def __init__(self):
        self._readReady = threading.Condition(threading.Lock())
        self._readers = 0

    def acquireRead(self):
        """ Acquire a read lock. Blocks only if a thread has
        acquired the write lock. """
        self._readReady.acquire()
        try:
            self._readers += 1
        finally:
            self._readReady.release()

    def releaseRead(self):
        """ Release a read lock. """
        self._readReady.acquire()
        try:
            self._readers -= 1
            if not self._readers:
                self._readReady.notifyAll()
        finally:
            self._readReady.release()

    def acquireWrite(self):
        """ Acquire a write lock. Blocks until there are no
        acquired read or write locks. """
        self._readReady.acquire()
        while self._readers > 0:
            self._readReady.wait()

    def releaseWrite(self):
        """ Release a write lock. """
        self._readReady.release()

class ReadLock:
    def __init__(self, readWriteLock):
        self._readWriteLock = readWriteLock

    def __enter__(self):
        self._readWriteLock.acquireRead()

    def __exit__(self, type, value, traceback):
        self._readWriteLock.releaseRead()

class WriteLock:
    def __init__(self, readWriteLock):
        self._readWriteLock = readWriteLock

    def __enter__(self):
        self._readWriteLock.acquireWrite()

    def __exit__(self, type, value, traceback):
        self._readWriteLock.releaseWrite()
