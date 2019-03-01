#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import os.path
import fnmatch

SearchTypes = ["rg", "hg", "git", "pt", "find", "ag"]

class SearchExternalCommandBuilder:
    def __init__(self, vimSettings):
        self._vimSettings = vimSettings

    def tryBuildExternalSearchCommand(self, searchType, rootDir, noIgnore):
        if searchType == "rg":
            return self._rgSearch(rootDir, noIgnore)

        if searchType == "hg":
            return self._hgSearch(rootDir, noIgnore)

        if searchType == "git":
            return self._gitSearch(rootDir, noIgnore)

        if searchType == "pt":
            return self._ptSearch(rootDir, noIgnore)

        if searchType == "find":
            return self._findSearch(rootDir, noIgnore)

        if searchType == "ag":
            return self._agSearch(rootDir, noIgnore)

        if searchType == "python":
            return self._pythonSearch(rootDir, noIgnore)

        assert False, f'Invalid search type "{searchType}"'

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

        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]

        if ".hg" in wildignoreDir:
            wildignoreDir.remove(".hg")
        if ".hg" in wildignoreFile:
            wildignoreFile.remove(".hg")
        ignore = ""
        for i in wildignoreDir:
            ignore += ' -X "%s"' % self._expandGlob("dir", i)
        for i in wildignoreFile:
            ignore += ' -X "%s"' % self._expandGlob("file", i)

        return 'hg files %s "%s"' % (ignore, dirPath)

    def _gitSearch(self, dirPath, noIgnore):
        if not self._exists(dirPath, ".git"):
            return None

        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]

        if ".git" in wildignoreDir:
            wildignoreDir.remove(".git")
        if ".git" in wildignoreFile:
            wildignoreFile.remove(".git")
        ignore = ""
        for i in wildignoreDir:
            ignore += ' -x "%s"' % i
        for i in wildignoreFile:
            ignore += ' -x "%s"' % i

        if noIgnore:
            no_ignore = ""
        else:
            no_ignore = "--exclude-standard"

        if self._vimSettings["get(g:, 'Mm_RecurseSubmodules', 0)"]:
            recurse_submodules = "--recurse-submodules"
        else:
            recurse_submodules = ""

        return "git ls-files %s && git ls-files --others %s %s" % (recurse_submodules, no_ignore, ignore)

    def _ptSearch(self, dirPath, noIgnore):
        # there is bug on Windows
        if os.name == 'nt':
            return None

        if not self._vimSettings["executable('pt')"]:
            return None

        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]

        ignore = ""
        for i in wildignoreDir:
            # pt does not show hidden files by default
            if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += " --ignore=%s" % i
        for i in wildignoreFile:
            if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += " --ignore=%s" % i

        if self._vimSettings["g:Mm_FollowLinks"]:
            followlinks = "-f"
        else:
            followlinks = ""

        if not self._vimSettings["g:Mm_ShowHidden"]:
            show_hidden = ""
        else:
            show_hidden = "--hidden"

        if noIgnore:
            no_ignore = "-U"
        else:
            no_ignore = ""

        return 'pt --nocolor %s %s %s %s -g="" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dirPath)

    def _findSearch(self, dirPath, noIgnore):
        if os.name == 'nt':
            return None

        if not self._vimSettings["executable('find')"] or not self._vimSettings["executable('sed')"]:
            return None

        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]

        ignore_dir = ""
        for d in wildignoreDir:
            ignore_dir += '-type d -name "%s" -prune -o ' % d

        ignore_file = ""
        for f in wildignoreFile:
                ignore_file += '-type f -name "%s" -o ' % f

        if self._vimSettings["g:Mm_FollowLinks"]:
            followlinks = "-L"
        else:
            followlinks = ""

        strip = ""

        if os.name == 'nt':
            redir_err = ""
        else:
            redir_err = " 2>/dev/null"

        if not self._vimSettings["g:Mm_ShowHidden"]:
            show_hidden = '-name ".*" -prune -o'
        else:
            show_hidden = ""

        return 'find %s "%s" -name "." -o %s %s %s -type f -print %s %s' % (
            followlinks, dirPath, ignore_dir, ignore_file, show_hidden, redir_err, strip)

    def _agSearch(self, dirPath, noIgnore):
        # TODO - Is it worth getting this working on windows?
        if not self._vimSettings["executable('ag')"] or os.name == 'nt':
            return None

        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]

        ignore = ""
        for i in wildignoreDir:
            # ag does not show hidden files by default
            if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += ' --ignore "%s"' % i
        for i in wildignoreFile:
            if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                ignore += ' --ignore "%s"' % i

        if self._vimSettings["g:Mm_FollowLinks"]:
            followlinks = "-f"
        else:
            followlinks = ""

        if not self._vimSettings["g:Mm_ShowHidden"]:
            show_hidden = ""
        else:
            show_hidden = "--hidden"

        if noIgnore:
            no_ignore = "-U"
        else:
            no_ignore = ""

        return 'ag --nocolor --silent %s %s %s %s -g "" "%s"' % (
            ignore, followlinks, show_hidden, no_ignore, dirPath)

    def _rgSearch(self, dirPath, noIgnore):

        if not self._vimSettings["executable('rg')"]:
            return None

        wildignoreDir = self._vimSettings["g:Mm_IgnoreDirectoryPatterns"]
        wildignoreFile = self._vimSettings["g:Mm_IgnoreFilePatterns"]

        # https://github.com/BurntSushi/ripgrep/issues/500
        if os.name == 'nt':
            color = ""
            ignore = ""
            for i in wildignoreDir:
                # rg does not show hidden files by default
                if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += ' -g "!%s"' % i
            for i in wildignoreFile:
                if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += ' -g "!%s"' % i
        else:
            color = "--color never"
            ignore = ""
            for i in wildignoreDir:
                if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += " -g '!%s'" % i
            for i in wildignoreFile:
                if self._vimSettings["g:Mm_ShowHidden"] or not i.startswith('.'):
                    ignore += " -g '!%s'" % i

        if self._vimSettings["g:Mm_FollowLinks"]:
            followlinks = "-L"
        else:
            followlinks = ""

        if not self._vimSettings["g:Mm_ShowHidden"]:
            show_hidden = ""
        else:
            show_hidden = "--hidden"

        if noIgnore:
            no_ignore = "--no-ignore"
        else:
            no_ignore = ""

        return 'rg --no-messages --files %s %s %s %s %s' % (
            color, ignore, followlinks, show_hidden, no_ignore)

