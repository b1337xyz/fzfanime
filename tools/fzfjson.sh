#!/usr/bin/env bash

declare -r -x anidb=../data/anilist.json
declare -r -x maldb=../data/maldb.json

preview() {
    echo "AniList"
    jq -C --arg k "$1" '.[$k]' "$anidb"
    echo "MAL"
    jq -C --arg k "$1" '.[$k]' "$maldb"
}
export -f preview

jq -Mcr 'keys[]' "$maldb" | fzf --border none --preview-window 'right:border-left' --preview 'preview {}'
