#!/usr/bin/env python3
#
# Remove entries wich the symlink in <ANIME_DIR> does not exist anymore
#
from datetime import datetime
from pathlib import Path
import os
import json

ROOT = os.path.dirname(os.path.realpath(__file__))
MALDB = os.path.join(ROOT, '../data/maldb.json')
ANIDB = os.path.join(ROOT, '../data/anilist.json')

class DB:
    def __init__(self, fpath):
        self.fpath = fpath
        self.fname = fpath.split('/')[-1]
        print('>>>', self.fname)
        self.read()

    def backup(self):
        if not self.db:
            return

        curr_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = '{}_{}'.format(curr_time, self.fname)
        fpath = os.path.join(HOME, fname)
        with open(fpath, 'w') as fp:
            json.dump(self.db, fp)

    def read(self):
        try:
            with open(self.fpath, 'r') as fp:
                self.db = json.load(fp)
        except FileNotFoundError:
            exit(1)

    def write(self):
        # self.backup()
        with open(self.fpath, 'w') as fp:
            json.dump(self.db, fp)

    def clean(self):
        db = self.db.copy()
        before = len(db)
        for k in db:
            fullpath = Path(self.db[k]['fullpath'])
            parent = fullpath.parent
            if parent.exists() and not fullpath.exists():
                del self.db[k]
                print('{} removed'.format(k))

        after = len(self.db)
        print('{} entries removed'.format(before - after))
        if before - after > 0:
            self.write()


DB(MALDB).clean()
DB(ANIDB).clean()
