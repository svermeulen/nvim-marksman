
import pynvim
import os
from marksman.util.StringHumpsFinder import getStringHumps
from marksman.util.AsyncCommandExecutor import AsyncCommandExecutor
from marksman.util.PythonSearchHandler import PythonSearchHandler
from marksman.util.SearchExternalCommandBuilder import SearchExternalCommandBuilder, SearchTypes as ExternalSearchTypes
from marksman.util.LockableValue import LockableValue
from marksman.util.ReadWriteLockableValue import ReadWriteLockableValue
from marksman.util.Log import Log
from datetime import datetime
import threading
from queue import Queue
import traceback
import time

SearchTypes = ExternalSearchTypes + ["python", "custom"]
WaitingForSearchTimeout = 5.0

class ProjectInfo:
    def __init__(self, rootPath):
        self.rootPath = rootPath
        self.idMap = ReadWriteLockableValue({})
        self.nameMap = ReadWriteLockableValue({})
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

    def _queueRefresh(self, info):
        if info.isUpdating.getValue():
            return

        info.isUpdating.setValue(True)
        self._refreshQueue.put(info.rootPath)

    @pynvim.function('MarksmanForceRefresh')
    def forceRefresh(self, args):
        self._lazyInit()

        assert len(args) == 1, 'Wrong number of arguments to MarksmanForceRefresh'

        rootPath = self._getCanonicalPath(args[0])

        info = self._getProjectInfo(rootPath)
        self._queueRefresh(info)

    def _waitForProjectToInitialize(self, projectInfo):
        elapsed = 0

        while projectInfo.isUpdating.getValue():
            time.sleep(0.05)
            elapsed += 0.05
            if elapsed > WaitingForSearchTimeout:
                raise RuntimeError(f"Timeout waiting to update project in Marksman!")

    def _tryOpenFirstMatch(self, projectInfo, id):
        self._waitForProjectToInitialize(projectInfo)

        matchesSlice, _ = self._lookupMatchesSlice(projectInfo, id, 0, 1, None)

        if len(matchesSlice) > 0:
            self._nvim.command('e ' + matchesSlice[0].path)
            return True

        return False

    @pynvim.command('MarksmanOpenFirstMatch', nargs='1', range='', sync=True)
    def openFirstMatch(self, args, _):
        self._lazyInit()

        assert len(args) == 2 or len(args) == 1, 'Wrong number of arguments to MarksmanOpenNextMatch'

        rootPath = self._getCanonicalPath(args[0])

        assert os.path.isdir(rootPath), f"Could not find directory '{rootPath}'"

        if len(args) == 1:
            id = ''
        else:
            id = args[1]

        projectInfo = self._getProjectInfo(rootPath)

        if not self._tryOpenFirstMatch(projectInfo, id):
            self._queueRefresh(projectInfo)
            if not self._tryOpenFirstMatch(projectInfo, id):
                self._nvim.command('echo "Could not find match"')

    @pynvim.command('MarksmanOpenNextMatch', nargs='1', range='', sync=True)
    def openNextMatch(self, args, _):
        self._lazyInit()

        assert len(args) == 1, 'Wrong number of arguments to MarksmanOpenNextMatch'

        rootPath = self._getCanonicalPath(args[0])

        assert os.path.isdir(rootPath), f"Could not find directory '{rootPath}'"

        projectInfo = self._getProjectInfo(rootPath)

        self._waitForProjectToInitialize(projectInfo)

        currentPath = self._getCanonicalPath(self._nvim.eval('expand("%:p")'))
        id = self._getFileNameHumps(os.path.basename(currentPath))

        matchesSlice, _ = self._lookupMatchesSlice(projectInfo, id, 0, 1, currentPath)

        if len(matchesSlice) > 0:
            self._nvim.command('e ' + matchesSlice[0].path)
        else:
            self._nvim.command('echo "Could not find alternative path"')

    @pynvim.command('MarksmanProfileSearchMethods', nargs='1', range='', sync=True)
    def profileSearchMethods(self, args, _):
        self._lazyInit()

        dirPath = self._getCanonicalPath(args[0])

        for i in range(2):
            self._log.info(f'Round {i+1}:')

            invalidTypes = []

            for searchType in SearchTypes:
                startTime = datetime.now()

                fileIterator = self._tryScanForFilesUsingSearchType(searchType, dirPath, False)

                if not fileIterator:
                    invalidTypes.append(searchType)
                    continue

                for path in fileIterator:
                    pass

                elapsed = (datetime.now() - startTime).total_seconds()
                self._log.info(f'Searching with "{searchType}" took {elapsed:0.2f} seconds')
                time.sleep(0.001)

        if len(invalidTypes) > 0:
            self._log.info(f'The following were attempted but not supported: {invalidTypes}')

        self._log.info(f'Done profiling')

    @pynvim.function('MarksmanGetProjectFileList', sync=True)
    def getProjectFileList(self, args):
        self._lazyInit()

        assert len(args) == 1, 'Wrong number of arguments to MarksmanGetProjectFileList'

        result = []

        for rootPath in args[0]:
            rootPath = self._getCanonicalPath(rootPath)

            assert os.path.isdir(rootPath), f"Could not find directory '{rootPath}'"

            projectInfo = self._getProjectInfo(rootPath)

            self._waitForProjectToInitialize(projectInfo)

            with projectInfo.nameMap.readLock:
                for pathList in projectInfo.nameMap.value.values():
                    with pathList.readLock:
                        result += pathList.value
        return result

    @pynvim.function('MarksmanLookupByFileName', sync=True)
    def lookupByFileName(self, args):
        self._lazyInit()

        assert len(args) == 2, 'Wrong number of arguments to MarksmanTryOpenByFileName'

        rootPath = self._getCanonicalPath(args[0])

        assert os.path.isdir(rootPath), f"Could not find directory '{rootPath}'"

        fileName = args[1]
        projectInfo = self._getProjectInfo(rootPath)

        self._waitForProjectToInitialize(projectInfo)

        with projectInfo.nameMap.readLock:
            pathList = projectInfo.nameMap.value.get(fileName)

            if not pathList:
                return []

            with pathList.readLock:
                return [x for x in pathList.value]

    @pynvim.function('MarksmanUpdateSearch', sync=True)
    def updateSearch(self, args):
        self._lazyInit()

        assert len(args) == 5, 'Wrong number of arguments to MarksmanUpdateSearch'

        rootPath = self._getCanonicalPath(args[0])

        assert os.path.isdir(rootPath), f"Could not find directory '{rootPath}'"

        requestId = args[1]
        offset = args[2]
        maxAmount = args[3]
        # We could use ignorePath here to hide the current project, but I find that
        # in practice this is more annoying than it is useful
        # ignorePath = self._getCanonicalPath(args[4])
        ignorePath = None

        projectInfo = self._getProjectInfo(rootPath)
        matchesSlice, totalMatchesCount = self._lookupMatchesSlice(
            projectInfo, requestId, offset, maxAmount, ignorePath)

        return {
            'totalCount': projectInfo.totalCount.getValue(),
            'isUpdating': projectInfo.isUpdating.getValue(),
            'matchesCount': totalMatchesCount,
            'matches': [self._convertToFileInfoDictionary(x) for x in matchesSlice],
        }

    def _getFileNameHumps(self, fileName):
        fileNameWithoutExtension = os.path.splitext(os.path.basename(fileName))[0]
        return getStringHumps(fileNameWithoutExtension)

    def _getCanonicalPath(self, path):
        return os.path.realpath(path)

    def _lazyInit(self):
        if self._hasInitialized:
            return

        self._hasInitialized = True
        self._vimSettings = self._getSettings()
        self._log = Log(self._nvim, self._vimSettings['g:Mm_EnableDebugLogging'] != 0)
        self._lastOpenTimes = ReadWriteLockableValue({})
        self._refreshQueue = Queue()
        self._projectMap = ReadWriteLockableValue({})
        self._pythonSearchHandler = PythonSearchHandler(self._vimSettings)
        self._searchCommandBuilder = SearchExternalCommandBuilder(self._vimSettings)
        self._printQueue = Queue()

        searchThread = threading.Thread(target=self._searchThread)
        # die when the main thread dies
        searchThread.daemon = True
        searchThread.start()

    def _getSettings(self):
        variables = [
            'g:Mm_IgnoreDirectoryPatterns', 'g:Mm_IgnoreFilePatterns', 'g:Mm_FollowLinks',
            'g:Mm_CustomSearchCommand', 'g:Mm_ShowHidden', 'g:Mm_SearchPreferenceOrder',
            'g:Mm_EnableDebugLogging'
        ]

        evalNames = [
            "exists('g:Mm_CustomSearchCommand')", "get(g:, 'Mm_RecurseSubmodules', 0)",
            "executable('rg')", "executable('pt')", "executable('ag')", "executable('find')",
            "executable('sed')", "&encoding"
        ]

        # Minimize rpcs by just making one call
        return self._nvim.call("marksman#evalAll", variables, evalNames)

    def _tryScanForFilesUsingSearchType(self, searchType, dirPath, noIgnore):
        os.chdir(dirPath)

        if searchType == "python":
            # This should always work
            return self._pythonSearchHandler.scanForFiles(dirPath, noIgnore)

        if searchType == "custom":
            if not self._vimSettings["exists('g:Mm_CustomSearchCommand')"]:
                return None

            cmd = self._vimSettings["g:Mm_CustomSearchCommand"] % dirPath.join('""')
        else:
            cmd = self._searchCommandBuilder.tryBuildExternalSearchCommand(
                searchType, dirPath, noIgnore)

        if not cmd:
            return None

        if self._log.includeDebugging:
            self._log.queueInfo(f'Marksman External Command: {cmd}')

        return AsyncCommandExecutor().execute(
            cmd, encoding=self._vimSettings["&encoding"])

    def _scanForFiles(self, dirPath, noIgnore):

        for searchType in self._vimSettings["g:Mm_SearchPreferenceOrder"]:
            result = self._tryScanForFilesUsingSearchType(searchType, dirPath, noIgnore)

            if result:
                return result

        assert False, "Could not find valid search type!"

    def _searchThreadInternal(self):
        while True:
            rootPath = self._refreshQueue.get()

            assert os.path.isdir(rootPath), f"Could not find directory '{rootPath}'"

            # self._log.queueDebug(f'Started processing "{rootPath}"')

            startTime = datetime.now()
            projectInfo = self._getProjectInfo(rootPath)
            projectInfo.totalCount.setValue(0)
            assert projectInfo.isUpdating.getValue()

            allFilesList = ReadWriteLockableValue([])

            projectInfo.idMap.setValue({'': allFilesList})

            # TODO - this should be configurable somehow
            # Sometimes you do want one or the other
            noIgnore = False

            for path in self._scanForFiles(rootPath, noIgnore):
                name = os.path.basename(path)
                path = self._getCanonicalPath(os.path.join(rootPath, path.strip()))

                # This can happen with symlink
                if not path.startswith(rootPath):
                    continue

                nameFileList = None
                with projectInfo.nameMap.readLock:
                    nameFileList = projectInfo.nameMap.value.get(name)

                if not nameFileList:
                    nameFileList = ReadWriteLockableValue([])
                    with projectInfo.nameMap.writeLock:
                        projectInfo.nameMap.value[name] = nameFileList

                with nameFileList.writeLock:
                    nameFileList.value.append(path)

                id = self._getFileNameHumps(name)

                if len(id) > 0:
                    idFileList = None
                    with projectInfo.idMap.readLock:
                        idFileList = projectInfo.idMap.value.get(id)

                    if not idFileList:
                        idFileList = ReadWriteLockableValue([])
                        with projectInfo.idMap.writeLock:
                            projectInfo.idMap.value[id] = idFileList

                    fileInfo = FileInfo(path, name)

                    with allFilesList.writeLock:
                        allFilesList.value.append(fileInfo)

                    with idFileList.writeLock:
                        idFileList.value.append(fileInfo)

                    with projectInfo.totalCount.lock:
                        projectInfo.totalCount.value += 1

            with allFilesList.readLock:
                # Update all the modification times
                for fileInfo in allFilesList.value:
                    try:
                        # This can fail sometimes
                        # For example, when using git, deleted files can be listed
                        modTime = datetime.fromtimestamp(os.path.getmtime(fileInfo.path))
                    except Exception as e:
                        continue

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

    def _getProjectInfo(self, rootPath):

        with self._projectMap.readLock:
            info = self._projectMap.value.get(rootPath)

        if not info:
            info = ProjectInfo(rootPath)

            with self._projectMap.writeLock:
                self._projectMap.value[rootPath] = info

            self._refreshQueue.put(rootPath)

        return info

    def _lookupMatchesSlice(self, projectInfo, requestId, offset, maxAmount, ignorePath):

        with projectInfo.idMap.readLock:
            fileList = projectInfo.idMap.value.get(requestId)

        if not fileList:
            return [], 0

        with fileList.readLock:
            return [x for x in fileList.value if x.path != ignorePath and os.path.exists(x.path)][offset:offset + maxAmount], len(fileList.value)

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
        assert self._hasInitialized

        path = self._getCanonicalPath(path)
        id = self._getFileNameHumps(os.path.basename(path))

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
        if not self._hasInitialized:
            return
        try:
            self._onBufEnterInternal(path)
        except Exception as e:
            self._log.exception(e)

    def _convertToFileInfoDictionary(self, fileInfo):
        return {'path': fileInfo.path, 'name': fileInfo.name}


if __name__ == "__main__":
    result = Marksman(None).updateSearch(['C:/Temp/test1', 'f', 0, 5])

    print(result['totalCount'])
