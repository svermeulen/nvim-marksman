
if exists('g:Mm_loaded')
	finish
endif
let g:Mm_loaded = 1

augroup Marksman
    autocmd!
    autocmd BufLeave * call marksman#onBufEntered()
augroup END

