#!/usr/bin/env python3
#
# Remove entries with empty items
#

import os
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.realpath(__file__))
ANIDB = os.path.join(ROOT, '../anilist.json')
MALDB = os.path.join(ROOT, '../maldb.json')

with open(ANIDB, 'r') as fp:
    anidb = json.load(fp)
with open(MALDB, 'r') as fp:
    maldb = json.load(fp)

year = datetime.now().year
bad = list()
for k in anidb:
    for sub_k in anidb[k]:
        if anidb[k][sub_k] == None and anidb[k]['year'] != year:
            print(f'{k} - \033[1;32m{sub_k}\033[m is empty')
            bad.append(k)
            break

for k in bad:
    if k in maldb:
        del maldb[k]
    del anidb[k]
    # print(k, 'removed')

print(f'{len(bad)} keys deleted')
if input('write changes? (y/N) ').lower() == 'y':
    with open(ANIDB, 'w') as fp:
        json.dump(anidb, fp)
    with open(MALDB, 'w') as fp:
        json.dump(maldb, fp)
