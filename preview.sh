#!/usr/bin/env bash
function start_ueberzug {
    mkfifo "${UEBERZUG_FIFO}"
    tail --follow "$UEBERZUG_FIFO" | ueberzug layer --parser json 2>/dev/null &
}
function start_feh {
    # wait for the preview 
    while ! [ -f "$FEH_FILE" ];do sleep 0.3; done

    # get current focused window
    active_window_id=$(xdotool getactivewindow)

    # get x and y positions
    read -r x y < <(xwininfo -id "$active_window_id" |
        sed -n 's/.*Corners:\s*\([+-][0-9]*\)\([+-][0-9]*\).*/\1 \2/p')

    feh --hide-pointer --no-menus --borderless --auto-zoom \
        --scale-down --geometry "${FEH_WIDTH}x${FEH_HEIGHT}${x}${y}" \
        --image-bg black --reload 0.3 --filelist "$FEH_FILE" &

    # unfocus feh
    sleep 0.5; xdotool windowactivate "$active_window_id"
}
function show_files {
    key="$1"
    fullpath="$2"
    printf '%s\n' "${fullpath%/*}"

    if [ -f "$MPVHIST" ];then
        last_ep=$(grep -F "/${key}/" "$MPVHIST" | tail -1)
        last_ep=${last_ep##*/}
        [ -n "$last_ep" ] && printf 'Continue: \e[1;32m%s\e[m\n' "$last_ep"
    fi

    cache="${CACHE_DIR}/${1}"
    if [ -e "$fullpath" ]; then
        find -L "$fullpath" -iregex "$RE_EXT" -printf '%f\n' | sort -V > "$cache"
    else
        printf '\e[1;31mUnavailable\e[m\n'
    fi

    if [ -f "$cache" ];then
        n=$(wc -l < "$cache")
        if [ "$n" -gt 0 ]; then
            printf 'Files: %s\n' "$n"
            { head -5 "$cache"; tail -5 "$cache"; } | sort -uV
        fi
    fi
}
function preview {
    IFS=$'\n' read -d '' -r title _type genres episodes score rated studios image fullpath < <(\
        jq -Mr --argjson k "\"$1\"" '.[$k] |
           "\(.title)
            \(.type // "Unknown")
            \(.genres | if length > 0 then . | join(", ") else "Unknown" end)
            \(.episodes // "Unknown")
            \(.score // "Unknown")
            \(.rating)
            \(.studios | if length > 0 then . | join(", ") else "Unknown" end)
            \(.image)
            \(.fullpath)"' "$DB" 2>/dev/null | sed 's/^\s*//')

    [ "$BACKEND" = "kitty" ] && kitty icat --transfer-mode=file \
        --stdin=no --clear --silent >/dev/null 2>&1 </dev/tty

    if [ "$title" = "null" ];then
        [ -e "$UEBERZUG_FIFO" ] &&
            printf '{"action": "remove", "identifier": "fzfanime"}\n' > "$UEBERZUG_FIFO"

        printf "404 - preview not found\n\n"
        return 0
    fi
    watched=$(grep -xF "$1" "$WATCHED_FILE" || true)
    if ! [[ "$BACKEND" =~ viu|chafa ]];then
        # shellcheck disable=SC2153
        printf '%'"$WIDTH"'s %s\n'              ' ' "$title"
        printf '%'"$WIDTH"'s Type: %s\n'        ' ' "${_type}"
        printf '%'"$WIDTH"'s Genre: %s\n'       ' ' "$genres"
        printf '%'"$WIDTH"'s Episodes: %s\n'    ' ' "$episodes"
        printf '%'"$WIDTH"'s Rated: %s\n'       ' ' "$rated"
        printf '%'"$WIDTH"'s Score: %s\n'       ' ' "$score"
        printf '%'"$WIDTH"'s Studios: %s\n'     ' ' "$studios"

        if [ -n "$watched" ];then printf '%'"$WIDTH"'s \e[1;32mWatched\e[m\n\r' ' '; else echo; fi
    fi

    case "$BACKEND" in
        feh) printf '%s\n' "$image" > "$FEH_FILE" ;;
        kitty)
            # shellcheck disable=SC2153
            kitty icat --transfer-mode=file \
                --stdin=no --silent --align=left --scale-up \
                --place "${WIDTH}x${HEIGHT}@0x0" "$image" >/dev/null 2>&1 </dev/tty
        ;;
        ueberzug) 
            printf '{"action": "add", "identifier": "%s", "x": 0, "y": 0, "width": %d, "height": %d, "scaler": "%s", "path": "%s"}\n' \
                "fzfanime" "$WIDTH" "$HEIGHT" "distort" "$image" > "$UEBERZUG_FIFO"
        ;;
        viu|chafa)
            # https://github.com/atanunq/viu#from-source-recommended
            # `tput cup 0 0` and `viu -a -x 0 -y 0` does not work so i had to do this :(
            arr=(
                "$title"
                "Type: ${_type}"
                "Genre: $genres"
                "Episodes: $episodes"
                "Rated: $rated"
                "Score: $score"
                "Studios: $studios"
            )
            i=0
            if [ "$BACKEND" = "chafa"  ];then
                chafa --size="${WIDTH}x${HEIGHT}" "$image"
            else
                viu -s -w "$WIDTH" -h "$HEIGHT" "$image"
            fi | while read -r str; do
                printf '%s' "$str"
                if [ "$i" -lt "${#arr[@]}" ]; then
                    printf ' %s ' "${arr[i]}"
                elif [ "$i" -eq "${#arr[@]}" ]; then
                    [ -n "$watched" ] && printf '\033[1;32m Watched \033[m'
                fi
                printf '\n'
                i=$((i+1))
            done
        ;;
        w3m)
            # https://github.com/junegunn/fzf/issues/2551
            read -r width height < <(printf '5;%s' "$image" | "$W3MIMGDISPLAY")
            printf '0;1;%s;%s;%s;%s;;;;;%s\n4;\n3;' \
                "0" "0" "$width" "$height" "$image" | "$W3MIMGDISPLAY"
        ;;
    esac

    [[ "$BACKEND" =~ viu|chafa ]] || for _ in {1..13};do echo; done
    # for _ in $(seq $((COLUMNS)));do printf '─' ;done ; echo
    show_files "$1" "$fullpath"
}
export -f preview show_files
