# ~/.zshrc — copy this one file into place on a new machine:
#
#     cp ~/ws/dev-setup/zsh/.zshrc ~/.zshrc
#
# That is the whole install. Everything with a body sits beside this file and is
# sourced from there, so this is a table of contents and nothing else — which is why
# one `cp` is enough and why it rarely needs doing again.
#
# Listed one by one rather than globbed: oh-my-zsh owns the prompt and has to run
# before anything prints, and `zsh/*.zsh` would sort aliases.zsh ahead of it.

source ~/ws/dev-setup/zsh/oh-my-zsh.zsh   # framework + prompt; no-op if omz is absent
source ~/ws/dev-setup/zsh/paths.zsh       # PATH and tool environment
source ~/ws/dev-setup/zsh/aliases.zsh     # aliases and one-liners
source ~/ws/dev-setup/zsh/functions.zsh   # cursor, azlogin, tfcleanup, gac, gacp
