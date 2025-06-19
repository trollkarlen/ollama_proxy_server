#!/usr/bin/env bash

[[ -n "$DEBUG" ]] && set -x

JWT_KEY="${JWT_KEY:-}"
JWT_KEY_FILE="$HOME/.jwt-key"

set -Euo pipefail
set -e

if [[ -z "$JWT_KEY" ]] || [[ ! -s "$JWT_KEY_FILE" ]]; then
    >&2 echo "No jwt key file or env set creating key and saving in $JWT_KEY_FILE"
    JWT_KEY="$(openssl rand -hex 64)"
    echo -ne "$JWT_KEY" > "$HOME/.jwt-key"
elif [[ -s "$JWT_KEY_FILE" ]]; then
    >&2 echo "found jwt key file '$JWT_KEY_FILE' setting to env"
    JWT_KEY="$(cat "$JWT_KEY_FILE")"
fi

if (( ${#@} )) && [ -t 0 ]; then
    # user whants interactive
    "${@}"
else
    ollama_proxy_server "--config=./config.ini" "--users_list=./authorized_users.txt" "--port=8080" "${@}"
fi
