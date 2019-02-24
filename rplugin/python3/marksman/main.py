
import pynvim
import os
from marksman.util.FileExplorer import FileExplorer
from marksman.util.LockableValue import LockableValue
from marksman.util.ReadWriteLockableValue import ReadWriteLockableValue
from marksman.util.Log import Log
from datetime import datetime
import threading
from queue import Queue
import traceback

class ProjectInfo:
    def __init__(self):
        self.idMap = ReadWriteLockableValue({})
        self.totalCount = LockableValue(0)
        self.isUpdating = LockableValue(True)

class FileInfo:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.modificationTime = ReadWriteLockableValue(datetime.min)

@pynvim.plugin
class Marksman(object):
    def __init__(self, nvim):
        self._nvim = nvim
        self._hasInitialized = False
        self._log = Log(nvim)

    def _getCanonicalPath(self, path):
        return os.path.abspath(path)

    def _lazyInit(self):
        if self._hasInitialized:
            return

        self._hasInitialized = True
        self._lastOpenTimes = ReadWriteLockableValue({})
        self._refreshQueue = Queue()
        self._projectMap = ReadWriteLockableValue({})
        self._explorer = FileExplorer(self._log, self._getSettings())
        self._printQueue = Queue()

        searchThread = threading.Thread(target=self._searchThread)
        # die when the main thread dies
        searchThread.daemon = True
        searchThread.start()

    def _getSettings(self):
        variables = [
            'g:Mm_WildIgnore', 'g:Mm_FollowLinks', 'g:Mm_ExternalCommand', 'g:Mm_ShowHidden',
            'g:Mm_SearchPreferenceOrder'
        ]

        evalNames = [
            "exists('g:Mm_ExternalCommand')", "get(g:, 'Mm_RecurseSubmodules', 0)",
            "executable('rg')", "executable('pt')", "executable('ag')", "executable('find')",
            "executable('sed')", "&encoding"
        ]

        # Minimize rpcs by just making one call
        return self._nvim.call("marksman#evalAll", variables, evalNames)

    def _getFileId(self, name):
        result = name[0].lower()
        for c in name[1:]:
            if c.isupper():
                result += c.lower()
        return result

    def _searchThreadInternal(self):
        while True:
            rootPath = self._refreshQueue.get()

            # self._log.queueDebug(f'Started processing "{rootPath}"')

            startTime = datetime.now()
            projectInfo = self._getProjectInfo(rootPath)
            projectInfo.totalCount.setValue(0)
            assert projectInfo.isUpdating.getValue()
            projectInfo.idMap.setValue({})

            noIgnore = False  # Do we care about this?

            allFileInfos = []

            for path in self._explorer.getAllFilesUnderDirectory(rootPath, noIgnore):
                name = os.path.basename(path)
                path = self._getCanonicalPath(path.strip())
                id = self._getFileId(name)

                fileList = None
                with projectInfo.idMap.readLock:
                    fileList = projectInfo.idMap.value.get(id)

                if not fileList:
                    fileList = ReadWriteLockableValue([])
                    with projectInfo.idMap.writeLock:
                        projectInfo.idMap.value[id] = fileList

                fileInfo = FileInfo(path, name)
                allFileInfos.append(fileInfo)
                with fileList.writeLock:
                    fileList.value.append(fileInfo)

                with projectInfo.totalCount.lock:
                    projectInfo.totalCount.value += 1

            # Update all the modification times
            for fileInfo in allFileInfos:
                modTime = datetime.fromtimestamp(os.path.getmtime(fileInfo.path))
                with fileInfo.modificationTime.writeLock:
                    fileInfo.modificationTime.value = modTime

            with projectInfo.idMap.readLock:
                fileLists = projectInfo.idMap.value.values()

            for fileList in fileLists:
                with fileList.writeLock:
                    self._sortFileList(fileList.value)

            assert projectInfo.isUpdating.getValue()
            projectInfo.isUpdating.setValue(False)

            elapsed = (datetime.now() - startTime).total_seconds()

            self._log.queueDebug(f'Finished processing directory "{rootPath}", took {elapsed:0.2f} seconds')

            self._refreshQueue.task_done()

    def _searchThread(self):
        try:
            self._searchThreadInternal()
        except Exception as e:
            self._log.queueException(e)

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

        with fileList.readLock:
            return fileList.value[offset:offset + maxAmount], len(fileList.value)

    def _getFileChangeTime(self, fileInfo):
        with self._lastOpenTimes.readLock:
            lastOpenTime = self._lastOpenTimes.value.get(fileInfo.path)

        with fileInfo.modificationTime.readLock:
            if lastOpenTime:
                if fileInfo.modificationTime.value:
                    return max(lastOpenTime, fileInfo.modificationTime.value)
                return lastOpenTime

            return fileInfo.modificationTime.value

    def _sortFileList(self, fileList):
        fileList.sort(reverse=True, key=self._getFileChangeTime)

    def _onBufEnterInternal(self, path):
        self._lazyInit()

        path = self._getCanonicalPath(path)
        id = self._getFileId(os.path.basename(path))

        with self._lastOpenTimes.writeLock:
            self._lastOpenTimes.value[path] = datetime.now()

        with self._projectMap.readLock:
            projectInfos = [x for x in self._projectMap.value.values()]

        for projInfo in projectInfos:
            with projInfo.idMap.readLock:
                fileList = projInfo.idMap.value.get(id)

            if not fileList:
                continue

            found = False
            with fileList.readLock:
                for fileInfo in fileList.value:
                    if fileInfo.path == path:
                        found = True
                        break

            if found:
                with fileList.writeLock:
                    self._sortFileList(fileList.value)

    @pynvim.autocmd('BufEnter', pattern='*', eval='expand("<afile>")')
    def onBufEnter(self, path):
        try:
            self._onBufEnterInternal(path)
        except Exception as e:
            self._log.exception(e)

    def _convertToFileInfoDictionary(self, fileInfo):
        return {'path': fileInfo.path, 'name': fileInfo.name}

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
            'matches': [self._convertToFileInfoDictionary(x) for x in matchesSlice],
        }


if __name__ == "__main__":
    result = Marksman(None).updateSearch(['C:/Temp/test1', 'f', 0, 5])

    print(result['totalCount'])
