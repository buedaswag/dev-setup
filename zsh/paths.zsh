# PATH and tool environment. Sourced from .zshrc.
#
# Order matters: homebrew first, because later lines assume `brew` resolves.

# homebrew
eval "$(/opt/homebrew/bin/brew shellenv zsh)"

# tfenv
export PATH="$HOME/.tfenv/bin:$PATH"

# python venvs
source ~/ws/dev-setup/zsh/py-venvs.sh

# vscode
export PATH="$PATH:/Applications/Visual Studio Code.app/Contents/Resources/app/bin"

# cursor
export PATH="$PATH:/Applications/Cursor.app/Contents/Resources/app/bin/cursor"

# psql postgres
export PATH=/Library/PostgreSQL/15/bin:$PATH
export PGDATA='/Library/PostgreSQL/15/data'
# Turn the pager off so psql output doesn't open in `less`. Guarded: unguarded, this
# appends on every shell start, and ~/.psqlrc grew to 2769 copies of one line.
# https://stackoverflow.com/questions/11180179/postgresql-disable-more-output
grep -qs 'pset pager off' ~/.psqlrc || echo "\\pset pager off" >> ~/.psqlrc

# openssl
export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"

# poetry
export PATH="$HOME/.poetry/bin:$PATH"

# gcloud google cloud
# source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
# source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"
