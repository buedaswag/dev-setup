# Oh My Zsh + Powerlevel10k. Sourced from .zshrc; does nothing if omz isn't installed.
#
# Split out because it is ~100 lines of framework boilerplate, most of it omz's own
# commented-out defaults, and it was burying the dozen lines that are actually mine.
#
# The guard matters on a fresh machine: `source $ZSH/oh-my-zsh.sh` against a missing
# install fails the whole .zshrc, and a shell that will not start is a bad first five
# minutes on a new laptop. Install omz and the settings apply themselves.

export ZSH="$HOME/.oh-my-zsh"

# Not installed yet: leave the shell alone rather than breaking it.
[[ -d "$ZSH" ]] || return 0

# Powerlevel10k instant prompt. Must stay near the top, before anything that writes
# to the console -- password prompts and [y/n] confirmations have to come first.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

ZSH_THEME="powerlevel10k/powerlevel10k"

# Too many plugins slow down shell startup, so this stays short.
plugins=( git zsh-syntax-highlighting zsh-autosuggestions )

source "$ZSH/oh-my-zsh.sh"

# Prompt config: `p10k configure` writes ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

############################################################
# omz options I'm not using, kept for reference
############################################################
# ZSH_THEME="random"                    # random theme each load; echo $RANDOM_THEME
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )
# CASE_SENSITIVE="true"
# HYPHEN_INSENSITIVE="true"             # needs CASE_SENSITIVE off
# zstyle ':omz:update' mode disabled    # or: auto, reminder
# zstyle ':omz:update' frequency 13     # days
# DISABLE_MAGIC_FUNCTIONS="true"        # if pasting URLs gets mangled
# DISABLE_LS_COLORS="true"
# DISABLE_AUTO_TITLE="true"
# ENABLE_CORRECTION="true"
# COMPLETION_WAITING_DOTS="true"        # breaks multiline prompts on zsh < 5.7.1
# DISABLE_UNTRACKED_FILES_DIRTY="true"  # much faster status in large repos
# HIST_STAMPS="mm/dd/yyyy"              # or dd.mm.yyyy, yyyy-mm-dd, strftime format
# ZSH_CUSTOM=/path/to/new-custom-folder
