#!/bin/bash
#
# Print every directory in the repository that contains Terraform code,
# one per line, sorted. Used by the 'validate' task in Taskfile.yml.
#
# This includes the root module, every module under modules/, and every
# fixture under test/fixtures/. So a module is validated on its own even
# if nothing calls it, and new fixtures are picked up without editing a list.
#
# Skipped: .terraform/ folders (downloaded copies of modules and providers).
#
# Usage: ./scripts/find-terraform-dirs.sh

# Always search from the repository root, wherever this is called from.
cd "$(dirname "$0")/.." || exit 1

# Find all .tf files, ignoring anything inside a .terraform folder...
find . -name ".terraform" -prune -o -name "*.tf" -print |
  # ...keep only the folder each file is in...
  while read -r tf_file; do
    dirname "$tf_file"
  done |
  # ...and list each folder once.
  sort -u
