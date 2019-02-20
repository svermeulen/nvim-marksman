scriptencoding utf-8

let g:marksmanCandidates = {}
let g:marksmanIsUpdating = {}

let g:marksmanProgressUpdateInterval = 0.3

let s:progressIndex = 0
let s:lastProgressTime = reltime()

function! s:InitVar(var, value)
    if !exists(a:var)
        exec 'let '.a:var.'='.string(a:value)
    endif
endfunction

call s:InitVar('g:Mm_CacheDirectory', $HOME)
call s:InitVar('g:Mm_NeedCacheTime', '1.5')
call s:InitVar('g:Mm_NumberOfCache', 5)
call s:InitVar('g:Mm_UseMemoryCache', 1)
call s:InitVar('g:Mm_IndexTimeLimit', 120)
call s:InitVar('g:Mm_FollowLinks', 0)
call s:InitVar('g:Mm_WildIgnore', {
            \ 'dir': [],
            \ 'file': []
            \})
call s:InitVar('g:Mm_UseVersionControlTool', 1)
call s:InitVar('g:Mm_UseCache', 1)
call s:InitVar('g:Mm_WorkingDirectory', '')
call s:InitVar('g:Mm_ShowHidden', 0)

function! s:getNextMatchesStr(candidates, chosenIndex)
    let maxChars = 150
    let charCount = 0
    let fullMsg = ''
    let charIndex = -1

    if a:chosenIndex > 0
        let fullMsg .= '... >'
    else
        let fullMsg .= '    >'
    endif

    for i in range(a:chosenIndex, len(a:candidates) - 1)
        let candidate = a:candidates[i].name

        let entry = candidate . ' | '
        let entryLength = strlen(entry)

        if charCount + entryLength > maxChars
            let fullMsg .= strpart(entry, 0, maxChars - charCount) . ' ...'
            break
        endif

        let fullMsg .= entry
        let charCount += entryLength
    endfor

    return fullMsg
endfunction

function! s:goToMark(mark)
    echom 'Chose ' . a:mark.name
endfunction

function! s:canonizePath(path)
    " Use forward slashes, simplify use of ellipses etc., and then lower case everything
    let path = tolower(simplify(substitute(a:path, '\\', '/', 'g')))

    " Capitalize the first letter if it's an absolute path
    return substitute(path, '\v^([A-Za-z]):', '\U\1:', '')
endfunction

function! g:MarksmanAddMarks(projectRootPath, id, candidate)
    let idMap = g:marksmanCandidates[a:projectRootPath]

    if !has_key(idMap, a:id)
        let idMap[a:id] = []
    endif

    call add(idMap[a:id], a:candidate)
endfunction

function! s:getAllMatches(projectRootPath, requestId)
    if !has_key(g:marksmanCandidates, a:projectRootPath)
        let g:marksmanCandidates[a:projectRootPath] = {}
        call MarksmanUpdateCache(a:projectRootPath)
    endif

    let idMap = g:marksmanCandidates[a:projectRootPath]

    return get(idMap, a:requestId, [])
endfunction

function! marksman#run(projectRootPath)
    let projectRootPath = s:canonizePath(a:projectRootPath)

    let requestId = ''
    let candidates = []

    let indent = 8
    let chosenIndex = 0

    while 1
        " Necessary to avoid putting CPU at 100%
        sleep 10m

        let candidates = s:getAllMatches(projectRootPath, requestId)
        redraw
        echon requestId
        echohl Cursor
        echon ' '
        echohl NONE
        for i in range(0, max([0, indent - len(requestId)]))
            echon ' '
        endfor
        echon s:getNextMatchesStr(candidates, chosenIndex)

        if get(g:marksmanIsUpdating, projectRootPath, 0)
            let elapsed = reltimefloat(reltime(s:lastProgressTime))

            if elapsed > g:marksmanProgressUpdateInterval
                let s:progressIndex = float2nr(fmod(s:progressIndex + 1, 3))
                let s:lastProgressTime = reltime()
            endif

            echon ' Searching'

            for i in range(0, s:progressIndex)
                echon '.'
            endfor
        endif

        let charNo = getchar(1)

        if !type(charNo) && charNo == 0
            continue
        endif

        let char = nr2char(getchar())

        if char ==# ''
            redraw
            echo
            break
        endif

        if char ==# ''
            if chosenIndex < len(candidates) - 1
                let chosenIndex += 1
            endif
            continue
        endif

        if charNo ==# "\<c-f7>"
            let requestId = strpart(requestId, 0, strlen(requestId)-1)
            continue
        endif

        if char ==# ''
            let requestId = ''
            continue
        endif

        if char ==# ''
            if chosenIndex > 0
                let chosenIndex -= 1
            endif

            continue
        endif

        if char ==# ''
            redraw
            echo
            if !empty(candidates)
                call s:goToMark(candidates[chosenIndex])
            endif

            break
        endif

        let requestId = requestId . char
    endwhile
endfunction
