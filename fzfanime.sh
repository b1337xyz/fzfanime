#!/usr/bin/env bash
# shellcheck disable=SC2155,SC1091
# Notes:
#   - grep -xFf <file1> <file2> ...  will keep the order of the second file

set -eo pipefail

root=$(realpath "$0") root=${root%/*}
cd "$root"

function help {
    cat << EOF
Usage: ${0##*/} [options ...]

Options:
    -u --update             update/create \$DB
    -p --player <player>    video player (default: mpv)
    -b --backend <backend>  image preview (default: ueberzug) (available: ueberzug kitty feh viu chafa)
    -f --fallback <backend> if \$DISPLAY is unset fallback to <backend> (default: viu)
    -h --help               show this message

Notes:
    - --option=value is not supported, use --option value
    - \$DB generated using Anilist APIv2 -> https://anilist.gitbook.io/anilist-apiv2-docs
      and Jikan APIv4 -> https://api.jikan.moe/v4/anime
    - By default AniList is used as main database

EOF
    exit 0
}
function update {
    set -x
    python3 update_maldb.py
    python3 update_anilist.py
    python3 tools/clean_db.py
    set +x
}

while [ $# -gt 0 ];do
    case "$1" in
        -p|--player) shift; player=$1 ;;
        -b|--backend) shift; backend=$1 ;;
        -f|--fallback) shift; fallback=$1 ;;
        -u|--update) update; exit 0 ;;
        -*) help ;;
    esac
    shift
done
[ -z "$DISPLAY" ] && hash "${fallback:-viu}" && backend=${fallback:-viu}

### USER SETTINGS
declare -r -x DB="${root}/data/anilist.json"
declare -r -x ANIMEHIST="${root}/data/anime_history.txt"
declare -r -x WATCHED_FILE="${root}/data/watched_anime.txt"
declare -r -x PLAYER=${player:-'mpv --profile=fzfanime'}
declare -r -x BACKEND=${backend:-ueberzug}
### END OF USER SETTINGS

### PREVIEW SETTINGS
declare -r -x W3MIMGDISPLAY=/usr/lib/w3m/w3mimgdisplay
declare -r -x UEBERZUG_FIFO=$(mktemp --dry-run --suffix "fzf-$$-ueberzug")
declare -r -x WIDTH=32  # image width
declare -r -x HEIGHT=20
declare -r -x MPVHIST=~/.cache/mpv/mpvhistory.log
declare -r -x CACHE_DIR=~/.cache/fzfanime_preview
declare -r -x FEH_FILE=/tmp/.fzfanime.feh
declare -r -x FEH_WIDTH=255
declare -r -x FEH_HEIGHT=380
### END OF PREVIEW SETTINGS

[ -e "$DB" ] || update

source preview.sh || { printf 'Failed to source %s\n' "${root}/preview.sh"; exit 1; }

[ -d "$CACHE_DIR" ] || mkdir -p "$CACHE_DIR"
[ -e "$WATCHED_FILE" ] || :> "$WATCHED_FILE"
[ -e "$ANIMEHIST" ] || :> "$ANIMEHIST"

declare -r -x mainfile=$(mktemp --dry-run) 
declare -r -x tempfile=$(mktemp --dry-run)
declare -r -x modefile=$(mktemp --dry-run)

function play {
    # path=$(jq -Mcr --argjson k "\"$1\"" '.[$k].fullpath' "$DB")
    path=$(jq -Mcr --arg k "$1" '.[$k].fullpath' "$DB")
    [ -e "$path" ] || return 1

    # save some cpu usage... maybe
    [ "$BACKEND" = ueberzug ] && 
        printf '{"action": "remove", "identifier": "preview"}\n' > "$UEBERZUG_FIFO"

    echo "$1" >> "$ANIMEHIST"
    # shellcheck disable=SC2086
    if hash devour;then
        devour $PLAYER "$path" >/dev/null 2>&1
    else
        nohup  $PLAYER "$path" >/dev/null 2>&1 & disown
    fi
}
function main {
    # filters
    case "$1" in
        shuffle) shuf "$mainfile"; return ;;
        add_watched)
            grep -qxF "$2" "$WATCHED_FILE" 2>/dev/null || printf '%s\n' "$2" >> "$WATCHED_FILE"
        ;;
        del_watched)
            if grep -qxF "$2" "$WATCHED_FILE" 2>/dev/null;then
                echo "$2" | sed -e 's/[]\[\*\$]/\\\\&/g' | xargs -rI{} sed -i "/{}/d" "$WATCHED_FILE"
            fi
        ;;
        avail)
            grep -xFf <(jq -SMcr .[].fullpath "$DB" | while read -r i;do 
                    a=${i%/*}
                    [ "$a" = "$b" ] && continue
                    [ -e "$a" ] || { b=$a; continue; }
                    printf '%s\n' "${i##*/}"
                done) "$mainfile" | tee "$tempfile"
        ;;
        by_score)
            grep -xFf "$mainfile" <(jq -Mcr \
                '[keys[] as $k | {id: $k, score: .[$k].score}] | sort_by(.score) | .[].id' "$DB") | tee "$tempfile"
        ;;
        by_year)
            sed 's/.*(\([0-9]\{4\}\)).*/\1;\0/g' "$mainfile" | sort -n | sed 's/^[0-9]\{4\}\;//g' | tee "$tempfile"
        ;;
        by_episodes)
            grep -xFf "$mainfile" <(jq -Mcr '[keys[] as $k | {id: $k, episodes: .[$k].episodes}] | sort_by(.episodes)[] | .id' "$DB") | tee "$tempfile"
        ;;
        watched)
            grep -xFf "$mainfile" "$WATCHED_FILE" | tac | tee "$tempfile"
        ;;
        unwatched)
            grep -xvFf "$WATCHED_FILE" "$mainfile" | tee "$tempfile"
        ;;
        history)
            grep -xFf "$mainfile" <(tac "$ANIMEHIST" | awk '!seen[$0]++') | tee "$tempfile"
        ;;
        continue)
            grep -vxFf "$WATCHED_FILE" <(grep -xFf "$mainfile" <(tac "$ANIMEHIST" | awk '!seen[$0]++')) | tee "$tempfile"
        ;;
        latest)
            keys=$(while read -r i;do printf '"%s",' "$i" ;done < "$mainfile")
            jq -Mcr --argjson a "[${keys::-1}]" '$a[] as $k | .[$k].fullpath' "$DB" | tr \\n \\0 |
                xargs -r0 ls --color=never -dN1tc 2>/dev/null | grep -oP '[^/]*$' | tee "$tempfile"
        ;;
        by_size)
            keys=$(while read -r i;do printf '"%s",' "$i" ;done < "$mainfile")
            jq -Mcr --argjson a "[${keys::-1}]" '$a[] as $k | .[$k].fullpath' "$DB" | tr \\n \\0 |
                du -L --files0-from=- | sort -n | grep -oP '[^/]*$' | tee "$tempfile"
        ;;
        genre) 
            printf "genres" > "$modefile"
            jq -r '.[] | .genres[] // "Unknown"' "$DB" | sort -u
            return
        ;;
        type)
            printf "type" > "$modefile"
            jq -r '.[] | .type // "Unknown"' "$DB" | sort -u
            return
        ;;
        rated)
            printf 'rated' > "$modefile"
            jq -r '.[] | .rating // "Unknown"' "$DB" | sort -u
            return
        ;;
        path)
            printf "path" > "$modefile"
            jq -Mcr '.[].fullpath' "$DB" | grep -oP '.*(?=/Anime/)' | sort -u
            return
        ;;
        select)
            curr_mode=$(<"$modefile")
            if [ "$curr_mode" = genres ];then
                if [ "$2" = "Unknown" ];then
                    grep -xFf <(jq -r 'keys[] as $k | select(.[$k]["genres"] == []) | $k' "$DB") "$mainfile"
                else
                    grep -xFf <(jq -r --arg mode "$curr_mode" --arg v "$2" 'keys[] as $k | select(.[$k][$mode] | index($v)) | $k' "$DB") "$mainfile"
                fi | tee "$tempfile"
            elif [[ "$curr_mode" =~ (type|rated) ]];then
                if [ "$2" = "Unknown" ];then
                    grep -xFf <(jq -r --arg mode "$curr_mode" 'keys[] as $k | select(.[$k][$mode] | not) | $k' "$DB") "$mainfile"
                else
                    grep -xFf <(jq -r --arg mode "$curr_mode" --arg v "$2" 'keys[] as $k | select(.[$k][$mode] == $v) | $k' "$DB") "$mainfile"
                fi | tee "$tempfile"
            elif [ "$curr_mode" = "path" ];then
                jq -Mcr '.[].fullpath' "$DB" | grep -F "${2}/" | grep -oP '[^/]*$' | tee "$tempfile"
            else
                play "$2"
                cat "$mainfile"
            fi
        ;;
        adult)
            jq -Sr 'keys[] as $k | select(.[$k].is_adult) | $k' "$DB" | tee "$mainfile"
        ;;
        *)
            jq -Sr 'keys[] as $k | select(.[$k].is_adult | not) | $k' "$DB" | tee "$mainfile"
        ;;
    esac

    [ -f "$modefile" ] && rm "$modefile"
    [ -f "$tempfile" ] && mv -f "$tempfile" "$mainfile"
}
export -f main play

trap finalise EXIT HUP INT
if [ -n "$DISPLAY" ];then
    case "$BACKEND" in
        ueberzug) start_ueberzug ;;
        feh) start_feh & ;;
    esac
fi


n=$'\n'
# --color 'gutter:-1,bg+:-1,fg+:6:bold,hl+:1,hl:1,border:7:bold,header:6:bold,info:7,pointer:1' \
main "$@" | fzf -e --no-sort --color dark --cycle \
    --border none --no-separator --prompt "NORMAL " \
    --preview 'preview {}' \
    --preview-window 'left:53%:border-none' \
    --header "^p ^s ^l ^r ^h ^w ^a ^e ^g ^v${n}A-p A-u A-c A-a A-d A-s A-b" \
    --bind 'ctrl-t:last' \
    --bind 'ctrl-b:first' \
    --bind 'ctrl-d:delete-char' \
    --bind 'enter:reload(main select {})+clear-query' \
    --bind 'ctrl-p:execute-silent(play {})' \
    --bind 'ctrl-r:reload(main)+first+change-prompt(NORMAL )' \
    --bind 'ctrl-h:reload(main adult)+first+change-prompt(ADULT )' \
    --bind 'ctrl-a:reload(main avail)+change-prompt(AVAILABLE )' \
    --bind 'ctrl-y:reload(main by_year)+first+change-prompt(BY YEAR )' \
    --bind 'ctrl-s:reload(main by_score)+first+change-prompt(BY SCORE )' \
    --bind 'ctrl-e:reload(main by_episodes)+first+change-prompt(BY EPISODE )' \
    --bind 'ctrl-w:reload(main watched)+first+change-prompt(WATCHED )' \
    --bind 'ctrl-l:reload(main history)+first+change-prompt(HISTORY )' \
    --bind 'ctrl-g:reload(main genre)+first+change-prompt(GENRE )' \
    --bind 'ctrl-v:reload(main type)+first+change-prompt(TYPE )' \
    --bind 'alt-l:reload(main latest)+first+change-prompt(LATEST )' \
    --bind 'alt-p:reload(main path)+first+change-prompt(PATH )' \
    --bind 'alt-r:reload(main rated)+first+change-prompt(RATED )' \
    --bind 'alt-s:reload(main shuffle)+first+change-prompt(SHUFFLED )' \
    --bind 'alt-u:reload(main unwatched)+change-prompt(UNWATCHED )' \
    --bind 'alt-c:reload(main continue)+first+change-prompt(CONTINUE )' \
    --bind 'alt-b:reload(main by_size)+first+change-prompt(BY SIZE )' \
    --bind 'alt-a:execute-silent(main add_watched {})+refresh-preview' \
    --bind 'alt-d:execute-silent(main del_watched {})+refresh-preview'
