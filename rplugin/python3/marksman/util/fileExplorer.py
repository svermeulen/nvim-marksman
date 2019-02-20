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


def mmEncode(str):
    return str


def lfDecode(str):
    return str


def mmOpen(file, mode='r', buffering=-1, encoding=None, errors=None,
           newline=None, closefd=True):
    return open(file, mode, buffering, encoding, errors, newline, closefd)


class FileExplorer:
    def __init__(self, nvim):
        self._nvim = nvim
        self._cur_dir = ''
        self._content = []
        self._cache_dir = os.path.join(nvim.eval("g:Mm_CacheDirectory"), '.MmCache', 'file')
        self._cache_index = os.path.join(self._cache_dir, 'cacheIndex')
        self._external_cmd = None
        self._initCache()
        self._executor = []
        self._no_ignore = None

    def _initCache(self):
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)
        if not os.path.exists(self._cache_index):
            with mmOpen(self._cache_index, 'w', errors='ignore'):
                pass

    def _getFiles(self, dir):
        start_time = time.time()
        wildignore = self._nvim.eval("g:Mm_WildIgnore")
        file_list = []
        for dir_path, dirs, files in os.walk(dir, followlinks = False
                if self._nvim.eval("g:Mm_FollowLinks") == '0' else True):
            dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i,j)
                       for j in wildignore['dir'])]
            for name in files:
                if True not in (fnmatch.fnmatch(name, j)
                                for j in wildignore['file']):
                    file_list.append(mmEncode(os.path.join(dir_path,name)))
                if time.time() - start_time > float(
                        self._nvim.eval("g:Mm_IndexTimeLimit")):
                    return file_list
        return file_list

    def _getFileList(self, dir):
        dir = dir if dir.endswith(os.sep) else dir + os.sep
        with mmOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            path_length = 0
            target = -1
            for i, line in enumerate(lines):
                path = line.split(None, 2)[2].strip()
                if dir.startswith(path) and len(path) > path_length:
                    path_length = len(path)
                    target = i

            if target != -1:
                lines[target] = re.sub('^\S*',
                                       '%.3f' % time.time(),
                                       lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                with mmOpen(os.path.join(self._cache_dir,
                                         lines[target].split(None, 2)[1]),
                            'r', errors='ignore') as cache_file:
                    if lines[target].split(None, 2)[2].strip() == dir:
                        return cache_file.readlines()
                    else:
                        file_list = [line for line in cache_file.readlines()
                                     if line.startswith(dir)]
                        if file_list == []:
                            file_list = self._getFiles(dir)
                        return file_list
            else:
                start_time = time.time()
                file_list = self._getFiles(dir)
                delta_seconds = time.time() - start_time
                if delta_seconds > float(self._nvim.eval("g:Mm_NeedCacheTime")):
                    cache_file_name = ''
                    if len(lines) < int(self._nvim.eval("g:Mm_NumberOfCache")):
                        f.seek(0, 2)
                        ts = time.time()
                        line = '%.3f cache_%.3f %s\n' % (ts, ts, dir)
                        f.write(line)
                        cache_file_name = 'cache_%.3f' % ts
                    else:
                        for i, line in enumerate(lines):
                            path = line.split(None, 2)[2].strip()
                            if path.startswith(dir):
                                cache_file_name = line.split(None, 2)[1].strip()
                                line = '%.3f %s %s\n' % (time.time(),
                                        cache_file_name, dir)
                                break
                        if cache_file_name == '':
                            timestamp = lines[0].split(None, 2)[0]
                            oldest = 0
                            for i, line in enumerate(lines):
                                if line.split(None, 2)[0] < timestamp:
                                    timestamp = line.split(None, 2)[0]
                                    oldest = i
                            cache_file_name = lines[oldest].split(None, 2)[1].strip()
                            lines[oldest] = '%.3f %s %s\n' % (time.time(),
                                            cache_file_name, dir)
                        f.seek(0)
                        f.truncate(0)
                        f.writelines(lines)
                    with mmOpen(os.path.join(self._cache_dir, cache_file_name),
                                'w', errors='ignore') as cache_file:
                        for line in file_list:
                            cache_file.write(line + '\n')
                return file_list

    def _refresh(self):
        dir = os.path.abspath(self._cur_dir)
        dir = dir if dir.endswith(os.sep) else dir + os.sep
        with mmOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            path_length = 0
            target = -1
            for i, line in enumerate(lines):
                path = line.split(None, 2)[2].strip()
                if dir.startswith(path) and len(path) > path_length:
                    path_length = len(path)
                    target = i

            if target != -1:
                lines[target] = re.sub('^\S*', '%.3f' % time.time(), lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                cache_file_name = lines[target].split(None, 2)[1]
                file_list = self._getFiles(dir)
                with mmOpen(os.path.join(self._cache_dir, cache_file_name),
                            'w', errors='ignore') as cache_file:
                    for line in file_list:
                        cache_file.write(line + '\n')

    def _exists(self, path, dir):
        """
        return True if `dir` exists in `path` or its ancestor path,
        otherwise return False
        """
        if os.name == 'nt':
            # e.g. C:\\
            root = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
        else:
            root = '/'

        while os.path.abspath(path) != root:
            cur_dir = os.path.join(path, dir)
            if os.path.exists(cur_dir) and os.path.isdir(cur_dir):
                return True
            path = os.path.join(path, "..")

        cur_dir = os.path.join(path, dir)
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

    def _buildCmd(self, dir, **kwargs):
        if self._nvim.eval("exists('g:Mm_ExternalCommand')") == '1':
            cmd = self._nvim.eval("g:Mm_ExternalCommand") % dir.join('""')
            self._external_cmd = cmd
            return cmd

        if self._nvim.eval("g:Mm_UseVersionControlTool") == '1':
            if self._exists(dir, ".git"):
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

                if "--no-ignore" in kwargs.get("arguments", {}):
                    no_ignore = ""
                else:
                    no_ignore = "--exclude-standard"

                if self._nvim.eval("get(g:, 'Mm_RecurseSubmodules', 0)") == '1':
                    recurse_submodules = "--recurse-submodules"
                else:
                    recurse_submodules = ""

                cmd = "git ls-files %s && git ls-files --others %s %s" % (recurse_submodules, no_ignore, ignore)
                self._external_cmd = cmd
                return cmd
            elif self._exists(dir, ".hg"):
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

                cmd = 'hg files %s "%s"' % (ignore, dir)
                self._external_cmd = cmd
                return cmd

        if self._nvim.eval("exists('g:Mm_DefaultExternalTool')") == '1':
            default_tool = {"rg": 0, "pt": 0, "ag": 0, "find": 0}
            tool = self._nvim.eval("g:Mm_DefaultExternalTool")
            if tool and self._nvim.eval("executable('%s')" % tool) == '0':
                raise Exception("executable '%s' can not be found!" % tool)
            default_tool[tool] = 1
        else:
            default_tool = {"rg": 1, "pt": 1, "ag": 1, "find": 1}

        if default_tool["rg"] and self._nvim.eval("executable('rg')") == '1':
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            if os.name == 'nt': # https://github.com/BurntSushi/ripgrep/issues/500
                color = ""
                ignore = ""
                for i in wildignore["dir"]:
                    if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'): # rg does not show hidden files by default
                        ignore += ' -g "!%s"' % i
                for i in wildignore["file"]:
                    if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'):
                        ignore += ' -g "!%s"' % i
            else:
                color = "--color never"
                ignore = ""
                for i in wildignore["dir"]:
                    if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'):
                        ignore += " -g '!%s'" % i
                for i in wildignore["file"]:
                    if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'):
                        ignore += " -g '!%s'" % i

            if self._nvim.eval("g:Mm_FollowLinks") == '1':
                followlinks = "-L"
            else:
                followlinks = ""

            if self._nvim.eval("g:Mm_ShowHidden") == '0':
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if "--no-ignore" in kwargs.get("arguments", {}):
                no_ignore = "--no-ignore"
            else:
                no_ignore = ""

            if dir == '.':
                cur_dir = ''
            else:
                cur_dir = '"%s"' % dir

            cmd = 'rg --no-messages --files %s %s %s %s %s %s' % (color, ignore, followlinks, show_hidden, no_ignore, cur_dir)
        elif default_tool["pt"] and self._nvim.eval("executable('pt')") == '1' and os.name != 'nt': # there is bug on Windows
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            ignore = ""
            for i in wildignore["dir"]:
                if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'): # pt does not show hidden files by default
                    ignore += " --ignore=%s" % i
            for i in wildignore["file"]:
                if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'):
                    ignore += " --ignore=%s" % i

            if self._nvim.eval("g:Mm_FollowLinks") == '1':
                followlinks = "-f"
            else:
                followlinks = ""

            if self._nvim.eval("g:Mm_ShowHidden") == '0':
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if "--no-ignore" in kwargs.get("arguments", {}):
                no_ignore = "-U"
            else:
                no_ignore = ""

            cmd = 'pt --nocolor %s %s %s %s -g="" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dir)
        elif default_tool["ag"] and self._nvim.eval("executable('ag')") == '1' and os.name != 'nt': # https://github.com/vim/vim/issues/3236
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            ignore = ""
            for i in wildignore["dir"]:
                if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'): # ag does not show hidden files by default
                    ignore += ' --ignore "%s"' % i
            for i in wildignore["file"]:
                if self._nvim.eval("g:Mm_ShowHidden") != '0' or not i.startswith('.'):
                    ignore += ' --ignore "%s"' % i

            if self._nvim.eval("g:Mm_FollowLinks") == '1':
                followlinks = "-f"
            else:
                followlinks = ""

            if self._nvim.eval("g:Mm_ShowHidden") == '0':
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if "--no-ignore" in kwargs.get("arguments", {}):
                no_ignore = "-U"
            else:
                no_ignore = ""

            cmd = 'ag --nocolor --silent %s %s %s %s -g "" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dir)
        elif default_tool["find"] and self._nvim.eval("executable('find')") == '1' \
                and self._nvim.eval("executable('sed')") == '1' and os.name != 'nt':
            wildignore = self._nvim.eval("g:Mm_WildIgnore")
            ignore_dir = ""
            for d in wildignore["dir"]:
                ignore_dir += '-type d -name "%s" -prune -o ' % d

            ignore_file = ""
            for f in wildignore["file"]:
                    ignore_file += '-type f -name "%s" -o ' % f

            if self._nvim.eval("g:Mm_FollowLinks") == '1':
                followlinks = "-L"
            else:
                followlinks = ""

            strip = ""

            if os.name == 'nt':
                redir_err = ""
            else:
                redir_err = " 2>/dev/null"

            if self._nvim.eval("g:Mm_ShowHidden") == '0':
                show_hidden = '-name ".*" -prune -o'
            else:
                show_hidden = ""

            cmd = 'find %s "%s" -name "." -o %s %s %s -type f -print %s %s' % (followlinks,
                                                                               dir,
                                                                               ignore_dir,
                                                                               ignore_file,
                                                                               show_hidden,
                                                                               redir_err,
                                                                               strip)
        else:
            cmd = None

        self._external_cmd = cmd

        return cmd

    def _writeCache(self, content):
        dir = self._cur_dir if self._cur_dir.endswith(os.sep) else self._cur_dir + os.sep
        with mmOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            target = -1
            for i, line in enumerate(lines):
                if dir == line.split(None, 2)[2].strip():
                    target = i
                    break

            if target != -1:    # already cached
                if time.time() - self._cmd_start_time <= float(self._nvim.eval("g:Mm_NeedCacheTime")):
                    os.remove(os.path.join(self._cache_dir, lines[target].split(None, 2)[1]))
                    del lines[target]
                    f.seek(0)
                    f.truncate(0)
                    f.writelines(lines)
                    return

                # update the time
                lines[target] = re.sub('^\S*',
                                       '%.3f' % time.time(),
                                       lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                with mmOpen(os.path.join(self._cache_dir,
                                         lines[target].split(None, 2)[1]),
                            'w', errors='ignore') as cache_file:
                    for line in content:
                        cache_file.write(line + '\n')
            else:
                if time.time() - self._cmd_start_time <= float(self._nvim.eval("g:Mm_NeedCacheTime")):
                    return

                cache_file_name = ''
                if len(lines) < int(self._nvim.eval("g:Mm_NumberOfCache")):
                    f.seek(0, 2)
                    ts = time.time()
                    # e.g., line = "1496669495.329 cache_1496669495.329 /foo/bar"
                    line = '%.3f cache_%.3f %s\n' % (ts, ts, dir)
                    f.write(line)
                    cache_file_name = 'cache_%.3f' % ts
                else:
                    timestamp = lines[0].split(None, 2)[0]
                    oldest = 0
                    for i, line in enumerate(lines):
                        if line.split(None, 2)[0] < timestamp:
                            timestamp = line.split(None, 2)[0]
                            oldest = i
                    cache_file_name = lines[oldest].split(None, 2)[1].strip()
                    lines[oldest] = '%.3f %s %s\n' % (time.time(), cache_file_name, dir)

                    f.seek(0)
                    f.truncate(0)
                    f.writelines(lines)

                with mmOpen(os.path.join(self._cache_dir, cache_file_name),
                            'w', errors='ignore') as cache_file:
                    for line in content:
                        cache_file.write(line + '\n')

    def _getFilesFromCache(self):
        dir = self._cur_dir if self._cur_dir.endswith(os.sep) else self._cur_dir + os.sep
        with mmOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            target = -1
            for i, line in enumerate(lines):
                if dir == line.split(None, 2)[2].strip():
                    target = i
                    break

            if target != -1:    # already cached
                # update the time
                lines[target] = re.sub('^\S*',
                                       '%.3f' % time.time(),
                                       lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                with mmOpen(os.path.join(self._cache_dir,
                                         lines[target].split(None, 2)[1]),
                            'r', errors='ignore') as cache_file:
                    file_list = cache_file.readlines()
                    if not file_list: # empty
                        return None

                    if os.path.isabs(file_list[0]):
                        return file_list
                    else:
                        return [os.path.join(mmEncode(dir), file) for file in file_list]
            else:
                return None

    def lookupFiles(self, rootPath, useCache):
        os.chdir(rootPath)
        return self.getContent(refresh=not useCache)

    def getContent(self, *args, **kwargs):
        files = kwargs.get("arguments", {}).get("--file", [])
        if files:
            result = []
            for file in files:
                with mmOpen(file, 'r', errors='ignore') as f:
                    result += f.readlines()
            return result

        if kwargs.get("arguments", {}).get("directory"):
            dir = kwargs.get("arguments", {}).get("directory")[0]
            if os.path.exists(os.path.expanduser(lfDecode(dir))):
                self._nvim.command("silent cd %s" % dir)
            else:
                self._nvim.command("echohl ErrorMsg | redraw | echon "
                                   "'Unknown directory `%s`' | echohl NONE" % dir)
                return None

        dir = os.getcwd()

        no_ignore = kwargs.get("arguments", {}).get("--no-ignore")
        if no_ignore != self._no_ignore:
            self._no_ignore = no_ignore
            arg_changes = True
        else:
            arg_changes = False

        if arg_changes or self._nvim.eval("g:Mm_UseMemoryCache") == '0' or dir != self._cur_dir or \
                not self._content:
            self._cur_dir = dir

            cmd = self._buildCmd(dir, **kwargs)
            self._nvim.command("let g:Mm_Debug_Cmd = '%s'" % escQuote(cmd))

            if self._nvim.eval("g:Mm_UseCache") == '1' and not kwargs.get("refresh", False):
                self._content = self._getFilesFromCache()
                if self._content:
                    return self._content

            if cmd:
                executor = AsyncExecutor()
                self._executor.append(executor)
                if cmd.split(None, 1)[0] == "dir":
                    content = executor.execute(cmd)
                else:
                    content = executor.execute(cmd, encoding=self._nvim.eval("&encoding"))
                self._cmd_start_time = time.time()
                return content
            else:
                self._content = self._getFileList(dir)

        return self._content

    def getFreshContent(self, *args, **kwargs):
        if self._external_cmd:
            self._content = []
            kwargs["refresh"] = True
            return self.getContent(*args, **kwargs)

        self._refresh()
        self._content = self._getFileList(self._cur_dir)
        return self._content

    def getStlCategory(self):
        return 'File'

    def getStlCurDir(self):
        return escQuote(mmEncode(os.path.abspath(self._cur_dir)))

    def supportsMulti(self):
        return True

    def supportsNameOnly(self):
        return True

    def cleanup(self):
        for exe in self._executor:
            exe.killProcess()
        self._executor = []
