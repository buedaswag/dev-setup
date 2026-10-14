# Functions with real bodies. Sourced from .zshrc.
#
# The one-liners live in aliases.zsh; these are long enough to read as code.

# Open Cursor on a path, or bare. Wraps `open -a` so a relative path still lands.
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

# az login as a service principal, reading the env file for that environment.
# Credentials live outside this repo, in ~/ws/notes, and stay there.
function azlogin {
    local env="$1"
    az logout
    set -a
    . ~/ws/notes/credentials/azure.$env.env
    set +a
    az login --service-principal -u $ARM_CLIENT_ID -p $ARM_CLIENT_SECRET --tenant $ARM_TENANT_ID
}

# Delete terraform local state and plan files, recursively.
function tfcleanup() {
    find . -name "planfile" -type f -delete
    find . -name ".terraform.*" -type f -delete
    find . -name "terraform.*" -type f -delete
    find . -name ".terraform" -type d -exec rm -rf {} +
    find . -name "terraform.tfstate.d" -type d -exec rm -rf {} +
}

# git add + commit, message built from the first 10 changed paths.
gac() {
    # Get the list of modified files (first 10 files)
    modified_files=$(git status -s | head -n 10 | awk '{print $2}')

    # Combine modified files into a commit message
    if [[ -z "$modified_files" ]]; then
        echo "No changes to commit."
        return 1
    fi
    commit_message="Modified files: $(echo "$modified_files" | tr '\n' ',' | sed 's/,$//; s/,/, /g')"

    # Add all changes
    git add .

    # Commit with the list of modified files as the message
    git commit -m "$commit_message"
}

# gac, then gp (aliases.zsh): push the current branch to origin.
gacp() {
    gac && gp
}
