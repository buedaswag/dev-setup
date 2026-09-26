# My ~/.zshrc. Canonical copy is ~/.zshrc; this is the mirror, committed by hand:
#
#     cp ~/.zshrc ~/ws/dev-setup/.zshrc
#
# Oh My Zsh first: it owns the prompt and has to run before anything prints.
source ~/ws/dev-setup/oh-my-zsh.zsh

# homebrew
eval "$(/opt/homebrew/bin/brew shellenv zsh)"

# tfenv
export PATH="$HOME/.tfenv/bin:$PATH"

# python venvs
source ~/ws/dev-setup/py-venvs.sh

# vscode
export PATH="$PATH:/Applications/Visual Studio Code.app/Contents/Resources/app/bin"

# cursor
export PATH="$PATH:/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
function cursor {
    if [[ $# = 0 ]]
    then
        open -a "Cursor"
    else
        local argPath="$1"
        [[ $1 = /* ]] && argPath="$1" || argPath="$PWD/${1#./}"
        open -a "Cursor" "$argPath"
    fi
}

# psql postgres
export PATH=/Library/PostgreSQL/15/bin:$PATH
export PGDATA='/Library/PostgreSQL/15/data'
# Turn off the pager so psql output doesn't open in `less`.
# https://stackoverflow.com/questions/11180179/postgresql-disable-more-output
grep -qs 'pset pager off' ~/.psqlrc || echo "\\pset pager off" >> ~/.psqlrc

############################################################
# azure shortcuts
############################################################

function azlogin {
    local env="$1"
    az logout
    set -a
    . ~/ws/notes/credentials/azure.$env.env
    set +a
    az login --service-principal -u $ARM_CLIENT_ID -p $ARM_CLIENT_SECRET --tenant $ARM_TENANT_ID
}

############################################################
# terraform shortcuts
############################################################

function tfcleanup() {
    find . -name "planfile" -type f -delete
    find . -name ".terraform.*" -type f -delete
    find . -name "terraform.*" -type f -delete
    find . -name ".terraform" -type d -exec rm -rf {} +
    find . -name "terraform.tfstate.d" -type d -exec rm -rf {} +
}

############################################################
# Short things are better - https://github.com/nibalizer/bash-tricks/blob/master/bash_tricks.sh
############################################################

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
alias c="cursor"
alias cu="cursor"
alias 'c.'='cursor .'

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

# Short things are better (git)
git config --global alias.c checkout
git config --global alias.b branch
git config --global alias.s status
alias gs='git status'
alias sg='git status'
alias ga='git add'
alias gaa='git add .'
alias ga.='git add .'
alias gb="git branch"

# Function to git add, commit
gac() {
    # Get the list of modified files (first 10 files)
    modified_files=$(git status -s | head -n 10 | awk '{print $2}')

    # Combine modified files into a commit message
    if [[ -z "$modified_files" ]]; then
        echo "No changes to commit."
        return 1
    fi
    commit_message="Modified files: $(echo "$modified_files" | tr '\n' ', ' | sed 's/, $//')"

    # Add all changes
    git add .

    # Commit with the list of modified files as the message
    git commit -m "$commit_message"
}

# Function to git add, commit and push in one command
gacp() {
    gac || return 1  # Exit if gac fails

    # Get the current branch
    current_branch=$(git branch --show-current)

    # Ensure we have a valid branch
    if [[ -z "$current_branch" ]]; then
        echo "Could not determine the current branch."
        return 1
    fi

    # Push to the current branch
    git push origin "$current_branch"
}

# Short things are better (kubernetes)
alias k='kubectl'

# Short things are better (django)
alias pm='python manage.py'

# Just fun
alias fucking=sudo

############################################################
# END Short things are better
############################################################

# openssl
export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"

# poetry
export PATH="$HOME/.poetry/bin:$PATH"

# ruby
export PATH="/usr/local/opt/ruby/bin:$PATH"
export LDFLAGS="-L/usr/local/opt/ruby/lib"
export CPPFLAGS="-I/usr/local/opt/ruby/include"

# gcloud google cloud
# source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
# source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"
