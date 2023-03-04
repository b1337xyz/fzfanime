#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import os
import json

ROOT = os.path.dirname(os.path.realpath(__file__))
MALDB = os.path.join(ROOT, '../data/maldb.json')
ANIDB = os.path.join(ROOT, '../data/anilist.json')

def load_json(fpath):
    with open(fpath, 'r') as f:
        return json.load(f)

def save_json(obj, fpath):
    with open(fpath, 'w') as f:
        json.dump(obj, f)

maldb = load_json(MALDB)
anidb = load_json(ANIDB)
keys = list(anidb)
before = len(keys)
skip = []
for k in keys:
    fullpath = Path(anidb[k]['fullpath'])
    parent = fullpath.parent
    if parent in skip:
        continue
    if not parent.exists():
        skip.append(parent)
        continue
    if not fullpath.exists():
        del anidb[k]
        del maldb[k]
        print('{} removed'.format(k))

after = len(anidb)
if before != after:
    print('{} entries removed'.format(before - after))
    save_json(anidb, ANIDB)
    save_json(maldb, MALDB)
