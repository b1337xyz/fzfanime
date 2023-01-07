## IMPORTANT: Edit/Read the scripts before running them 

### Notes:
- The script expects that all files in `$ANIME_DIR` are symlinks
- Before running `fzfanime.sh` create `$DB` and `$MALDB`
- By default AniList is used as main database

---

### Defaults
```bash
ANIME_DIR=~/Videos/Anime    
BACKEND=ueberzug    # ueberzug kitty
DB=anilist.json     # generated with tools/update_anilist.py
MALDB=maldb.json    # generated with tools/update_maldb.py
PLAYER='mpv'                 
```
---

### Dependencies
- [fzf](https://github.com/junegunn/fzf)
- [jq](https://github.com/stedolan/jq)
- [ueberzug](https://github.com/b1337xyz/ueberzug) (optional)
- [devour](https://github.com/salman-abedin/devour) (optional)
- [mpvhistory.lua](https://github.com/b1337xyz/config/blob/main/mpv/scripts/mpvhistory.lua) (optional)

---

![demo](demo.gif)

---
```
alt-c   : Continue watching
alt-s   : Shuffle list
alt-a   : Add current line to `$WATCHED_FILE`
alt-d   : Remove current line from `$WATCHED_FILE`
alt-u   : Unlist entries from `$WATCHED_FILE`
ctrl-l  : Load `$ANIMEHIST`
ctrl-w  : Load `$WATCHED_FILE`
alt-p   : Select `path`
alt-r   : Select `rated`
ctrl-v  : Select `type`
alt-b   : Sort by size
alt-l   : Sort by ctime (time of last modification of file)
ctrl-e  : Sort by episodes
ctrl-g  : Sort by genre
ctrl-s  : Sort by score
ctrl-y  : Sort by year
ctrl-a  : List only available entries
ctrl-h  : List only entries rated Rx
ctrl-b  : Go to first item of the list
ctrl-t  : Go to last item of the list
ctrl-p  : Play current line with `$PLAYER`
ctrl-r  : Reload
```
