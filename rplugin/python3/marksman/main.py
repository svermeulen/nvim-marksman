
import pynvim
import os
from marksman.util.FileExplorer import FileExplorer
from marksman.util.LockableValue import LockableValue
from marksman.util.ReadWriteLockableValue import ReadWriteLockableValue
import os.path
from datetime import datetime
import threading
from queue import Queue

class ProjectInfo:
    def __init__(self):
        self.idMap = ReadWriteLockableValue({})
        self.totalCount = LockableValue(0)
        self.isUpdating = LockableValue(True)

@pynvim.plugin
class Marksman(object):
    def __init__(self, nvim):
        self._nvim = nvim
        self._hasInitialized = False

    def _getCanonicalPath(self, path):
        return os.path.abspath(path)

    def _lazyInit(self):
        if self._hasInitialized:
            return

        self._hasInitialized = True
        self._refreshQueue = Queue()
        self._projectMap = ReadWriteLockableValue({})
        self._explorer = FileExplorer(self._getSettings())
        self._printQueue = Queue()

        searchThread = threading.Thread(target=self._searchThread)
        # die when the main thread dies
        searchThread.daemon = True
        searchThread.start()

    def _getSettings(self):
        variables = [
            'g:Mm_WildIgnore', 'g:Mm_FollowLinks', 'g:Mm_IndexTimeLimit',
            'g:Mm_ExternalCommand', 'g:Mm_UseVersionControlTool', 'g:Mm_DefaultExternalTool',
            'g:Mm_ShowHidden',
        ]

        evalNames = [
            "exists('g:Mm_ExternalCommand')", "get(g:, 'Mm_RecurseSubmodules', 0)",
            "exists('g:Mm_DefaultExternalTool')", "executable('rg')",
            "executable('pt')", "executable('ag')", "executable('find')",
            "executable('sed')", "&encoding"
        ]

        # Minimize rpcs by just making one call
        return self._nvim.call("marksman#evalAll", variables, evalNames)

    def _debugPrint(self, str):
        str = str.replace('\\', '\\\\').replace('"', '\\"')
        self._nvim.command(f'echom "{str}"')

    def _getFileId(self, name):
        result = name[0].lower()
        for c in name[1:]:
            if c.isupper():
                result += c.lower()
        return result

    def _searchThread(self):
        while True:
            rootPath = self._refreshQueue.get()

            # self._nvim.async_call(self._debugPrint, f'Started processing "{rootPath}"')

            startTime = datetime.now()
            projectInfo = self._getProjectInfo(rootPath)
            projectInfo.totalCount.setValue(0)
            assert projectInfo.isUpdating.getValue()
            projectInfo.idMap.setValue({})

            noIgnore = False  # Do we care about this?

            fileList = self._explorer.getAllFilesUnderDirectory(rootPath, noIgnore)

            for path in fileList:
                name = os.path.basename(path)
                path = self._getCanonicalPath(path.strip())
                id = self._getFileId(name)

                fileList = None
                with projectInfo.idMap.readLock:
                    fileList = projectInfo.idMap.value.get(id)

                if not fileList:
                    fileList = LockableValue([])
                    with projectInfo.idMap.writeLock:
                        projectInfo.idMap.value[id] = fileList

                with fileList.lock:
                    fileList.value.append({'name': name, 'path': path})

                with projectInfo.totalCount.lock:
                    projectInfo.totalCount.value += 1


            lastCommand = None
            if self._explorer._lastCommand:
                lastCommand = self._explorer._lastCommand.replace("'", "''")

            self._nvim.async_call(lambda: self._nvim.command("let g:Mm_LastCmd = '%s'" % lastCommand))

            assert projectInfo.isUpdating.getValue()
            projectInfo.isUpdating.setValue(False)

            elapsed = (datetime.now() - startTime).total_seconds()

            self._nvim.async_call(self._debugPrint, f'vim-marksman: Finished processing directory "{rootPath}", took {elapsed:0.2f} seconds')
            self._refreshQueue.task_done()

    @pynvim.function('MarksmanForceRefresh')
    def forceRefresh(self, args):
        self._lazyInit()

        assert len(args) == 1, 'Wrong number of arguments to MarksmanForceRefresh'

        rootPath = self._getCanonicalPath(args[0])

        info = self._getProjectInfo(rootPath)

        if info.isUpdating.getValue():
            return

        info.isUpdating.setValue(True)
        self._refreshQueue.put(rootPath)

    def _getProjectInfo(self, rootPath):

        with self._projectMap.readLock:
            info = self._projectMap.value.get(rootPath)

        if not info:
            info = ProjectInfo()

            with self._projectMap.writeLock:
                self._projectMap.value[rootPath] = info

            self._refreshQueue.put(rootPath)

        return info

    def _lookupMatchesSlice(self, projectInfo, requestId, offset, maxAmount):

        with projectInfo.idMap.readLock:
            fileList = projectInfo.idMap.value.get(requestId)

        if not fileList:
            return [], 0

        with fileList.lock:
            return fileList.value[offset:offset + maxAmount], len(fileList.value)

    @pynvim.function('MarksmanUpdateSearch', sync=True)
    def updateSearch(self, args):
        self._lazyInit()

        assert len(args) == 4, 'Wrong number of arguments to MarksmanUpdateSearch'

        rootPath = self._getCanonicalPath(args[0])
        requestId = args[1]
        offset = args[2]
        maxAmount = args[3]

        projectInfo = self._getProjectInfo(rootPath)
        matchesSlice, totalMatchesCount = self._lookupMatchesSlice(
            projectInfo, requestId, offset, maxAmount)

        return {
            'totalCount': projectInfo.totalCount.getValue(),
            'isUpdating': projectInfo.isUpdating.getValue(),
            'matchesCount': totalMatchesCount,
            'matches': matchesSlice,
        }


if __name__ == "__main__":
    result = Marksman(None).updateSearch(['C:/Temp/test1', 'f', 0, 5])

    print(result['totalCount'])
