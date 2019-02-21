scriptencoding utf-8

let s:candidates = {}
let s:isUpdating = {}
let s:totalProjectCount = {}
let s:progressIndex = 0
let s:lastProgressTime = reltime()
let s:lastOpenTime = {}

function! s:getNextMatchesStr(candidates, chosenIndex, totalCharCount)
    let maxChars = &columns - a:totalCharCount - 15
    let charCount = 0
    let fullMsg = ''
    let charIndex = -1

    if a:chosenIndex > 0
        let fullMsg .= '... '
        let charCount += 4
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

function! marksman#getCanonicalPath(path)
    " Use forward slashes, simplify use of ellipses etc., and then lower case everything
    let path = tolower(simplify(substitute(a:path, '\\', '/', 'g')))

    " Capitalize the first letter if it's an absolute path
    return substitute(path, '\v^([A-Za-z]):', '\U\1:', '')
endfunction

function! marksman#markProjectInProgress(projectRootPath, inProgress)
    let s:isUpdating[a:projectRootPath] = a:inProgress
endfunction

function! marksman#onBufEntered()
    let path = expand('%:p')

    if len(path) == 0
        return
    endif

    let path = marksman#getCanonicalPath(path)
    let s:lastOpenTime[path] = localtime()
endfunction

function! marksman#addFileMark(projectRootPath, id, candidate)
    if !has_key(s:candidates, a:projectRootPath)
        let s:candidates[a:projectRootPath] = {}
    endif

    let idMap = s:candidates[a:projectRootPath]

    if !has_key(idMap, a:id)
        let idMap[a:id] = []
    endif

    call add(idMap[a:id], a:candidate)

    if !has_key(s:totalProjectCount, a:projectRootPath)
        let s:totalProjectCount[a:projectRootPath] = 0
    endif

    let s:totalProjectCount[a:projectRootPath] += 1
endfunction

function! s:tryGetLastOpenTime(path)
    return get(s:lastOpenTime, a:path, 0)
endfunction

function! s:CompareCandidates(entry1, entry2)
    let time1 = get(s:lastOpenTime, a:entry1.path, -1)
    let time2 = get(s:lastOpenTime, a:entry2.path, -1)

    if time1 == time2
        return 0
    endif

    if time1 < time2
        return 1
    endif

    return -1
endfunction

function! s:getAllMatches(projectRootPath, requestId)
    if !has_key(s:candidates, a:projectRootPath)
        call s:forceRefresh(a:projectRootPath, 0)
    endif

    let idMap = s:candidates[a:projectRootPath]

    return sort(get(idMap, a:requestId, []), 's:CompareCandidates')
endfunction

function! s:clearEcho()
    redraw
    for i in range(1, &cmdheight)
        echo
    endfor
endfunction

function! s:forceRefresh(projectRootPath, updateCache)
    let s:candidates[a:projectRootPath] = {}
    let s:totalProjectCount[a:projectRootPath] = 0
    call MarksmanUpdateCache(a:projectRootPath, a:updateCache)
endfunction

function! marksman#run(projectRootPath)
    let projectRootPath = marksman#getCanonicalPath(a:projectRootPath)

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

        let totalCount = string(s:totalProjectCount[projectRootPath])
        echon '(' . totalCount

        let charCount += 1 + len(totalCount)

        if get(s:isUpdating, projectRootPath, 0)
            let elapsed = reltimefloat(reltime(s:lastProgressTime))

            if elapsed > g:Mm_ProgressUpdateInterval
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
            call s:clearEcho()
            break
        endif

        if char ==# ''
            if chosenIndex < len(candidates) - 1
                let chosenIndex += 1
            endif
            continue
        endif

        if charNo ==# "\<f5>"
            call s:forceRefresh(projectRootPath, 1)
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
            call s:clearEcho()

            if !empty(candidates)
                call s:goToMark(candidates[chosenIndex])
            endif

            break
        endif

        let requestId = requestId . char
    endwhile
endfunction

function! marksman#init()
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
call s:InitVar('g:Mm_ProgressUpdateInterval', 0.1)

