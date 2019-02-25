scriptencoding utf-8

let s:progressIndex = 0
let s:lastProgressTime = reltime()

function! s:getMatchListString(candidates, hasMorePrevious, maxLength)
    let fullMsg = ''
    let charIndex = -1

    if a:hasMorePrevious
        let fullMsg .= '< '
    endif

    let maxLength = a:maxLength - 2

    let firstEntry = 1
    for candidate in a:candidates
        let entry = ''
        if !firstEntry
            let entry .= ', '
        endif
        let firstEntry = 0

        let entry .= candidate.name

        if strlen(fullMsg) + strlen(entry) >= maxLength
            let fullMsg .= strpart(entry, 0, maxLength - strlen(fullMsg)) . ' >'
            break
        endif

        let fullMsg .= entry
    endfor

    return fullMsg
endfunction

function! s:clearEcho()
    redraw
    for i in range(1, &cmdheight)
        echo
    endfor
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

function! s:assert(condition, message)
    if !a:condition
        throw "vim-marksman: Assert hit: " . a:message
    endif
endfunction

function! s:addPadding(numSpaces)
    let message = ''

    if a:numSpaces > 0
        for i in range(1, a:numSpaces)
            let message .= ' '
        endfor
    endif

    return message
endfunction

function! marksman#run(...)
    let projectRootPath = len(a:000) ? a:1 : getcwd()
    let requestId = len(a:000) > 1 ? a:2 : ''
    let offset = len(a:000) > 2 ? a:3 : 0

    let pageSize = 15
    let leftIndent = 10
    let rightIndent = 15
    let currentPath = expand('%:p')

    while 1
        " Necessary to avoid putting CPU at 100%
        sleep 10m

        let result = MarksmanUpdateSearch(projectRootPath, requestId, offset, pageSize, currentPath)
        let offset = max([0, min([offset, result.matchesCount - 1])])

        redraw
        " echo ''
        echon strpart(requestId, 0, leftIndent)
        echohl Cursor
        echon ' '
        echohl NONE

        " Keep the same indent regardless of the size of request id
        echon s:addPadding(leftIndent - strlen(requestId))

        let message = ''

        let footerStart = &columns - rightIndent - leftIndent
        let progressLength = 4

        let maxMatchesStrLen = footerStart - leftIndent - progressLength
        let matchesStr = s:getMatchListString(result.matches, offset > 0, maxMatchesStrLen)
        let matchesStrLen = strlen(matchesStr)

        call s:assert(matchesStrLen <= maxMatchesStrLen, string(matchesStrLen) . " <= " . string(maxMatchesStrLen))

        let message .= matchesStr
        let message .= s:addPadding(matchesStrLen - maxMatchesStrLen)

        if result.isUpdating
            let elapsed = reltimefloat(reltime(s:lastProgressTime))

            if elapsed > g:Mm_ProgressUpdateInterval
                let s:progressIndex = float2nr(fmod(s:progressIndex + 1, 3))
                let s:lastProgressTime = reltime()
            endif

            let message .= ' '
            for i in range(0, s:progressIndex)
                let message .= '.'
            endfor
        endif

        let message .= s:addPadding(footerStart - strlen(message))

        let footer = string(result.matchesCount) . '/' . string(result.totalCount)

        let message .= footer
        echon message

        " for debugging
        " echon s:addPadding(rightIndent - strlen(footer) - 3) . '|'

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

        if charNo ==# "\<f5>"
            call MarksmanForceRefresh(projectRootPath)
            continue
        endif

        if char ==# ''
            let requestId = strpart(requestId, 0, strlen(requestId)-1)
            continue
        endif

        if char ==# ''
            let requestId = ''
            continue
        endif

        if char ==# ']'
            if offset < result.matchesCount - 1
                let offset += 1
            endif
            continue
        endif

        if char ==# '['
            if offset > 0
                let offset -= 1
            endif
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

function! s:InitVar(var, value)
    if !exists(a:var)
        exec 'let '.a:var.'='.string(a:value)
    endif
endfunction

call s:InitVar('g:Mm_FollowLinks', 0)
call s:InitVar('g:Mm_WildIgnore', {
            \ 'dir': [],
            \ 'file': []
            \})
call s:InitVar('g:Mm_ShowHidden', 0)
call s:InitVar('g:Mm_ProgressUpdateInterval', 0.25)
call s:InitVar('g:Mm_SearchPreferenceOrder', ['git', 'hg', 'rg', 'pt', 'ag', 'find', 'python'])

command! -nargs=? Marksman call marksman#run(<q-args>)

