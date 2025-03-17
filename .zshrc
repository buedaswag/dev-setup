# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="powerlevel10k/powerlevel10k"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git docker zsh-autosuggestions zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

############################################################
# ADDED BY MIG
############################################################

# tfenv
export PATH="$HOME/.tfenv/bin:$PATH"

###### BEGIN PYTHON VIRTUAL ENVIRONMENTS

export WORKON_HOME=~/.virtualenvs

function workon() {
    source $WORKON_HOME/$1/bin/activate;
}
function lsvenv() {
    ls -la $WORKON_HOME
}
function rmvenv() {
    rm -r $WORKON_HOME/$1
}

# python 3.10 venv
function mkvenv310() {
    python3.10 -m venv $WORKON_HOME/$1
}
function mkvenvp310() {
    mkvenv310 $1 && workon $1 && pip3.10 install -U pip setuptools wheel
}
function mkvenvr310() {
    mkvenvp310 $1 && pip3.10 install -r requirements.txt
}

# python 3.8 venv
function mkvenv38() {
    python3.8 -m venv $WORKON_HOME/$1
}
function mkvenvp38() {
    mkvenv38 $1 && workon $1 && pip3.8 install -U pip setuptools wheel
}
function mkvenvr38() {
    mkvenvp38 $1 && pip3.8 install -r requirements.txt
}

####### DEFAULT VIRTUAL ENVIRONMENT
workon mig-venv310
export PATH=$PATH:$HOME/bin

alias pythonv='python3 --version'
alias pyv='python3 --version'
alias pipv='pip3 --version'
alias wpy='which python3'
alias wpip='which pip3'

###### END PYTHON VIRTUAL ENVIRONMENTS

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
# https://stackoverflow.com/questions/11180179/postgresql-disable-more-output
echo "\\pset pager off" >> ~/.psqlrc
export PGDATA='/Library/PostgreSQL/15/data'

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
# Aliases
#========

# I'm a bad typist

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
# alias 'c.'='code .'
alias c="cursor"
alias cu="cursor"
alias 'c.'='cursor .'
alias py='python'
alias lvenv='lsvenv'

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
alias ga='git add .'

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

# Short things are better (vscode)
# alias c='code'

# Short things are better (django)
alias pm='python manage.py'

# Just fun
alias fucking=sudo

############################################################
# END Short things are better - https://github.com/nibalizer/bash-tricks/blob/master/bash_tricks.sh
############################################################

# openssl
export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"

export PATH="$HOME/.poetry/bin:$PATH"

############################################################
# gcloud google cloud
############################################################

# source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
# source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"
