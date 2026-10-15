#!/bin/bash
#
# Check the Terraform code in one directory.
# Used by the 'validate' task in Taskfile.yml, once per directory.
#
# 1. 'terraform init' without a backend, to download providers and modules.
#    If a module comes from the private registry and we are not logged in,
#    SKIP this directory: we cannot fix that here.
# 2. 'terraform validate'.
# 3. 'terraform test', only if the directory has tests (*.tftest.hcl here or in tests/).
#    If the tests fail only because there are no cloud credentials,
#    print a message and carry on: that is not a problem with the code.
#
# Exit code: 0 if everything passed or was skipped, 1 if something failed.
#
# Usage: ./scripts/check-terraform-dir.sh <directory>

DIR="$1"

# The error 'terraform init' prints when registry login is missing.
# Check a real CI log once and adjust this if the wording differs.
REGISTRY_LOGIN_ERROR="401 Unauthorized"

# Errors that mean "no cloud credentials", not "broken code".
# Check a real CI log once and add the wording you see there.
MISSING_CREDENTIALS_ERRORS=(
  "could not find default credentials"
  "Attempted to load application default credentials"
  "oauth2: cannot fetch token"
)

if [ -z "$DIR" ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi


# Does this directory have Terraform tests?
has_tests() {
  compgen -G "$DIR/*.tftest.hcl" > /dev/null ||
    compgen -G "$DIR/tests/*.tftest.hcl" > /dev/null
}

# Did this output fail only because cloud credentials are missing?
is_missing_credentials() {
  local output="$1"
  local error
  for error in "${MISSING_CREDENTIALS_ERRORS[@]}"; do
    if grep -qi "$error" <<< "$output"; then
      return 0
    fi
  done
  return 1
}


echo "==> $DIR"

# Step 1: init. Keep the output, we only show it if something goes wrong.
if ! init_output=$(terraform -chdir="$DIR" init -backend=false -input=false 2>&1); then

  if grep -q "$REGISTRY_LOGIN_ERROR" <<< "$init_output"; then
    echo "    SKIPPED: uses a module from the private registry, which needs a login."
    exit 0
  fi

  echo "$init_output"
  echo "    FAILED: terraform init"
  exit 1
fi

# Step 2: validate.
if ! terraform -chdir="$DIR" validate; then
  echo "    FAILED: terraform validate"
  exit 1
fi
echo "    OK: validate"

# Step 3: test, only where there are tests.
if ! has_tests; then
  exit 0
fi

if test_output=$(terraform -chdir="$DIR" test 2>&1); then
  echo "$test_output"
  echo "    OK: test"
  exit 0
fi

if is_missing_credentials "$test_output"; then
  echo "    SKIPPED: tests need cloud credentials, which this run does not have."
  exit 0
fi

echo "$test_output"
echo "    FAILED: terraform test"
exit 1
