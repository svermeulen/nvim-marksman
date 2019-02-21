
import pynvim
import os
from marksman.util.fileExplorer import FileExplorer
import os.path
import time
import hashlib
from datetime import datetime


@pynvim.plugin
class Marksman(object):
    def __init__(self, nvim):
        self._nvim = nvim
        self._isRunning = False
        self._explorer = FileExplorer(nvim)

    def _getId(self, word):
        result = word[0].lower()
        for c in word[1:]:
            if c.isupper():
                result += c.lower()
        return result

    def _getCacheFilePath(self, rootPath):
        cacheDir = os.path.join(
            self._nvim.eval("g:Mm_CacheDirectory"), '.MmCache')

        if not os.path.exists(cacheDir):
            os.makedirs(cacheDir)

        hash = int(hashlib.sha256(rootPath.encode('utf-8')).hexdigest(), 16) % 10**8
        return os.path.join(cacheDir, f'{hash}.txt')

    def _debugPrint(self, str):
        self._nvim.command(f'echom "{str}"')

    def _addToMemoryCache(self, rootPath, path):
        name = os.path.basename(path)
        path = self._nvim.call("marksman#getCanonicalPath", path)
        id = self._getId(name)
        self._nvim.command(
            f'call marksman#addFileMark("{rootPath}",'
            + f'"{id}", {{ "name": "{name}", "path": "{path}" }})')

    def _tryUpdateMemoryCacheFromFileCache(self, rootPath):
        cacheFilePath = self._getCacheFilePath(rootPath)

        if not os.path.exists(cacheFilePath):
            return False

        startTime = datetime.now()
        with open(cacheFilePath, 'r', errors='ignore') as cacheFile:
            count = 0
            for line in cacheFile.readlines():
                path = line.strip()
                self._addToMemoryCache(rootPath, path)
                count += 1
                if count % 100 == 0:
                    # Sleep so that the count display updates
                    time.sleep(0.001)

        self._debugPrint("Took %s seconds for cache update" % (datetime.now() - startTime).total_seconds())
        return True

    def _runForDirectory(self, rootPath, forceUpdateCache):

        cacheEnabled = self._nvim.eval("g:Mm_UseCache")

        if cacheEnabled and not forceUpdateCache:
            if self._tryUpdateMemoryCacheFromFileCache(rootPath):
                return

        cacheFile = None

        if cacheEnabled:
            cacheFile = open(
                self._getCacheFilePath(rootPath), 'w', errors='ignore')

        startTime = datetime.now()
        try:
            noIgnore = False  # Do we care about this?
            count = 0
            for path in self._explorer.getAllFilesUnderDirectory(rootPath, noIgnore):
                path = os.path.abspath(path.strip())
                self._addToMemoryCache(rootPath, path)
                if cacheFile:
                    cacheFile.write(path + '\n')
                count += 1

                if count % 100 == 0:
                    # Sleep so that the count display updates
                    time.sleep(0.001)
        finally:
            if cacheFile:
                cacheFile.close()

        self._debugPrint("Took %s seconds for full update" % (datetime.now() - startTime).total_seconds())

    def _markInProgress(self, rootPath, inProgress):
        self._nvim.call('marksman#markProjectInProgress', rootPath, inProgress)

    @pynvim.function('MarksmanUpdateCache')
    def run(self, args):
        assert not self._isRunning, 'Already running'
        assert len(args) == 2, 'Expected one argument to MarksmanUpdateCache'

        rootPath = args[0]
        updateCache = args[1]

        self._isRunning = True
        self._markInProgress(rootPath, True)

        try:
            self._runForDirectory(rootPath, updateCache)
        finally:
            self._isRunning = False
            self._markInProgress(rootPath, False)
