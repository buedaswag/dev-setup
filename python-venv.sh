#!/usr/bin/env zsh
# Python virtual environment management functions
# Source this from .zshrc: source ~/ws/python-venv.sh

export WORKON_HOME=~/.virtualenvs

# Resolve a brew-installed Python binary by version (e.g., 3.13, 3.14)
# Returns the full path to the python3.X binary, or falls back to default python3
function _resolve_python() {
    local version="$1"
    if [[ -z "$version" ]]; then
        # Find the latest brew-installed Python version
        local latest=$(ls -d /opt/homebrew/opt/python@3.*/bin/python3.* 2>/dev/null \
            | grep -v config \
            | sort -t. -k2 -n \
            | tail -1)
        if [[ -n "$latest" ]]; then
            echo "$latest"
        else
            echo "python3"
        fi
    else
        local pybin="/opt/homebrew/opt/python@${version}/bin/python${version}"
        if [[ -x "$pybin" ]]; then
            echo "$pybin"
        else
            echo "Error: Python ${version} not found. Run 'lspy' to see available versions." >&2
            return 1
        fi
    fi
}

# List all brew-installed Python versions
function lspy() {
    echo "Brew-installed Python versions:"
    for pydir in /opt/homebrew/opt/python@3.*/; do
        local ver=$(basename "$pydir" | sed 's/python@//')
        local pybin="${pydir}bin/python${ver}"
        if [[ -x "$pybin" ]]; then
            echo "  ${ver}  ->  $($pybin --version 2>&1)"
        fi
    done
    echo ""
    echo "Default python3: $(python3 --version 2>&1) ($(which python3))"
}

# Resolve a venv name: accepts "name" or "name@version"
# If bare name, looks for name@* in WORKON_HOME
function _resolve_venv() {
    local name="$1"
    # If exact match exists (e.g., user passed "myenv@3.13"), use it
    if [[ -d "$WORKON_HOME/$name" ]]; then
        echo "$name"
        return 0
    fi
    # Try to find name@* match
    local matches=("$WORKON_HOME/${name}@"*(N/))
    if [[ ${#matches[@]} -eq 0 ]]; then
        echo "Error: Virtual environment '$name' not found. Run 'lsvenv' to see available envs." >&2
        return 1
    elif [[ ${#matches[@]} -gt 1 ]]; then
        echo "Error: Multiple matches for '$name':" >&2
        for m in "${matches[@]}"; do echo "  $(basename "$m")" >&2; done
        echo "Specify the full name (e.g., ${name}@version)." >&2
        return 1
    fi
    echo "$(basename "${matches[1]}")"
}

function workon() {
    if [[ -z "$1" ]]; then
        echo "Usage: workon <venv-name>"
        return 1
    fi
    local resolved
    resolved=$(_resolve_venv "$1") || return 1
    source "$WORKON_HOME/$resolved/bin/activate"
}

function lsvenv() {
    echo "Virtual environments in $WORKON_HOME:"
    for venv in "$WORKON_HOME"/*/; do
        local name=$(basename "$venv")
        local pyver=$("$venv/bin/python3" --version 2>/dev/null || echo "unknown")
        echo "  ${name}  (${pyver})"
    done
}

function rmvenv() {
    if [[ -z "$1" ]]; then
        echo "Usage: rmvenv <venv-name>"
        return 1
    fi
    local resolved
    resolved=$(_resolve_venv "$1") || return 1
    rm -r "$WORKON_HOME/$resolved"
    echo "Removed virtual environment '$resolved'"
}

# Create a venv with an optional Python version
# Usage: mkvenv <name> [python-version]
# Examples: mkvenv myenv         (uses latest brew Python)
#           mkvenv myenv 3.13    (uses Python 3.13)
function mkvenv() {
    if [[ -z "$1" ]]; then
        echo "Usage: mkvenv <name> [python-version]"
        echo "  e.g. mkvenv myenv        # latest Python"
        echo "  e.g. mkvenv myenv 3.13   # specific version"
        echo ""
        echo "Run 'lspy' to see available Python versions."
        return 1
    fi
    local pybin
    pybin=$(_resolve_python "$2") || return 1
    local pyver
    pyver=$("$pybin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local venv_name="${1}@${pyver}"
    echo "Creating venv '$venv_name' with $($pybin --version 2>&1)..."
    "$pybin" -m venv "$WORKON_HOME/$venv_name"
}

function mkvenvp() {
    mkvenv "$1" "$2" && workon "$1" && pip install -U pip setuptools wheel
}
function mkvenvr() {
    mkvenvp "$1" "$2" && pip install -r requirements.txt
}

####### DEFAULT VIRTUAL ENVIRONMENT
workon mig-venv 2>/dev/null
export PATH=$PATH:$HOME/bin

alias pythonv='python3 --version'
alias pyv='python3 --version'
alias pipv='pip3 --version'
alias lvenv='lsvenv'
alias py='python'
alias wpy='which python3'
alias wpip='which pip3'
