#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import os.path
import fnmatch
import time
from .asyncExecutor import AsyncExecutor


def escQuote(str):
    return "" if str is None else str.replace("'", "''")


def mmOpen(file, mode='r', buffering=-1, encoding=None, errors=None,
           newline=None, closefd=True):
    return open(file, mode, buffering, encoding, errors, newline, closefd)


class FileExplorer:
    def __init__(self, nvim):
        self._nvim = nvim

    def _getFilesWithPythonDirectly(self, rootDir):
        startTime = time.time()
        wildignore = self._nvim.eval("g:Mm_WildIgnore")
        fileList = []

        for dirPath, dirs, files in os.walk(
                rootDir, followlinks=False
                if not self._nvim.eval("g:Mm_FollowLinks") else True):
            dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i, j)
                       for j in wildignore['dir'])]
            for name in files:
                if True not in (fnmatch.fnmatch(name, j)
                                for j in wildignore['file']):
                    fileList.append(os.path.join(dirPath, name))
                if time.time() - startTime > float(
                        self._nvim.eval("g:Mm_IndexTimeLimit")):
                    return fileList
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

    def _tryBuildCmd(self, dirPath, noIgnore):
        if self._nvim.eval("exists('g:Mm_ExternalCommand')"):
            return self._nvim.eval("g:Mm_ExternalCommand") % dirPath.join('""')

        if self._nvim.eval("g:Mm_UseVersionControlTool"):
            if self._exists(dirPath, ".git"):
                wildignore = self._nvim.eval("g:Mm_WildIgnore")
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

                if self._nvim.eval("get(g:, 'Mm_RecurseSubmodules', 0)"):
                    recurse_submodules = "--recurse-submodules"
                else:
                    recurse_submodules = ""

                return "git ls-files %s && git ls-files --others %s %s" % (recurse_submodules, no_ignore, ignore)

            if self._exists(dirPath, ".hg"):
                wildignore = self._nvim.eval("g:Mm_WildIgnore")
                if ".hg" in wildignore["dir"]:
                    wildignore["dir"].remove(".hg")
                if ".hg" in wildignore["file"]:
                    wildignore["file"].remove(".hg")
                ignore = ""
                for i in wildignore["dir"]:
                    ignore += ' -X "%s"' % self._expandGlob("dir", i)
                for i in wildignore["file"]:
                    ignore += ' -X "%s"' % self._expandGlob("file", i)

                return 'hg files %s "%s"' % (ignore, dirPath)

        if self._nvim.eval("exists('g:Mm_DefaultExternalTool')"):
            default_tool = {"rg": 0, "pt": 0, "ag": 0, "find": 0}
            tool = self._nvim.eval("g:Mm_DefaultExternalTool")
            if tool and not self._nvim.eval("executable('%s')" % tool):
                raise Exception("executable '%s' can not be found!" % tool)
            default_tool[tool] = 1
        else:
            default_tool = {"rg": 1, "pt": 1, "ag": 1, "find": 1}

        if default_tool["rg"] and self._nvim.eval("executable('rg')"):
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            # https://github.com/BurntSushi/ripgrep/issues/500
            if os.name == 'nt':
                color = ""
                ignore = ""
                for i in wildignore["dir"]:
                    # rg does not show hidden files by default
                    if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                        ignore += ' -g "!%s"' % i
                for i in wildignore["file"]:
                    if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                        ignore += ' -g "!%s"' % i
            else:
                color = "--color never"
                ignore = ""
                for i in wildignore["dir"]:
                    if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                        ignore += " -g '!%s'" % i
                for i in wildignore["file"]:
                    if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                        ignore += " -g '!%s'" % i

            if self._nvim.eval("g:Mm_FollowLinks"):
                followlinks = "-L"
            else:
                followlinks = ""

            if not self._nvim.eval("g:Mm_ShowHidden"):
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if noIgnore:
                no_ignore = "--no-ignore"
            else:
                no_ignore = ""

            return 'rg --no-messages --files %s %s %s %s %s' % (
                color, ignore, followlinks, show_hidden, no_ignore)

        # there is bug on Windows
        if default_tool["pt"] and self._nvim.eval("executable('pt')") and os.name != 'nt':
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            ignore = ""
            for i in wildignore["dir"]:
                # pt does not show hidden files by default
                if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                    ignore += " --ignore=%s" % i
            for i in wildignore["file"]:
                if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                    ignore += " --ignore=%s" % i

            if self._nvim.eval("g:Mm_FollowLinks"):
                followlinks = "-f"
            else:
                followlinks = ""

            if not self._nvim.eval("g:Mm_ShowHidden"):
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if noIgnore:
                no_ignore = "-U"
            else:
                no_ignore = ""

            return 'pt --nocolor %s %s %s %s -g="" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dirPath)

        # https://github.com/vim/vim/issues/3236
        if default_tool["ag"] and self._nvim.eval("executable('ag')") and os.name != 'nt':
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            ignore = ""
            for i in wildignore["dir"]:
                # ag does not show hidden files by default
                if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                    ignore += ' --ignore "%s"' % i
            for i in wildignore["file"]:
                if self._nvim.eval("g:Mm_ShowHidden") or not i.startswith('.'):
                    ignore += ' --ignore "%s"' % i

            if self._nvim.eval("g:Mm_FollowLinks"):
                followlinks = "-f"
            else:
                followlinks = ""

            if not self._nvim.eval("g:Mm_ShowHidden"):
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if noIgnore:
                no_ignore = "-U"
            else:
                no_ignore = ""

            return 'ag --nocolor --silent %s %s %s %s -g "" "%s"' % (
                ignore, followlinks, show_hidden, no_ignore, dirPath)

        if default_tool["find"] and self._nvim.eval("executable('find')") \
                and self._nvim.eval("executable('sed')") and os.name != 'nt':
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            ignore_dir = ""
            for d in wildignore["dir"]:
                ignore_dir += '-type d -name "%s" -prune -o ' % d

            ignore_file = ""
            for f in wildignore["file"]:
                    ignore_file += '-type f -name "%s" -o ' % f

            if self._nvim.eval("g:Mm_FollowLinks"):
                followlinks = "-L"
            else:
                followlinks = ""

            strip = ""

            if os.name == 'nt':
                redir_err = ""
            else:
                redir_err = " 2>/dev/null"

            if not self._nvim.eval("g:Mm_ShowHidden"):
                show_hidden = '-name ".*" -prune -o'
            else:
                show_hidden = ""

            return 'find %s "%s" -name "." -o %s %s %s -type f -print %s %s' % (
                followlinks, dirPath, ignore_dir, ignore_file, show_hidden, redir_err, strip)

        return None

    def getAllFilesUnderDirectory(self, rootDir, noIgnore):
        os.chdir(rootDir)

        cmd = self._tryBuildCmd(rootDir, noIgnore)
        self._nvim.command("let g:Mm_LastCmd = '%s'" % escQuote(cmd))

        if cmd:
            executor = AsyncExecutor()
            if cmd.split(None, 1)[0] == "dir":
                fileList = executor.execute(cmd)
            else:
                fileList = executor.execute(
                    cmd, encoding=self._nvim.eval("&encoding"))
            self._cmdStartTime = time.time()
        else:
            fileList = self._getFilesWithPythonDirectly(rootDir)

        return fileList
