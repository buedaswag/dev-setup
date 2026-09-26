# Oh My Zsh + Powerlevel10k. Sourced from .zshrc; asks only for what is installed.
#
# Split out because it is ~100 lines of framework boilerplate, most of it omz's own
# commented-out defaults, and it was burying the dozen lines that are actually mine.
#
# The guards matter on a fresh machine, where omz, p10k and the custom plugins land
# one at a time. `source $ZSH/oh-my-zsh.sh` against a missing install fails the whole
# .zshrc, and a missing theme or plugin makes omz print "not found" above every
# prompt. Install each piece and its settings apply themselves.
# tests/test_oh_my_zsh.py pins this down.

export ZSH="$HOME/.oh-my-zsh"
ZSH_CUSTOM="${ZSH_CUSTOM:-$ZSH/custom}"

# Not installed (or a leftover, empty dir): leave the shell alone rather than breaking it.
[[ -r "$ZSH/oh-my-zsh.sh" ]] || return 0

# Where omz itself would look: custom first, then bundled.
_omz_has() { [[ -d "$ZSH_CUSTOM/$1" || -d "$ZSH/$1" ]] }

if _omz_has themes/powerlevel10k; then
  # Instant prompt. Must stay near the top, before anything that writes to the
  # console -- password prompts and [y/n] confirmations have to come first.
  if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
    source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
  fi
  ZSH_THEME="powerlevel10k/powerlevel10k"
else
  ZSH_THEME="robbyrussell"
fi

# Too many plugins slow down shell startup, so this stays short.
plugins=()
for _p in git zsh-syntax-highlighting zsh-autosuggestions; do
  _omz_has "plugins/$_p" && plugins+=( "$_p" )
done
unset _p

source "$ZSH/oh-my-zsh.sh"

# Prompt config: `p10k configure` writes ~/.p10k.zsh. Without p10k it is just noise.
[[ "$ZSH_THEME" == powerlevel10k/* && -f ~/.p10k.zsh ]] && source ~/.p10k.zsh
unfunction _omz_has

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
