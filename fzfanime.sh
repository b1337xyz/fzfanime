#!/usr/bin/env bash
# shellcheck disable=SC2155,SC2034
set -eo pipefail

export TERM=screen-256color

echo -ne "\033]0;fzfanime.sh\007"
root=$(realpath "$0") root=${root%/*}
cd "$root"

function help {
    cat << EOF
Usage: ${0##*/} [options ...]

Options:
    -u --update             Update/create \$DB
    -p --player <player>    Video player (default: mpv)
    -b --backend <backend>  Image preview (default: ueberzug) (available: ueberzug kitty feh viu chafa)
    -f --fallback <backend> If \$DISPLAY is unset fallback to <backend> (default: viu)
    -c --clean              Remove entries where .fullpath does not exist
    -e --edit               Edit the config file
    -q --quit-on-play       Quit fzf when playing
    -h --help               Show this message

Notes:
    - \$DB generated using Anilist APIv2 -> https://anilist.gitbook.io/anilist-apiv2-docs
      and Jikan APIv4 -> https://api.jikan.moe/v4/anime
    - By default AniList is used as main database

EOF
    exit 0
}

while [ $# -gt 0 ];do
    case "$1" in
        -p|--player*) shift; player=${1#*=} ;;
        -b|--backend*) shift; backend=${1#*=} ;;
        -f|--fallback*) shift; fallback=${1#*=} ;;
        -e|--edit) "${EDITOR:-vi}" config; exit 0 ;;
        -u|--update) 
            . "${root}/venv/bin/activate"
            python3 tools/update.py
            exit $?
            ;;
        -c|--clean) python3 tools/clean_db.py; exit $? ;;
        -g|--upgrade) python3 tools/clean_db.py && python3 tools/update.py; exit $? ;;
        -q|--quit-on-play) declare -r -x quit_on_play=y ;;
        -*) help ;;
    esac
    shift
done
[ -z "$DISPLAY" ] && backend=${fallback:-viu}

### USER SETTINGS
declare -r -x DB="${root}/data/anilist.json"
declare -r -x ANIMEHIST="${root}/data/anime_history.txt"
declare -r -x WATCHED_FILE="${root}/data/watched_anime.txt"
declare -r -x PLAYER=${player:-'mpv --force-window=immediate --input-ipc-server=/tmp/mpvanime'}
declare -x BACKEND=${backend:-ueberzug}
declare -r FZF_DEFAULT_OPTS="--exact --no-separator --cycle --no-hscroll --no-scrollbar --color=dark"
### END OF USER SETTINGS

### PREVIEW SETTINGS
declare -r -x W3MIMGDISPLAY=/usr/lib/w3m/w3mimgdisplay
declare -r -x UEBERZUG_FIFO=$(mktemp --dry-run --suffix "fzf-$$-ueberzug")
declare -r -x WIDTH=28  # image width
declare -r -x HEIGHT=16
declare -r -x MPVHIST=~/.cache/mpv/mpvhistory.log
declare -r -x CACHE_DIR=~/.cache/fzfanime
declare -r -x FEH_FILE=/tmp/.fzfanime.feh
declare -r -x FEH_WIDTH=255
declare -r -x FEH_HEIGHT=380
declare -r -x RE_EXT='.*\.\(webm\|mkv\|avi\|mp4\|ogm\|mpg\|rmvb\)$'
### END OF PREVIEW SETTINGS

[ -e "$DB" ]           || { "${EDITOR:-vi}" "${root}/config" && python3 tools/update.py; }
[ -e "$WATCHED_FILE" ] || :> "$WATCHED_FILE"
[ -e "$ANIMEHIST" ]    || :> "$ANIMEHIST"
[ -d "$CACHE_DIR" ]    || mkdir -p "$CACHE_DIR"
hash "$BACKEND" 2>/dev/null || { printf '"%s" not found\n' "$BACKEND"; exit 1; }

# shellcheck disable=SC1091
source preview.sh || { printf 'Failed to source %s\n' "${root}/preview.sh"; exit 1; }

declare -r -x pid=$$
declare -r -x script=$0
declare -r -x mainfile=$(mktemp --dry-run) 
declare -r -x tempfile=$(mktemp --dry-run)
declare -r -x modefile=$(mktemp --dry-run)
declare -r -x goback=${mainfile}.bak

function play {
    path=$(jq -r --arg k "$1" '.[$k].fullpath' "$DB")
    [ -e "$path" ] || return 1

    # save some cpu usage... maybe
    [ -S "$UEBERZUG_FIFO" ] && 
        printf '{"action":"remove", "identifier":"fzf"}\n' > "$UEBERZUG_FIFO"

    echo "$1" >> "$ANIMEHIST"
    # shellcheck disable=SC2086
    if hash devour && [ -z "$quit_on_play" ];then
        devour $PLAYER "$path" >/dev/null 2>&1
    else
        nohup  $PLAYER "$path" >/dev/null 2>&1 & disown
    fi

    [ "$quit_on_play" = y ] && sleep 1 && kill "$pid"
}

function main {
    # grep -xFf <file1> <file2> ...  will keep the order of the second file
    
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
            grep -xFf <(jq -Sr .[].fullpath "$DB" | while read -r i;do 
                    a=${i%/*}
                    [ "$a" = "$b" ] && continue
                    [ -e "$a" ] || { b=$a; continue; }
                    printf '%s\n' "${i##*/}"
                done) "$mainfile" | tee "$tempfile"
        ;;
        by_score)
            grep -xFf "$mainfile" <(jq -r \
                '[keys[] as $k | {id: $k, score: .[$k].score}] | sort_by(.score) | .[].id' "$DB") | tee "$tempfile"
        ;;
        by_year)
            # sed 's/.*(\([0-9]\{4\}\)).*/\1;\0/g' "$mainfile" | sort -n | sed 's/^[0-9]\{4\}\;//g' | tee "$tempfile"
            grep -xFf "$mainfile" < <(jq -r \
                '[keys[] as $k | {id: $k, t: .[$k].aired}] | sort_by(.t) | .[].id' "$DB") | tee "$tempfile"
        ;;
        by_episodes)
            grep -xFf "$mainfile" <(jq -r '[keys[] as $k |
                {id: $k, episodes: .[$k].episodes}] | sort_by(.episodes)[] | .id' "$DB") | tee "$tempfile"
        ;;
        by_size)
            keys=$(awk '{printf("\"%s\",", $0)}' "$mainfile")
            jq -r --argjson a "[${keys::-1}]" '$a[] as $k | .[$k].fullpath' "$DB" | tr \\n \\0 |
                du -sL --files0-from=- | sort -n | grep -oP '[^/]*$' | tee "$tempfile"
        ;;
        by_time)
            keys=$(awk '{printf("\"%s\",", $0)}' "$mainfile")
            grep -xFf "$mainfile" <(jq -r --argjson a "[${keys::-1}]" '$a[] as $k | .[$k].fullpath | split("/")[:-1] | join("/")' "$DB" |
                sort -u | tr \\n \\0 | xargs -r0I '{}' find '{}' -mindepth 1 -maxdepth 1 -type d -printf '%C@\t%f\n' 2>/dev/null |
                sort -rn | cut -f2-) | tee "$tempfile"
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
        [0-9]*)
            m=$(( $1 + 10 ))
            grep -Ff < <(jq --argjson n "$1" --argjson m "$m" -Sr 'keys[] as $k |
                select(.[$k].score >= $n and .[$k].score < $m) | $k' "$DB") "$mainfile" | tee "$tempfile"
        ;;
        genre) 
            printf genres > "$modefile"
            jq -r '.[] | .genres[] // "Unknown"' "$DB" | sort -u
            return
        ;;
        type)
            printf type > "$modefile"
            jq -r '.[] | .type // "Unknown"' "$DB" | sort -u
            return
        ;;
        rating)
            printf rating > "$modefile"
            jq -r '.[] | .rating // "Unknown"' "$DB" | sort -u
            return
        ;;
        path)
            printf path > "$modefile"
            jq -r '.[].fullpath' "$DB" | grep -oP '.*(?=/.*/)' | sort -u
            return
        ;;
        go_back) cat "$goback"; return ;;
        select)
            curr_mode=$(<"$modefile")
            if [ "$curr_mode" = genres ];then
                if [ "$2" = "Unknown" ];then
                    jq -r 'keys[] as $k | select(.[$k]["genres"] == []) | $k' "$DB"
                else
                    jq -r --arg mode "$curr_mode" --arg v "$2" 'keys[] as $k | select(.[$k][$mode] | index($v)) | $k' "$DB"
                fi | tee "$tempfile"
            elif [[ "$curr_mode" =~ (type|rating) ]];then
                if [ "$2" = "Unknown" ];then
                    jq -r --arg mode "$curr_mode" 'keys[] as $k | select(.[$k][$mode] | not) | $k' "$DB"
                else
                    jq -r --arg mode "$curr_mode" --arg v "$2" 'keys[] as $k | select(.[$k][$mode] == $v) | $k' "$DB"
                fi | tee "$tempfile"
            elif [ "$curr_mode" = path ];then
                jq -r '.[].fullpath' "$DB" | grep -F "${2}/" | grep -oP '[^/]*$' | tee "$tempfile"
            else
                play "$2"
                cat "$mainfile"
            fi
        ;;
        adult)
            jq -Sr 'keys[] as $k | select(.[$k].is_adult) | $k' "$DB" | tee "$tempfile"
        ;;
        *)
            jq -Sr 'keys[] as $k | select(.[$k].is_adult | not) | $k' "$DB" | tee "$tempfile"
        ;;
    esac

    [ -f "$modefile" ] && rm "$modefile"
    if [ -s "$tempfile" ];then
        [ -f "$mainfile" ] && cp "$mainfile" "$goback"
        mv -f "$tempfile" "$mainfile"  # Make sure not to read and write the same file in the same pipeline
    fi
}

function delete {
    path=$(jq -r --arg k "$1" '.[$k].fullpath' "$DB")
    printf 'Yes\nNo' | dmenu -l 2 -p "Delete ${path}?" | grep -qx Yes && rm -rf "$path"
}

function finalise {
    jobs -p | xargs -r kill 2>/dev/null || true
    rm "$FEH_FILE" "$UEBERZUG_FIFO" "$tempfile" "$mainfile" "$goback" "$modefile" 2>/dev/null || true
    exit 0
}

trap finalise EXIT
export -f main play delete
if [ -n "$DISPLAY" ];then
    case "$BACKEND" in
        ueberzug) start_ueberzug ;;
        feh) start_feh & ;;
    esac
fi


n=$'\n'
# --color 'gutter:-1,bg+:-1,fg+:6:bold,hl+:1,hl:1,border:7:bold,header:6:bold,info:7,pointer:1' \
red=$'\e[1;31m'
blu=$'\e[1;34m'
rst=$'\e[m'
label="╢ \
^p ${red}pla${rst} \
^s ${red}sco${rst} \
^l ${red}las${rst} \
^f ${red}fir${rst} \
^r ${red}rel${rst} \
^h ${red}hen${rst} \
^t ${red}his${rst} \
^w ${red}wat${rst} \
^a ${red}ava${rst} \
^e ${red}epi${rst} \
^g ${red}gen${rst} \
^v ${red}typ${rst} \
^n ${red}rem${rst} \
[p ${blu}pat${rst} \
[u ${blu}unw${rst} \
[c ${blu}con${rst} \
[a ${blu}add${rst} \
[d ${blu}del${rst} \
[s ${blu}shu${rst} \
[b ${blu}siz${rst} \
╟"

main _ | fzf --border=bottom --reverse --border-label="${label}" \
    --info inline-right \
    --border-label-pos=3:center \
    --padding 2%,1,2%,1 \
    --border=sharp \
    --prompt "> " \
    --preview 'preview {}' \
    --preview-window 'right:48%:border-none' \
    --bind 'enter:reload(main select {})+clear-query' \
    --bind 'ctrl-n:execute(delete {})+refresh-preview' \
    --bind 'ctrl-l:last' \
    --bind 'ctrl-f:first' \
    --bind 'ctrl-d:delete-char' \
    --bind 'ctrl-p:execute-silent(quit_on_play=n play {})' \
    --bind 'ctrl-r:reload(main)+first+change-prompt(NORMAL )' \
    --bind 'ctrl-h:reload(main adult)+first+change-prompt(ADULT )' \
    --bind 'ctrl-a:reload(main avail)+change-prompt(AVAILABLE )' \
    --bind 'ctrl-w:reload(main watched)+first+change-prompt(WATCHED )' \
    --bind 'ctrl-t:reload(main history)+first+change-prompt(HISTORY )' \
    --bind 'ctrl-g:reload(main genre)+first+change-prompt(GENRE )' \
    --bind 'ctrl-v:reload(main type)+first+change-prompt(TYPE )' \
    --bind 'ctrl-y:reload(main by_year)+first+change-prompt(BY YEAR )' \
    --bind 'ctrl-s:reload(main by_score)+first+change-prompt(BY SCORE )' \
    --bind 'ctrl-e:reload(main by_episodes)+first+change-prompt(BY EPISODE )' \
    --bind 'alt-b:reload(main by_size)+first+change-prompt(BY SIZE )' \
    --bind 'alt-l:reload(main by_time)+first+change-prompt(BY TIME )' \
    --bind 'alt-p:reload(main path)+first+change-prompt(PATH )' \
    --bind 'alt-r:reload(main rating)+first+change-prompt(RATING )' \
    --bind 'alt-s:reload(main shuffle)+first+change-prompt(SHUFFLED )' \
    --bind 'alt-u:reload(main unwatched)+change-prompt(UNWATCHED )' \
    --bind 'alt-c:reload(main continue)+first+change-prompt(CONTINUE )' \
    --bind 'alt-a:execute-silent(main add_watched {})+refresh-preview' \
    --bind 'alt-d:execute-silent(main del_watched {})+refresh-preview' \
    --bind 'f2:reload(main 20)+refresh-preview' \
    --bind 'f3:reload(main 30)+refresh-preview' \
    --bind 'f4:reload(main 40)+refresh-preview' \
    --bind 'f5:reload(main 50)+refresh-preview' \
    --bind 'f6:reload(main 60)+refresh-preview' \
    --bind 'f7:reload(main 70)+refresh-preview' \
    --bind 'f8:reload(main 80)+refresh-preview' \
    --bind 'f9:reload(main 90)+refresh-preview' \
    --bind 'tab:reload(main go_back)+refresh-preview' \
    --bind 'end:preview-bottom' \
    --bind 'home:preview-top'
