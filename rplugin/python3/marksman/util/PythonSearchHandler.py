
import os

class PythonSearchHandler:
    def __init__(self, vimSettings):
        self._vimSettings = vimSettings

    def scanForFiles(self, rootDir, noIgnore):
        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]
        fileList = []

        followlinks = False if not self._vimSettings["g:Mm_FollowLinks"] else True

        for dirPath, dirs, files in os.walk(rootDir, followlinks=followlinks):
            dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i, j)
                       for j in wildignoreDir)]
            for name in files:
                if True not in (fnmatch.fnmatch(name, j) for j in wildignoreFile):
                    fileList.append(os.path.join(dirPath, name))
        return fileList

