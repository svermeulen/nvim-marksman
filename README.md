
<img align="right" width="281" height="284" src="https://i.imgur.com/etJCqp2.png">

# Marksman.vim

Marksman is a file finder.  However, it is not a fuzzy file finder like [CtrlP](https://github.com/kien/ctrlp.vim), [Leaderf](https://github.com/Yggdroot/LeaderF), or [Fzf](https://github.com/junegunn/fzf.vim).  Unlike these tools, with Marksman each file has a generated shorthand that is derived from the file name that you have to type exactly in order to go to the file.

This shorthand is chosen based on the 'humps' in the file name (ie. when the case changes or an underscore is encountered).  For example, the file "FooBar.py" has a shorthand 'fb'.  So in order to select this file you would execute Marksman, then type 'fb' then press enter.

# Installation

If using [vim-plug](https://github.com/junegunn/vim-plug) then you can install with the following line:

```
Plug 'svermeulen/nvim-marksman', { 'do': ':UpdateRemotePlugins' }
```

# Usage

To run, execute the command `:Marksman`.  By default this will run in the current working directly.  You can also specify the directory explicitly, for example by running `:Marksman C:/Foo/Bar`.

When it is initially run it will asynchronously populate the list of files by scanning the given directory.  It will attempt to use external commands such as [rg](https://github.com/BurntSushi/ripgrep), [ag](https://github.com/ggreer/the_silver_searcher), `pt`, and `find`, or if none of those can be found then it will just directly search inside python.

Once it has started populating the list of the files, you can start typing the humps of the file that you are looking for.  In some cases there might be multiple matches, in which case you can cycle between the list by pressing `<c-l>` or `<c-h>` (note that this is also configurable below).  Once you have found the file you are looking for, press enter to open it.

Note that Marksman will try to choose an intelligent order to present the files in.  By default this will be chosen based on the file modification time and also the last time the file was opened in vim (whichever is more recent)

Note also that Marksman will cache the results in memory, so if you add files during your vim session you need to force refresh Marksman by pressing `<F5>` in order for the new files to show up.

# Keys

* `<esc>` - Cancel Marksman
* `<enter>` - Open the selected file
* `<c-w>` - Clear the current typed shorthand
* `<c-h>` - Delete one character
* `]` - Cycle the list forward
* `[` - Cycle the list backwards
* `<F5>` - Re-scan the file system

# Options

# Options

TBD

# Credits

The code to do the async search in python was shamelessly stolen from [Leaderf](https://github.com/Yggdroot/LeaderF) (thanks @Yggdroot)

