import os
import sys
import shlex
import signal
import threading
import subprocess
import locale

if sys.version_info >= (3, 0):
    import queue as Queue
else:
    import Queue


def lfBytes2Str(bytes, encoding=None):
    try:
        if encoding:
            return bytes.decode(encoding)
        else:
            if locale.getdefaultlocale()[1] is None:
                return bytes.decode()
            else:
                return bytes.decode(locale.getdefaultlocale()[1])
    except ValueError:
        return bytes.decode(errors="ignore")
    except UnicodeDecodeError:
        return bytes.decode(errors="ignore")


class AsyncCommandExecutor(object):
    """
    A class to implement executing a command in subprocess, then
    read the output asynchronously.
    """
    def __init__(self):
        self._outQueue = Queue.Queue()
        self._errQueue = Queue.Queue()
        self._process = None
        self._finished = False

    def _readerThread(self, fd, queue, is_out):
        try:
            for line in iter(fd.readline, b""):
                queue.put(line)
        except ValueError:
            pass
        finally:
            queue.put(None)
            if is_out:
                self._finished = True

    def execute(self, cmd, encoding=None, cleanup=None):
        if os.name == 'nt':
            self._process = subprocess.Popen(cmd, bufsize=-1,
                                             stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             shell=True,
                                             universal_newlines=False)
        else:
            self._process = subprocess.Popen(cmd, bufsize=-1,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             preexec_fn=os.setsid,
                                             shell=True,
                                             universal_newlines=False)

        self._finished = False

        stdout_thread = threading.Thread(target=self._readerThread,
                                         args=(self._process.stdout, self._outQueue, True))
        stdout_thread.daemon = True
        stdout_thread.start()

        stderr_thread = threading.Thread(target=self._readerThread,
                                         args=(self._process.stderr, self._errQueue, False))
        stderr_thread.daemon = True
        stderr_thread.start()

        stdout_thread.join(0.01)

        result = AsyncCommandExecutor.Result(self._outQueue, self._errQueue, encoding, cleanup, self._process)

        return result

    def killProcess(self):
        # Popen.poll always returns None, bug?
        # if self._process and not self._process.poll():
        if self._process and not self._finished:
            if os.name == 'nt':
                subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=self._process.pid), shell=True)
            else:
                try:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                except OSError:
                    pass

            self._process = None

    class Result(object):
        def __init__(self, outQueue, errQueue, encoding, cleanup, process):
            self._outQueue = outQueue
            self._errQueue = errQueue
            self._encoding = encoding
            self._cleanup = cleanup
            self._process = process

        def __iter__(self):
            try:
                if self._encoding:
                    while True:
                        line = self._outQueue.get()
                        if line is None:
                            break
                        yield lfBytes2Str(line.rstrip(b"\r\n"), self._encoding)
                else:
                    while True:
                        line = self._outQueue.get()
                        if line is None:
                            break
                        yield lfBytes2Str(line.rstrip(b"\r\n"))

                err = b"".join(iter(self._errQueue.get, None))
                if err:
                    raise Exception(lfBytes2Str(err, self._encoding))
            finally:
                try:
                    if self._process:
                        self._process.stdout.close()
                except IOError:
                    pass

                if self._cleanup:
                    self._cleanup()


if __name__ == "__main__":
    executor = AsyncCommandExecutor()
    # out = executor.execute("D:/Utils/ctags58/ctags.exe -f- -R")
    os.chdir("D:/Projects/neovim")
    out = executor.execute("git ls-files && git ls-files --others")
    print("stdout begin: ============================================")
    for i in out:
        print(repr(i))
    print("stdout end: ==============================================")
