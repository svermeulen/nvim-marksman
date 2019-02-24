scriptencoding utf-8

let s:progressIndex = 0
let s:lastProgressTime = reltime()

function! s:printMatches(candidates, totalCharCount, hasMorePrevious)
    let maxChars = &columns - a:totalCharCount - 15
    let charCount = 0
    let fullMsg = ''
    let charIndex = -1

    if a:hasMorePrevious
        let fullMsg .= '... '
        let charCount += 4
    endif

    let firstEntry = 1
    for candidate in a:candidates
        let entry = ''
        if !firstEntry
            let entry .= ', '
        endif
        let firstEntry = 0

        let entry .= candidate.name
        let entryLength = strlen(entry)

        if charCount + entryLength > maxChars
            let fullMsg .= strpart(entry, 0, maxChars - charCount) . ' ...'
            break
        endif

        let fullMsg .= entry
        let charCount += entryLength
    endfor

    echon fullMsg
endfunction

function! s:clearEcho()
    redraw
    for i in range(1, &cmdheight)
        echo
    endfor
endfunction

function! marksman#runTest()
    let result = MarksmanUpdateSearch('', '', 3)
    echom result.totalCount
endfunction

function! marksman#evalAll(variableNames, evalList)
    let result = {}
    for name in a:variableNames
        if exists(name)
            let result[name] = eval(name)
        else
            let result[name] = v:null
        endif
    endfor
    for value in a:evalList
        let result[value] = eval(value)
    endfor
    return result
endfunction

function! marksman#run(projectRootPath)
    let requestId = ''

    let indent1 = 8
    let indent2 = 20
    let offset = 0
    let maxAmount = 10

    while 1
        " Necessary to avoid putting CPU at 100%
        sleep 10m

        let charCount = 0
        let result = MarksmanUpdateSearch(a:projectRootPath, requestId, offset, maxAmount)

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

        echon '(' . result.totalCount

        let charCount += 1 + len(result.totalCount)

        if result.isUpdating
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

        call s:printMatches(result.matches, charCount, offset > 0)

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
            " if offset < len(candidates) - 1
            "     let chosenIndex += 1
            " endif
            continue
        endif

        if charNo ==# "\<f5>"
            call MarksmanForceRefresh(a:projectRootPath)
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
            " if chosenIndex > 0
            "     let chosenIndex -= 1
            " endif

            continue
        endif

        if char ==# ''
            call s:clearEcho()

            if !empty(result.matches)
                exec 'e ' . result.matches[0].path
            endif

            break
        endif

        let requestId = requestId . char
    endwhile
endfunction

function! marksman#init()
endfunction

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
call s:InitVar('g:Mm_ProgressUpdateInterval', 0.25)

