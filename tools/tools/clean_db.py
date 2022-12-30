#!/usr/bin/env python3
#
# Remove entries wich the symlink in <ANIME_DIR> does not exist anymore
#

import os
import json
from datetime import datetime

HOME = os.getenv('HOME')
ROOT = os.path.dirname(os.path.realpath(__file__))
ANIME_PATH = os.path.join(HOME, 'Videos/Anime')
ANIDB = os.path.join(ROOT, '../anilist.json')
MALDB = os.path.join(ROOT, '../maldb.json')


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
            self.db = dict()

    def write(self):
        #self.backup()
        with open(self.fpath, 'w') as fp:
            json.dump(self.db, fp)

    def clean(self):
        db = self.db.copy()
        before = len(db)
        for k in db:
            anime = os.path.join(ANIME_PATH, k)
            if not os.path.islink(anime):
                del self.db[k]
                print('{} removed'.format(k))
        after = len(self.db)
        print('{} entries removed'.format(before - after))
        if before - after > 0:
            self.write()


DB(MALDB).clean()
DB(ANIDB).clean()
