#!/usr/bin/env python3
#
# Try to update entries with empty items
#

import os
import json
from update import *

ROOT = os.path.dirname(os.path.realpath(__file__))
ANIDB = os.path.join(ROOT, '../data/anilist.json')
MALDB = os.path.join(ROOT, '../data/maldb.json')

with open(ANIDB, 'r') as fp:
    anidb = json.load(fp)
with open(MALDB, 'r') as fp:
    maldb = json.load(fp)

bad = list()
for k in anidb:
    for sub_k in anidb[k]:
        if anidb[k][sub_k] is None:
            print(f'{k} - \033[1;32m{sub_k}\033[m is empty')
            bad.append(k)
            break

session = requests.Session()
mal = MAL(session)
anilist = Anilist(session)
total = len(bad)
for idx, k in enumerate(bad, start=1):
    fullpath = anidb[k]['fullpath']
    print(f'[{idx}/{total}] {k}')
    mal.update(k, fullpath)
    anilist.update(k, fullpath, mal.db.get(k, {}).copy())

fill_the_gaps(anilist.db, mal.db)
save_json(anilist.db, ANIDB)
fill_the_gaps(mal.db, anilist.db)
save_json(mal.db, MALDB)
