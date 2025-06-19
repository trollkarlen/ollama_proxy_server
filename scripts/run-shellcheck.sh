#!/usr/bin/env bash

# shellcheck disable=SC2034
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

[[ -n "$DEBUG" ]] && set -x

set -Euo pipefail
set -e

FAIL=0

if ! command -v shellcheck >/dev/null; then
   >&2 echo "shellcheck not installed or on path, please install"
   exit 43
fi

# newline as field separator
while read -d $'\n' -r value || [ -n "$value" ]
do
    printf 'checking file "%s":\n' "$value"
    if ! shellcheck "$value"; then
        FAIL=$((FAIL+1))
    fi
done <<<"$(git ls-files | grep -E "\.sh$|\.bash")"
# < for file instead and <<'EOF' for eof input
exit $FAIL
