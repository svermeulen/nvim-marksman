
import pynvim
import os
from marksman.util.fileExplorer import FileExplorer
import os.path


@pynvim.plugin
class Marksman(object):
    def __init__(self, nvim):
        self._nvim = nvim
        self._isRunning = False
        self._explorer = None

    def _getId(self, word):
        result = ''
        for c in word:
            if c.isupper():
                result += c.lower()
        return result

    def _updateCache(self, projectRootPath):
        if not self._explorer:
            # Do this lazily
            self._explorer = FileExplorer(self._nvim)

        for path in self._explorer.lookupFiles(projectRootPath):
            name = os.path.basename(path)
            self._nvim.command(
                f'call g:MarksmanAddMarks("{projectRootPath}",'
                + f'"{self._getId(name)}", {{ "name": "{name}", "path": "{path}" }})')

    @pynvim.function('MarksmanUpdateCache')
    def run(self, args):
        assert len(args) == 1, 'Expected one argument to MarksmanUpdateCache'

        projectRootPath = args[0]

        if self._isRunning:
            return

        self._isRunning = True
        self._nvim.command(
            f'let g:marksmanIsUpdating["{projectRootPath}"] = 1')

        try:
            self._updateCache(projectRootPath)
        finally:
            self._isRunning = False
            self._nvim.command(
              f'let g:marksmanIsUpdating["{projectRootPath}"] = 0')
