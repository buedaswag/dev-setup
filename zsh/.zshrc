# ~/.zshrc — on a new machine, make ~/.zshrc a one-line stub that sources this file:
#
#     echo 'source ~/ws/dev-setup/zsh/.zshrc' > ~/.zshrc
#
# That is the whole install, and edits here are live. Not `cp` (every edit would need
# re-copying) and not a symlink (installers that append to ~/.zshrc would write
# machine-specific lines into this public repo); they append to the stub instead.
# Everything with a body sits beside this file and is sourced from there, so this is a
# table of contents and nothing else.
#
# Listed one by one rather than globbed: oh-my-zsh owns the prompt and has to run
# before anything prints, and `zsh/*.zsh` would sort aliases.zsh ahead of it.

source ~/ws/dev-setup/zsh/oh-my-zsh.zsh   # framework + prompt; no-op if omz is absent
source ~/ws/dev-setup/zsh/paths.zsh       # PATH and tool environment
source ~/ws/dev-setup/zsh/aliases.zsh     # aliases and one-liners
source ~/ws/dev-setup/zsh/functions.zsh   # cursor, azlogin, tfcleanup, gac, gacp
source ~/ws/dev-setup/zsh/db-proxy.zsh    # corporate laptop: edge, krenew (myproxy)
