#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import os.path
import fnmatch
import time
from .AsyncExecutor import AsyncExecutor


def mmOpen(file, mode='r', buffering=-1, encoding=None, errors=None,
           newline=None, closefd=True):
    return open(file, mode, buffering, encoding, errors, newline, closefd)


class FileExplorer:
    def __init__(self, log, settings):
        self._log = log
        self._settings = settings
        self._searchMethods = {
            "rg": self._rgSearch, "hg": self._hgSearch,
            "git": self._gitSearch, "pt": self._ptSearch,
            "find": self._findSearch, "ag": self._agSearch,
        }

    def _getFilesWithPythonDirectly(self, rootDir):
        wildignore = self._settings["g:Mm_WildIgnore"]
        fileList = []

        followlinks = False if not self._settings["g:Mm_FollowLinks"] else True

        for dirPath, dirs, files in os.walk(rootDir, followlinks=followlinks):
            dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i, j)
                       for j in wildignore['dir'])]
            for name in files:
                if True not in (fnmatch.fnmatch(name, j) for j in wildignore['file']):
                    fileList.append(os.path.join(dirPath, name))
        return fileList

    def _exists(self, path, dirPath):
        """
        return True if `dirPath` exists in `path` or its ancestor path,
        otherwise return False
        """
        if os.name == 'nt':
            # e.g. C:\\
            root = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
        else:
            root = '/'

        while os.path.abspath(path) != root:
            cur_dir = os.path.join(path, dirPath)
            if os.path.exists(cur_dir) and os.path.isdir(cur_dir):
                return True
            path = os.path.join(path, "..")

        cur_dir = os.path.join(path, dirPath)
        if os.path.exists(cur_dir) and os.path.isdir(cur_dir):
            return True

        return False

    def _expandGlob(self, type, glob):
        # is absolute path
        if os.name == 'nt' and re.match(r"^[a-zA-Z]:[/\\]", glob) or glob.startswith('/'):
            if type == "file":
                return glob
            elif type == "dir":
                return os.path.join(glob, '*')
            else:
                return glob
        else:
            if type == "file":
                return "**/" + glob
            elif type == "dir":
                return "**/" + os.path.join(glob, '*')
            else:
                return glob

    def _hgSearch(self, dirPath, noIgnore):
        if not self._exists(dirPath, ".hg"):
            return None

        wildignore = self._settings["g:Mm_WildIgnore"]
        if ".hg" in wildignore["dir"]:
            wildignore["dir"].remove(".hg")
        if ".hg" in wildignore["file"]:
            wildignore["file"].remove(".hg")
        ignore = ""
        for i in wildignore["dir"]:
            ignore += ' -X "%s"' % self._expandGlob("dir", i)
        for i in wildignore["file"]:
            ignore += ' -X "%s"' % self._expandGlob("file", i)

        cmd = 'hg files %s "%s"' % (ignore, dirPath)
        return self._runExternalCommand(cmd)

    def _gitSearch(self, dirPath, noIgnore):
        if not self._exists(dirPath, ".git"):
            return None

        wildignore = self._settings["g:Mm_WildIgnore"]
        if ".git" in wildignore["dir"]:
            wildignore["dir"].remove(".git")
        if ".git" in wildignore["file"]:
            wildignore["file"].remove(".git")
        ignore = ""
        for i in wildignore["dir"]:
            ignore += ' -x "%s"' % i
        for i in wildignore["file"]:
            ignore += ' -x "%s"' % i

        if noIgnore:
            no_ignore = ""
        else:
            no_ignore = "--exclude-standard"

        if self._settings["get(g:, 'Mm_RecurseSubmodules', 0)"]:
            recurse_submodules = "--recurse-submodules"
        else:
            recurse_submodules = ""

        cmd = "git ls-files %s && git ls-files --others %s %s" % (recurse_submodules, no_ignore, ignore)
        return self._runExternalCommand(cmd)

    def _ptSearch(self, dirPath, noIgnore):
        # there is bug on Windows
        if os.name == 'nt':
            return None

        if not self._settings["executable('pt')"]:
            return None

        wildignore = self._settings["g:Mm_WildIgnore"]
        ignore = ""
        for i in wildignore["dir"]:
            # pt does not show hidden files by default
            if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += " --ignore=%s" % i
        for i in wildignore["file"]:
            if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += " --ignore=%s" % i

        if self._settings["g:Mm_FollowLinks"]:
            followlinks = "-f"
        else:
            followlinks = ""

        if not self._settings["g:Mm_ShowHidden"]:
            show_hidden = ""
        else:
            show_hidden = "--hidden"

        if noIgnore:
            no_ignore = "-U"
        else:
            no_ignore = ""

        cmd = 'pt --nocolor %s %s %s %s -g="" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dirPath)
        return self._runExternalCommand(cmd)

    def _findSearch(self, dirPath, noIgnore):
        if os.name == 'nt':
            return None

        if not self._settings["executable('find')"] or not self._settings["executable('sed')"]:
            return None

        wildignore = self._settings["g:Mm_WildIgnore"]
        ignore_dir = ""
        for d in wildignore["dir"]:
            ignore_dir += '-type d -name "%s" -prune -o ' % d

        ignore_file = ""
        for f in wildignore["file"]:
                ignore_file += '-type f -name "%s" -o ' % f

        if self._settings["g:Mm_FollowLinks"]:
            followlinks = "-L"
        else:
            followlinks = ""

        strip = ""

        if os.name == 'nt':
            redir_err = ""
        else:
            redir_err = " 2>/dev/null"

        if not self._settings["g:Mm_ShowHidden"]:
            show_hidden = '-name ".*" -prune -o'
        else:
            show_hidden = ""

        cmd = 'find %s "%s" -name "." -o %s %s %s -type f -print %s %s' % (
            followlinks, dirPath, ignore_dir, ignore_file, show_hidden, redir_err, strip)
        return self._runExternalCommand(cmd)

    def _agSearch(self, dirPath, noIgnore):
        if not self._settings["executable('ag')"] or os.name == 'nt':
            return None

        wildignore = self._settings["g:Mm_WildIgnore"]
        ignore = ""
        for i in wildignore["dir"]:
            # ag does not show hidden files by default
            if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += ' --ignore "%s"' % i
        for i in wildignore["file"]:
            if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += ' --ignore "%s"' % i

        if self._settings["g:Mm_FollowLinks"]:
            followlinks = "-f"
        else:
            followlinks = ""

        if not self._settings["g:Mm_ShowHidden"]:
            show_hidden = ""
        else:
            show_hidden = "--hidden"

        if noIgnore:
            no_ignore = "-U"
        else:
            no_ignore = ""

        cmd = 'ag --nocolor --silent %s %s %s %s -g "" "%s"' % (
            ignore, followlinks, show_hidden, no_ignore, dirPath)
        return self._runExternalCommand(cmd)

    def _rgSearch(self, dirPath, noIgnore):

        if not self._settings["executable('rg')"]:
            return None

        wildignore = self._settings["g:Mm_WildIgnore"]
        # https://github.com/BurntSushi/ripgrep/issues/500
        if os.name == 'nt':
            color = ""
            ignore = ""
            for i in wildignore["dir"]:
                # rg does not show hidden files by default
                if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += ' -g "!%s"' % i
            for i in wildignore["file"]:
                if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += ' -g "!%s"' % i
        else:
            color = "--color never"
            ignore = ""
            for i in wildignore["dir"]:
                if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += " -g '!%s'" % i
            for i in wildignore["file"]:
                if self._settings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += " -g '!%s'" % i

        if self._settings["g:Mm_FollowLinks"]:
            followlinks = "-L"
        else:
            followlinks = ""

        if not self._settings["g:Mm_ShowHidden"]:
            show_hidden = ""
        else:
            show_hidden = "--hidden"

        if noIgnore:
            no_ignore = "--no-ignore"
        else:
            no_ignore = ""

        cmd = 'rg --no-messages --files %s %s %s %s %s' % (
            color, ignore, followlinks, show_hidden, no_ignore)
        return self._runExternalCommand(cmd)

    def _runExternalCommand(self, cmd):
        self._log.debug(f'Running external command "{cmd}"')
        executor = AsyncExecutor()
        if cmd.split(None, 1)[0] == "dir":
            return executor.execute(cmd)

        return executor.execute(
            cmd, encoding=self._settings["&encoding"])

    def getAllFilesUnderDirectory(self, dirPath, noIgnore):
        os.chdir(dirPath)

        self._log.debug(f'doing things')

        if self._settings["exists('g:Mm_ExternalCommand')"]:
            return self._runExternalCommand(
                self._settings["g:Mm_ExternalCommand"] % dirPath.join('""'))

        for searchType in self._settings["g:Mm_SearchPreferenceOrder"]:
            fileList = self._searchMethods[searchType](dirPath, noIgnore)

            if fileList:
                return fileList

        assert False, "Could not find valid search type!"
