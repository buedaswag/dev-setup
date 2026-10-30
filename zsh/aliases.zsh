# Aliases and the small shortcuts that are really aliases with an argument.
# Sourced from .zshrc.
#
# Short things are better — https://github.com/nibalizer/bash-tricks/blob/master/bash_tricks.sh

# I'm a bad typist
alias l='ls -la'
alias sl=ls
alias mdkir=mkdir
alias soruce=source
alias souce=source

# Short things are better
alias v=vagrant
alias g=git
alias d=docker
alias j='jupyter notebook'
alias jn='jupyter notebook'
alias tf='terraform'
alias k='kubectl'
alias pm='python manage.py'

# cursor
alias c="cursor"
alias cu="cursor"
alias 'c.'='cursor .'

# git
git config --global alias.c checkout
git config --global alias.b branch
git config --global alias.s status
alias gs='git status'
alias sg='git status'
alias ga='git add'
alias gaa='git add .'
alias ga.='git add .'
alias gb="git branch"
alias gd='git diff'

# gc "message" [flags], or gc [flags] "message" -- e.g. gc "fix typo" -a, gc --amend "reworded".
# Replaces omz's gc (git commit --verbose); the alias has to go before the function can be defined.
unalias gc 2>/dev/null
gc() {
    if [[ $1 == -* ]]; then
        git commit -m "${@[-1]}" "${@[1,-2]}"
    else
        git commit -m "$1" "${@:2}"
    fi
}

# gp [flags] -- push the current branch to origin, upstream or not. Replaces omz's gp (git push).
unalias gp 2>/dev/null
gp() { git push origin "$(git branch --show-current)" "$@" }

# gpull [flags] -- pull the current branch from origin, upstream or not.
gpull() { git pull origin "$(git branch --show-current)" "$@" }

# Just fun
alias fucking=sudo

# hg [-n N] word [word...] -- the commands I ran: lines whose command (alias expanded) is one of the
# words and that contain every word, any order, any case. No such line: every word, anywhere.
# Plain, deduplicated, newest last; -n N keeps the latest N. At a terminal, pick a number and
# it lands on the next prompt.
# e.g. hg terraform finds "terraform login x" and "tf plan", not "mkdir terraform".
unalias hg 2>/dev/null
hg() {
  local -a limit
  zparseopts -D -F -- n:=limit || return 2
  [[ -z $limit || $limit[2] == <1-> ]] || { print -u2 "hg: -n wants a positive number"; return 2 }
  (( $# )) || { print -u2 "usage: hg [-n N] word [word...]"; return 2 }
  local line expanded cmd word i pick
  local -a words commands anywhere matches
  local -A seen
  words=(${(L)@})
  for line in ${(f)"$(builtin fc -ln 1)"}; do
    line=${line%\\n}
    cmd=${line%% *}
    expanded=$line
    [[ -n ${aliases[$cmd]} ]] && expanded="${aliases[$cmd]}${line#$cmd}"
    # Typed and expanded both count: hg tf and hg terraform each find "tf plan".
    for word in $words; do
      [[ ${(L)line} == *"$word"* || ${(L)expanded} == *"$word"* ]] || continue 2
    done
    anywhere+=("$line")
    (( ${words[(Ie)${(L)cmd}]} || ${words[(Ie)${(L)${expanded%% *}}]} )) && commands+=("$line")
  done
  (( $#commands )) || commands=("${anywhere[@]}")
  # Newest first so the latest copy of a repeat is the one kept, then back to oldest first.
  for (( i = $#commands; i > 0; i-- )); do
    (( ${+seen[${commands[i]}]} )) && continue
    seen[${commands[i]}]=1
    matches=("${commands[i]}" "${matches[@]}")
  done
  (( $#matches )) || return 1
  (( $#limit && limit[2] < $#matches )) && matches=("${(@)matches[-${limit[2]},-1]}")
  if [[ ! -t 0 || ! -t 1 ]]; then
    print -rl -- "${matches[@]}"
    return
  fi
  for (( i = 1; i <= $#matches; i++ )); do
    print -r -- "$i) ${matches[i]}"
  done
  read -r "pick?Pick a number to put it on the prompt (Enter to quit): " || return 0
  [[ $pick == <1-> && $pick -le $#matches ]] && print -z -- "${matches[pick]}"
  return 0
}
