
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

    def info(self, message):
        self._nvim.async_call(self._echom, message)

    def error(self, message):
        self._nvim.async_call(self._echoerr, message)

    def exception(self, e):
        if IncludeDebugging:
            errorMessage = traceback.format_exc()
        else:
            errorMessage = f'Error when running marksman search: {type(e).__name__}: {e}'

        self.error(errorMessage)

    def debug(self, message):
        if IncludeDebugging:
            self.info(message)

