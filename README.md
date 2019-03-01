
<img align="right" width="281" height="284" src="https://i.imgur.com/etJCqp2.png">

# Marksman.vim

Marksman is a file finder.  However, it is not a fuzzy file finder like [CtrlP](https://github.com/kien/ctrlp.vim), [Leaderf](https://github.com/Yggdroot/LeaderF), or [Fzf](https://github.com/junegunn/fzf.vim).  Unlike these tools, with Marksman each file has a generated shorthand that is derived from the file name that you have to type exactly in order to go to the file.

This shorthand is chosen based on the 'humps' in the file name.  For example, the files "FooBar.py", "fooBar.cpp" and "foo_bar.txt" will have a generated shorthand 'fb'.  So in order to select this file you would execute Marksman, then type 'fb' then press enter.

Note that it is not meant as a replacement for a fuzzy finder.  It is meant for cases where you already know the exact name of the file you want to go to and want to get there in the fewest keystrokes possible.

# Installation

If using [vim-plug](https://github.com/junegunn/vim-plug) then you can install with the following line:

```
Plug 'svermeulen/nvim-marksman', { 'do': ':UpdateRemotePlugins' }
```

# Usage

To run, execute the command `:Marksman`.  By default this will run in the current working directly.  You can also specify the directory explicitly, for example by running `:Marksman C:/Foo/Bar`.

You might want to bind a command to it, for example:

```
nnoremap <leader>m :<c-u>Marksman<cr>
```

What it looks like:  (note the text in the status bar)

![example](https://i.imgur.com/sFe4v0y.gif)

When it is initially run it will asynchronously populate the list of files by scanning the given directory.  It will attempt to use external commands such as [rg](https://github.com/BurntSushi/ripgrep), [ag](https://github.com/ggreer/the_silver_searcher), `pt`, and `find`, or if none of those can be found then it will just directly search inside python.

Once it has started populating the list of the files, you can start typing the humps of the file that you are looking for.  In some cases there might be multiple matches, in which case you can cycle between the list by pressing `<c-l>` or `<c-h>` (note that this is also configurable below).  Once you have found the file you are looking for, press enter to open it.

Note that Marksman will try to choose an intelligent order to present the files in.  By default this will be chosen based on the file modification time and also the last time the file was opened in vim (whichever is more recent)

Note also that Marksman will cache the results in memory, so if you add files during your vim session you need to force refresh Marksman by pressing `<F5>` in order for the new files to show up.

# Keys

After launching Marksman:

| Command               | Default       | Description
| -------               | -----------   | -----------
| `exit`                | `\<ESC>`      | Cancel Marksman
| `open`                | `\<ENTER>`    | Open the selected file
| `scroll_left`         | `[`           | Scroll the list backward
| `scroll_right`        | `]`           | Scroll the list forward
| `delete_word`         | `\<C-W>`      | Clear the current typed shorthand
| `delete_character`    | `\<C-H>`      | Delete one character
| `refresh`             | `\<F5>`       | Quit Marksman

# Example Config

You can include the following customization in your .vimrc.  Note that the values below are already set as the default so including this same code would have no effect:

```viml
" You might want to experiment with this order to see for yourself which one is fastest
" 'custom' will try and use g:Mm_CustomSearchCommand if it is set (see below)
let g:Mm_SearchPreferenceOrder = ['custom', 'git', 'hg', 'rg', 'pt', 'ag', 'find', 'python']

" Add patterns for directories that you do not want Marksman to traverse for files
" For example:
" let g:Mm_IgnoreDirectoryPatterns = ['bin', 'obj', '*temp*', '.git']
let g:Mm_IgnoreDirectoryPatterns = []

" Add patterns for files that you do not want to be included in the Marksman list
" For example:
" let g:Mm_IgnoreFilePatterns = ['*.pyc', '*.bin', '*.zip']
let g:Mm_IgnoreFilePatterns = []

" Override the default key mappings to control the Marksman window
" Note that you only need to include the ones you want to override.  If a given action is
" not specified it will use the defaults listed here
let g:Mm_KeyMaps = {
    \ 'exit': "\<esc>",
    \ 'open': "\<enter>",
    \ 'scroll_left': "[",
    \ 'scroll_right': "]",
    \ 'delete_word': "\<c-w>",
    \ 'delete_character': "\<c-h>",
    \ 'refresh': "\<F5>",
    \ }

" When set to 1, you will see files like '.gitignore', '.vimrc' or folders like '.config', '.git', etc.
" Note that you can also set this to true and then add special cases to the g:Mm_IgnorePatterns list
let g:Mm_ShowHidden = 0

" When set to 1, directories that are symbolic links will be traversed
let g:Mm_FollowLinks = 0

" You can also optionally supply your own external command to use to get the list of files
" It will just need to return a newline seperated list of absolute paths
" Note that when Mm_CustomSearchCommand is set, Mm_SearchPreferenceOrder, Mm_FollowLinks, 
" Mm_IgnoreDirectoryPatterns, and Mm_IgnoreFilePatterns settings are ignored
" Also note that it will only run based on where 'custom' is in g:Mm_SearchPreferenceOrder
" let g:Mm_CustomSearchCommand = 'my/custom/file_search.exe'
```

# Credits

A lot of things for this plugin were shamelessly stolen from [Leaderf](https://github.com/Yggdroot/LeaderF) (thanks @Yggdroot)

