#!/usr/bin/env bash

declare -r -x anidb=../anilist.json
declare -r -x maldb=../maldb.json

preview() {
    echo "AniList"
    jq -C --arg k "$1" '.[$k]' "$anidb"
    echo "MAL"
    jq -C --arg k "$1" '.[$k]' "$maldb"
}
export -f preview

jq -Mcr 'keys[]' "$anidb" | fzf --preview 'preview {}'
