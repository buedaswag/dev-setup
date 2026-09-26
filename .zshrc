# ~/.zshrc — copy this one file into place on a new machine:
#
#     cp ~/ws/dev-setup/.zshrc ~/.zshrc
#
# That is the whole install. Everything with a body lives in zsh/ and is sourced from
# there, so this file is a table of contents and nothing else — which is why one `cp`
# is enough and why it rarely needs doing again.
#
# oh-my-zsh comes first: it owns the prompt and has to run before anything prints.

source ~/ws/dev-setup/zsh/oh-my-zsh.zsh   # framework + prompt; no-op if omz is absent
source ~/ws/dev-setup/zsh/paths.zsh       # PATH and tool environment
source ~/ws/dev-setup/zsh/aliases.zsh     # aliases and one-liners
source ~/ws/dev-setup/zsh/functions.zsh   # cursor, azlogin, tfcleanup, gac, gacp
