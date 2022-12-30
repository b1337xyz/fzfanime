#!/usr/bin/env dash
#
# Remove dead symlinks from $ANIME_DIR
# Symlink from /mnt/*/Anime (change this if needed) to $ANIME_DIR
# And finnally, update maldb.json and anilist.json
#

ANIME_DIR=~/Videos/Anime

set -e

root=$(realpath "$0") root=${root%/*}
cd "$root" 

lock=/tmp/.myanimedb.update.lock
[ -f "$lock" ] && exit 1
:> "$lock"
trap 'rm "$lock"' EXIT HUP INT

echo checking...
for i in "${ANIME_DIR}"/*
do
    rlink=$(readlink -m "$i")
    [ -e "${rlink%/*}" ] || continue
    [ -e "$rlink" ] || rm -v "$i"
done

echo updating...
find -L /mnt/*/Anime -mindepth 1 -maxdepth 1 | while read -r i
do
    [ -h "${ANIME_DIR}/${i##*/}" ] ||
        ln -fvrs "$i" "${ANIME_DIR}"
done

set -x

../update_maldb.py
../update_anilist.py
./clean_db.py

exit 0
