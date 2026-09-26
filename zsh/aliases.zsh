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
alias hg='history | grep'
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

# Just fun
alias fucking=sudo

# history grep tail
hgt() {
  if [ -z "$1" ]; then
    echo "Error: Missing search string argument"
    return 1
  fi

  local search_string="$1"
  local tail_count=${2:-10}
  history | grep "$search_string" | tail -n "$tail_count"
}
