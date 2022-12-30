## WARNING: Edit/Read the scripts before running them 

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

| Bind   | Description                                       |
|--------|---------------------------------------------------|
|alt-c   | continue watching                                 |
|alt-s   | shuffle list                                      |
|alt-a   | add current line to `$WATCHED_FILE`               |
|alt-d   | remove current line from `$WATCHED_FILE`          |
|alt-u   | unlist entries from `$WATCHED_FILE`               |
|ctrl-l  | load `$ANIMEHIST`                                 |
|ctrl-w  | load `$WATCHED_FILE`                              |
|alt-p   | select `path`                                     |
|alt-r   | select `rated`                                    |
|ctrl-v  | select `type`                                     |
|alt-b   | sort by size                                      |
|alt-l   | sort by ctime (time of last modification of file) |
|ctrl-e  | sort by episodes                                  |
|ctrl-g  | sort by genre                                     |
|ctrl-s  | sort by score                                     |
|ctrl-y  | sort by year                                      |
|ctrl-a  | list only available entries                       |
|ctrl-h  | list only entries rated Rx                        |
|ctrl-b  | go to first item of the list                      |
|ctrl-t  | go to last item of the list                       |
|ctrl-p  | play current line with `$PLAYER`                  |
|ctrl-r  | reload                                            |

![preview]()
