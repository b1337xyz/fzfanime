## IMPORTANT: Edit/Read the scripts before running them 

### Notes:
- Files in `$ANIME_DIR` are all symlinks 
- Before running `fzfanime.sh` create `$DB` and `$MALDB`
- By default anilist is used as main database

---

### Defaults
```bash
ANIME_DIR=~/Videos/Anime    
PLAYER='mpv'                 
DB=~/.cache/anilist.json    # generated with tools/update_anilist.py
MALDB=~/.cache/maldb.json   # generated with tools/update_maldb.py
ANIMEHIST=~/.cache/anime_history.txt
WATCHED_FILE=~/.cache/watched_anime.txt
MPVHIST=~/.cache/mpv/mpvhistory.log # https://github.com/b1337xyz/config/blob/main/mpv/scripts/mpvhistory.lua
BACKEND=ueberzug # ueberzug kitty
```

---

### Dependencies
- [fzf](https://github.com/junegunn/fzf)
- [jq](https://github.com/stedolan/jq)
- [ueberzug](https://github.com/b1337xyz/ueberzug)
- [devour](https://github.com/salman-abedin/devour) (optional)

---

| Bind   | Description                                                  |
|---     |---                                                           |
|Alt-c   | continue watching                                            |
|Alt-s   | shuffle list                                                 |
|Alt-a   | add current line to `$WATCHED_FILE`                          |
|Alt-d   | remove current line from `$WATCHED_FILE`                     |
|Alt-u   | unlist entries from `$WATCHED_FILE`                          |
|Ctrl-l  | load `$ANIMEHIST`                                            |
|Ctrl-w  | load `$WATCHED_FILE`                                         |
|Alt-p   | select `path`                                                |
|Alt-r   | select `rated`                                               |
|Ctrl-v  | select `type`                                                |
|Alt-b   | sort by size                                                 |
|Alt-l   | sort by ctime (time of last modification of file)            |
|Ctrl-e  | sort by episodes                                             |
|Ctrl-g  | sort by genre                                                |
|Ctrl-s  | sort by score                                                |
|Ctrl-y  | sort by year                                                 |
|Ctrl-a  | list only available entries                                  |
|Ctrl-h  | list only entries rated Rx                                   |
|Ctrl-b  | go to first item of the list                                 |
|Ctrl-t  | go to last item of the list                                  |
|Ctrl-p  | play current line with `$PLAYER`                             |
|Ctrl-r  | reload                                                       |

![preview]()
