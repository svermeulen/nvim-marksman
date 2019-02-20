scriptencoding utf-8

let g:marksmanCandidates = {}
let g:marksmanIsUpdating = {}
let g:marksmanTotalProjectCount = {}

let g:marksmanProgressUpdateInterval = 0.3

let s:progressIndex = 0
let s:lastProgressTime = reltime()

function! s:getNextMatchesStr(candidates, chosenIndex, totalCharCount)
    let maxChars = &columns - a:totalCharCount - 15
    let charCount = 0
    let fullMsg = ''
    let charIndex = -1

    if a:chosenIndex > 0
        let fullMsg .= ' ... '
    else
        let fullMsg .= '     '
    endif

    let firstEntry = 1
    for i in range(a:chosenIndex, len(a:candidates) - 1)
        let candidate = a:candidates[i].name

        let entry = ''
        if !firstEntry
            let entry .= ', '
        endif
        let firstEntry = 0

        let entry .= candidate
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

function! s:InitVar(var, value)
    if !exists(a:var)
        exec 'let '.a:var.'='.string(a:value)
    endif
endfunction

function! s:goToMark(mark)
    exec 'e ' . a:mark.path
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

    let g:marksmanTotalProjectCount[a:projectRootPath] += 1
endfunction

function! s:getAllMatches(projectRootPath, requestId)
    if !has_key(g:marksmanCandidates, a:projectRootPath)
        call s:forceRefresh(a:projectRootPath, 1)
    endif

    let idMap = g:marksmanCandidates[a:projectRootPath]

    return get(idMap, a:requestId, [])
endfunction

function! s:forceRefresh(projectRootPath, useCache)
    let g:marksmanCandidates[a:projectRootPath] = {}
    let g:marksmanTotalProjectCount[a:projectRootPath] = 0
    call MarksmanUpdateCache(a:projectRootPath, a:useCache)
endfunction

function! marksman#run(projectRootPath)
    let projectRootPath = s:canonizePath(a:projectRootPath)

    let requestId = ''
    let candidates = []

    let indent1 = 8
    let indent2 = 20
    let chosenIndex = 0

    while 1
        " Necessary to avoid putting CPU at 100%
        sleep 10m

        let charCount = 0
        let candidates = s:getAllMatches(projectRootPath, requestId)
        redraw
        echon requestId
        echohl Cursor
        echon ' '
        echohl NONE

        let charCount += len(requestId) + 1

        if charCount < indent1
            for i in range(1, indent1 - charCount)
                echon ' '
            endfor
            let charCount = indent1
        endif

        let totalCount = string(g:marksmanTotalProjectCount[projectRootPath])
        echon '(' . totalCount

        let charCount += 1 + len(totalCount)

        if get(g:marksmanIsUpdating, projectRootPath, 0)
            let elapsed = reltimefloat(reltime(s:lastProgressTime))

            if elapsed > g:marksmanProgressUpdateInterval
                let s:progressIndex = float2nr(fmod(s:progressIndex + 1, 3))
                let s:lastProgressTime = reltime()
            endif

            for i in range(0, s:progressIndex)
                echon '.'
                let charCount += 1
            endfor
        endif

        echon ')'
        let charCount += 1

        if charCount < indent2
            for i in range(1, indent2 - charCount)
                echon ' '
            endfor
            let charCount = indent2
        endif

        echon s:getNextMatchesStr(candidates, chosenIndex, charCount)

        let charNo = getchar(1)

        if !type(charNo) && charNo == 0
            continue
        endif

        let charNo = getchar()
        let char = nr2char(charNo)

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

        if charNo ==# "\<f5>"
            call s:forceRefresh(projectRootPath, 0)
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
