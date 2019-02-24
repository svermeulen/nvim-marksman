
import traceback

IncludeDebugging = 1

# Thread safe logger
class Log:
    def __init__(self, nvim):
        self._nvim = nvim

    def _escape(self, message):
        return message.replace('\\', '\\\\').replace('"', '\\"')

    def _echom(self, message):
        self._nvim.command(f'echom "vim-marksman: {self._escape(message)}"')

    def _echoerr(self, message):
        self._nvim.command(f'echoerr "vim-marksman: {self._escape(message)}"')

    def queueInfo(self, message):
        self._nvim.async_call(self._echom, message)

    def info(self, message):
        self._echom(message)

    def queueError(self, message):
        self._nvim.async_call(self._echoerr, message)

    def error(self, message):
        self._echoerr(message)

    def _getExceptionMessage(self, e):
        if IncludeDebugging:
            return traceback.format_exc()

        return f'Error when running marksman search: {type(e).__name__}: {e}'

    def queueException(self, e):
        self._nvim.async_call(self._echoerr, self._getExceptionMessage(e))

    def exception(self, e):
        self._echoerr(self._getExceptionMessage(e))

    def queueDebug(self, message):
        if IncludeDebugging:
            self.queueInfo(message)

    def debug(self, message):
        if IncludeDebugging:
            self.info(message)

