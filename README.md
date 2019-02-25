
<img align="right" width="281" height="284" src="https://i.imgur.com/etJCqp2.png">

# Marksman.vim

Marksman is a file finder.  However, it is not a fuzzy finder like CtrlP, Leaderf, or Fzf.  Each file has a shorthand that is derived from the file name that you have to type exactly in order to go to the file.

This shorthand is chosen based on the 'humps' in the file name (ie. when the case changes or an underscore is encountered).  For example, the file "FooBar.py" has a shorthand 'fb'.  So in order to select this file you would execute Marksman, then type 'fb' then press enter.

To run, execute the command `:Marksman`.  By default this will run in the current working directly.  You can also specify the directory explicitly, for example by running `:Marksman C:/Foo/Bar`.

When it is initially run it will asynchronously populate the list of files by scanning the given directory.  It will attempt to use external commands such as rg, ag, pt, and find, or if none of those can be found then it will just directly search using python methods.

Once it has started populating the list of the files, you can start typing the humps of the file that you are looking for.  In some cases there might be multiple matches, in which case you can cycle between the list by pressing `<c-l>` or `<c-h>`.  Once you have found the file you are looking for, press enter to open it.

Note that Marksman will try to choose an intelligent order to present the files in.  By default this will be chosen based on the file modification time and also the last time the file was opened in vim (whichever is more recent)

