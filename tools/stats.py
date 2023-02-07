#!/usr/bin/env python3
import os
import json

ROOT = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(ROOT, '../anilist.json')
HOME = os.getenv('HOME')
WATCHED = os.path.join(HOME, '.scripts/shell/fzfanime/watched_anime.txt')

with open(DB_PATH, 'r') as fp:
    db = json.load(fp)

with open(WATCHED, 'r') as fp:
    wl = len([k for k in fp.readlines() if k.strip() in db])

minutes = sum(
    db[k]["duration"] * db[k]["episodes"] for k in db
    if "duration" in db[k] and db[k]["episodes"] and db[k]["duration"]
)
hours = minutes // 60
days = hours // 24
line = '<' + '=' * 30 + '>'
p = wl * 100 // len(db)
print('''{}
titles  : {:>10}
watched : {:>10} ({}%)
minutes : {:>10}
hours   : {:>10}
days    : {:>10}
{}'''.format(
    line, len(db), wl, p, minutes, hours, days, line
))
