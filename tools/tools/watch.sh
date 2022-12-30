#!/bin/sh
#
# Watch if a directory is created and update the database
#

set -e

search()
{
    # change </mnt/*/Anime> to the path you want to watch
    find /mnt/*/Anime -mindepth 1 -maxdepth 1 -type d > "$b"
}

root=$(realpath "$0") root=${root%/*}
cd "$root" 

lock=/tmp/.myanimedb.watch.lock
[ -f "$lock" ] && exit 1
:>"$lock"
a=$(mktemp)
b=$(mktemp)
trap 'rm "$a" "$b" "$lock" 2>/dev/null' EXIT HUP INT

while sleep 15;do
    if ! diff -q "$a" "$b" >/dev/null 2>&1
    then
        cp "$b" "$a"
        ./tools/update.sh
    fi
    search
done
