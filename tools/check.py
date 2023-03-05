#!/usr/bin/env python3
#
# Remove entries with empty items
#

import os
import json
from datetime import datetime
from update import *

ROOT = os.path.dirname(os.path.realpath(__file__))
ANIDB = os.path.join(ROOT, '../data/anilist.json')
MALDB = os.path.join(ROOT, '../data/maldb.json')

with open(ANIDB, 'r') as fp:
    anidb = json.load(fp)
with open(MALDB, 'r') as fp:
    maldb = json.load(fp)

year = datetime.now().year
bad = list()
for k in anidb:
    for sub_k in anidb[k]:
        if anidb[k][sub_k] is None and anidb[k]['year'] != year:
            print(f'{k} - \033[1;32m{sub_k}\033[m is empty')
            bad.append(k)
            break

session = requests.Session()
mal = MAL(session)
anilist = Anilist(session)
total = len(bad)
for idx, k in enumerate(bad, start=1):
    title = k
    fullpath = anidb[k]['fullpath']
    print(f'[{idx}/{total}] {title}')
    mal.update(title, fullpath)
    anilist.update(title, fullpath, mal.db)

fill_the_gaps(anilist.db, mal.db)
save_json(anilist.db, ANIDB)
fill_the_gaps(mal.db, anilist.db)
save_json(mal.db, MALDB)

# for k in bad:
#     if k in maldb:
#         del maldb[k]
#     del anidb[k]
# print(f'{len(bad)} keys deleted')
# if input('write changes? (y/N) ').strip().lower() == 'y':
#     with open(ANIDB, 'w') as fp:
#         json.dump(anidb, fp)
#     with open(MALDB, 'w') as fp:
#         json.dump(maldb, fp)
