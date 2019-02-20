
import pynvim
import os
from marksman.util.fileExplorer import FileExplorer
import os.path
import time


@pynvim.plugin
class Marksman(object):
    def __init__(self, nvim):
        self._nvim = nvim
        self._isRunning = False
        self._explorer = None

    def _getId(self, word):
        result = word[0].lower()
        for c in word[1:]:
            if c.isupper():
                result += c.lower()
        return result

    def _updateVimCache(self, projectRootPath, useCache):
        if not self._explorer:
            # Do this lazily
            self._explorer = FileExplorer(self._nvim)

        count = 0
        for path in self._explorer.lookupFiles(projectRootPath, useCache):
            path = os.path.abspath(path.strip()).replace('\\', '/')
            name = os.path.basename(path)

            self._nvim.command(
                f'call g:MarksmanAddFileMark("{projectRootPath}",'
                + f'"{self._getId(name)}", {{ "name": "{name}", "path": "{path}" }})')
            count += 1

            if count % 100 == 0:
                # Sleep so that the count display updates
                time.sleep(0.001)

    @pynvim.function('MarksmanUpdateCache')
    def run(self, args):
        assert len(args) == 2, 'Expected one argument to MarksmanUpdateCache'

        projectRootPath = args[0]
        useCache = args[1]

        if self._isRunning:
            return

        self._isRunning = True
        self._nvim.command(
            f'let g:marksmanIsUpdating["{projectRootPath}"] = 1')

        try:
            self._updateVimCache(projectRootPath, useCache)
        finally:
            self._isRunning = False
            self._nvim.command(
              f'let g:marksmanIsUpdating["{projectRootPath}"] = 0')
