#!/usr/bin/env bash
# shellcheck disable=SC2155,SC2154,SC2086,SC2153
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
function finalise {
    jobs -p | xargs -r kill 2>/dev/null || true
    rm "$tempfile" "$mainfile" "$modefile" 2>/dev/null || true
    if [ -S "$UEBERZUG_FIFO" ];then
        printf '{"action": "remove", "identifier": "preview"}\n' > "$UEBERZUG_FIFO"
        rm "$UEBERZUG_FIFO" 2>/dev/null
    fi
    [ -f "$FEH_IMAGE" ] && rm "$FEH_IMAGE"
}
function check_link {
    p=$(readlink -m "${ANIME_DIR}/$1")
    x=$p
    printf '%s\n' "$x"

    if [ -f "$MPVHIST" ];then
        last_ep=$(grep -F "/${1}/" "$MPVHIST" | tail -n1)
        last_ep=${last_ep##*/}
        if [ -f "${p}/${last_ep}" ];then
            printf 'Continue: \e[1;32m%s\e[m\n' "$last_ep"
        fi
    fi

    declare -a files=()
    cache="${CACHE_DIR}/${1}"
    if [ -e "$p" ]; then
        [ -f "$cache" ] && rm "$cache"
        ext_ptr='.*\.\(webm\|mkv\|avi\|mp4\|ogm\|mpg\|rmvb\)$'
        size=$(du -sh "$p" | awk '{print $1}' | tee -a "$cache")

        while IFS= read -r -d $'\0' i; do
            files+=("$i")
            echo "$i"
        done < <(find "$p" -iregex "$ext_ptr" -printf '%f\0' | sort -z) >> "$cache"
    elif [ -s "$cache" ]; then
        size=$(head -1 "$cache")
        while read -r i;do
            files+=("$i")
        done < <(tail -n +2 "$cache")
        printf '\e[1;31mUnavailable\e[m\n'
    fi

    if [ "${#files[@]}" -gt 0 ];then
        [ -n "$size" ] && printf 'Size: %s\t' "$size"
        printf 'Files: %s\n' "${#files[@]}"
        n=4
        for ((i=0;i<"${#files[@]}";i++));do
            x=${files[i]}
            if [ "$i" -lt "$n" ] || [ "${#files[@]}" -le $((n*2)) ];then
                printf '%s\n' "$x"
            elif [ "$i" -ge $(( ${#files[@]} - n )) ];then
                printf '%s\n' "$x"
            fi
        done
    else
        printf '\e[1;31mUnavailable\e[m\n'
    fi
}
function preview {
    IFS=$'\n' read -d '' -r title _type genres episodes score rated studios image < <(\
        jq -Mr --argjson k "\"$1\"" '.[$k] |
           "\(.title // "404")
            \(.type)
            \(.genres | if length > 0 then . | join(", ") else "Unknown" end)
            \(.episodes // "Unknown")
            \(.score // "Unknown")
            \(.rated)
            \(.studios | if length > 0 then . | join(", ") else "Unknown" end)
            \(.image)"' "$DB" 2>/dev/null | sed 's/^\s*//')

    [ "$BACKEND" = "kitty" ] && kitty icat --transfer-mode=file \
        --stdin=no --clear --silent >/dev/null 2>&1 </dev/tty

    if [ "$title" = "404" ];then

        [ "$BACKEND" = "ueberzug" ] &&
            printf '{"action": "remove", "identifier": "preview"}\n' > "$UEBERZUG_FIFO"

        printf "404 - preview not found\n\n"
        # for _ in $(seq $((COLUMNS)));do printf '─' ;done ; echo
        # check_link "$1"
        return 0
    fi
    watched=$(grep -xF "$1" "$WATCHED_FILE" || true)
    if ! [[ "$BACKEND" =~ viu|chafa ]];then
        printf '%'$WIDTH's %s\n'              ' ' "$title"
        printf '%'$WIDTH's Type: %s\n'        ' ' "${_type:-Unknown}"
        printf '%'$WIDTH's Genre: %s\n'       ' ' "$genres"
        printf '%'$WIDTH's Episodes: %s\n'    ' ' "$episodes"
        printf '%'$WIDTH's Rated: %s\n'       ' ' "$rated"
        printf '%'$WIDTH's Score: %s\n'       ' ' "$score"
        printf '%'$WIDTH's Studios: %s\n'     ' ' "$studios"

        if [ "$watched" ];then
            printf '%'$WIDTH's \e[1;32mWatched\e[m\n\r' ' '
        else
            echo
        fi
    fi


    case "$BACKEND" in
        kitty)
            kitty icat --transfer-mode=file \
                --stdin=no --silent --align=left --scale-up \
                --place "${WIDTH}x${HEIGHT}@0x0" "$image" >/dev/null 2>&1 </dev/tty
        ;;
        ueberzug) 
            printf '{"action": "add", "identifier": "%s", "x": 0, "y": 0, "width": %d, "height": %d, "scaler": "%s", "path": "%s"}\n' \
                "preview" "$WIDTH" "$HEIGHT" "distort" "$image" > "$UEBERZUG_FIFO"
        ;;
        feh)
            echo "$image" > "$FEH_FILE"
        ;;
        viu|chafa)
            # https://github.com/atanunq/viu#from-source-recommended
            # `tput cup 0 0` and `viu -a -x 0 -y 0` does not work so i had to do this :(
            arr=(
                "$title"
                "Type: ${_type:-Unknown}"
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
                printf '%s ' "$str"
                if [ "$i" -lt "${#arr[@]}" ]; then
                    printf '%s ' "${arr[i]}"
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

    
    if ! [[ "$BACKEND" =~ viu|chafa ]];then
        for _ in {1..13};do echo ;done
    fi
    # for _ in $(seq $((COLUMNS)));do printf '─' ;done ; echo
    check_link "$1" &
}
export -f preview check_link
