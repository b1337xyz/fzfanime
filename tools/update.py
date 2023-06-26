#!/usr/bin/env python3
from urllib.parse import quote
from time import sleep
from thefuzz import process
from threading import Thread
from glob import glob
from shutil import copy
import requests
import os
import re
import json

ROOT = os.path.dirname(os.path.realpath(__file__))
CONFIG = os.path.join(ROOT, '../config')
DATA_DIR = os.path.join(ROOT, '../data')
IMG_DIR = os.path.realpath(os.path.join(ROOT, '../images'))
MALDB = os.path.join(DATA_DIR, 'maldb.json')
ANIDB = os.path.join(DATA_DIR, 'anilist.json')
API_QUERY = '''
query ($idMal: Int, $search: String, $page: Int, $perPage: Int) {
    Page (page: $page, perPage: $perPage) {
        media (idMal: $idMal, search: $search, sort: SEARCH_MATCH, type: ANIME) {
            id
            idMal
            isAdult
            title {
                romaji
            }
            startDate {
                year
            }
            genres
            episodes
            duration
            averageScore
            description(asHtml: false)
            coverImage {
                large
            }
            studios (sort: NAME, isMain: true) {
                nodes {
                    name
                }
            }
        }
    }
}
'''.strip()  # noqa: E501


def load_json(file: str) -> dict:
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except json.decoder.JSONDecodeError:
        bak = f'{file}.bak'
        return load_json(bak)
    except FileNotFoundError:
        return dict()


def save_json(obj: dict, file: str):
    if os.path.exists(file):
        copy(file, f'{file}.bak')
    with open(file, 'w') as f:
        json.dump(obj, f)


def download(url: str, image: str):
    r = requests.get(url, stream=True)
    with open(image, 'wb') as f:
        f.write(r.content)


def save_image(url: str, filename: str) -> str:
    image = os.path.join(IMG_DIR, filename)
    if not os.path.exists(image):
        Thread(target=download, args=(url, image)).start()
    return image


def get_titles() -> list:
    print('Searching... ', flush=True, end='')
    with open(CONFIG, 'r') as f:
        config = [os.path.expanduser(i) for i in map(str.strip, f)
                  if i and not i.startswith('#')]

    files = []
    for path in config:
        if os.path.exists(path):
            files.extend((os.path.join(path, i), i) for i in os.listdir(path))
        else:
            for i in filter(os.path.exists, glob(path)):
                files.extend((os.path.join(i, j), j) for j in os.listdir(i))
    print(f'{len(files)} titles found')
    return files


def clean_str(s: str) -> str:
    s = re.sub(r'\[[^][]*\]', '', s)
    s = re.sub(r'\([^()]*\)', '', s)
    # s = re.sub(r"(?ui)\W", ' ', s)
    s = s.replace('-', ' ')
    keep = [' ', '.', '!']
    s = ''.join(c for c in s if c.isalnum() or c in keep)
    return re.sub(r'\s{2,}', ' ', s).strip()


def fuzzy_sort(query: str, options: dict, data: list) -> dict:
    try:
        k = [
            i[-1] for i in process.extract(query, options, limit=len(data))
            if i[1] > 50
        ][0]
        return data[k]
    except IndexError:
        return


def get_year(title: str) -> int:
    try:
        return int(re.findall(r'\((\d{4})\)', title)[-1])
    except IndexError:
        return


def fill_the_gaps(a: dict, b: dict):
    """ Replace empty values from `a` with `b` and vice versa """
    for k in a:
        for v in a[k]:
            if not a[k][v] and k in b and b[k][v]:
                a[k][v] = b[k][v]

        for v in b.get(k, []):
            if not b[k][v] and a[k][v]:
                b[k][v] = a[k][v]


class MAL:
    def __init__(self, session):
        self.db = load_json(MALDB)
        self.session = session
        self.api = 'https://api.jikan.moe/v4/anime/'

    def search(self, query: str = None, mal_id: int = None) -> dict:
        print(f'\tMAL {query = } {mal_id = }')
        url = self.api + f'?q={quote(query)}' if query else mal_id
        return self.session.get(url).json().get('data')

    def filter_by_year(self, year: int, data: list) -> list:
        by_year = [
            i for i in data
            if year in [i['year'], i["aired"]["prop"]["from"]["year"]]
        ]
        return by_year if by_year else data

    def get_info(self, title: str) -> dict:
        if (idMal := re.search(r'\[malid-(\d+)\]', title)) is not None:
            return self.search(idMal=idMal.group(1))

        year = get_year(title)
        query = clean_str(title)
        if len(query) < 3:
            print(f'Query length less than 3: {query = }')
            return

        if (info := self.search(query.lower())) is None:
            return

        info = self.filter_by_year(year, info) if year else info
        return fuzzy_sort(query, {
            i: clean_str(d['title']) for i, d in enumerate(info)
        }, info)

    def update(self, title: str, fullpath: str):
        info = self.get_info(title)
        if not info:
            return

        url = info['images']['jpg']['large_image_url']
        filename = f'mal-{info["mal_id"]}.jpg'
        image = save_image(url, filename)

        year = info.get('year', info["aired"]["prop"]["from"]["year"])
        rating = None if not info['rating'] else info['rating'].split()[0]

        self.db[title] = {
            'anilist_id': None,
            'duration': None,
            'episodes': info['episodes'],
            'genres': [i['name'] for i in info['genres']],
            'image': image,
            'is_adult': rating == "Rx",
            'mal_id': int(info['mal_id']),
            'rating': rating,
            'score': info['score'],
            'studios': [i['name'] for i in info['studios']],
            'title': clean_str(info['title']),
            'type': info['type'],
            'year': year,
            'aired': info['aired']['from'],
            'fullpath': fullpath
        }


class Anilist:
    def __init__(self, session):
        self.db = load_json(ANIDB)
        self.session = session
        self.api = 'https://graphql.anilist.co'

    def search(self, **variables) -> dict:
        print(f'\tAnilist {variables}')
        variables.update({'page': 1, 'perPage': 15})
        r = self.session.post(self.api, json={
            'query': API_QUERY, 'variables': variables
        })
        return r.json()['data']['Page']['media']

    def filter_by_year(self, year: int, data: list) -> list:
        by_year = [i for i in data if i['startDate']['year'] == year]
        return by_year if by_year else data

    def get_info(self, title: str, mal_id: int = None) -> dict:
        if mal_id:
            try:
                return self.search(idMal=mal_id)[0]
            except IndexError:
                pass

        year = get_year(title)
        query = clean_str(title)
        info = self.search(search=query.lower())
        info = self.filter_by_year(year, info) if year else info
        return fuzzy_sort(query, {
            i: d['title']['romaji'] for i, d in enumerate(info)
        }, info)

    def update(self, title: str, fullpath: str, fallback: dict) -> None:
        info = self.get_info(title, fallback.get('mal_id'))
        if not info:
            if fallback:
                fallback['score'] *= 10  # bug: score can be None?
                self.db[title] = fallback
            return

        url = info['coverImage']['large']
        filename = f'anilist-{info["id"]}.jpg'
        image = save_image(url, filename)

        if (score := info['averageScore']) is None:
            score = fallback.get('score', 0) * 10

        self.db[title] = {
            'anilist_id': info['id'],
            'duration': info['duration'],
            'episodes': info['episodes'],
            'genres': info['genres'],
            'image': image,
            'is_adult': info['isAdult'],
            'mal_id': info['idMal'],
            'rating': None,
            'score': score,
            'studios': [i['name'] for i in info['studios']['nodes']],
            'title': clean_str(info['title']['romaji']),
            'type': None,
            'year': info['startDate']['year'],
            'aired': None,
            'fullpath': fullpath
        }


def main():
    session = requests.Session()
    mal = MAL(session)
    anilist = Anilist(session)
    titles = [i for i in get_titles()
              if i[1] not in mal.db or i[1] not in anilist.db]
    if not titles:
        print('Nothing new')
        return

    total = len(titles)
    for idx, tmp in enumerate(titles, start=1):
        fullpath, title = tmp
        print(f'[{idx}/{total}] {title}')

        mal.update(title, fullpath)
        anilist.update(title, fullpath, mal.db.get(title, {}).copy())

        fill_the_gaps(anilist.db, mal.db)
        save_json(anilist.db, ANIDB)
        save_json(mal.db, MALDB)
        sleep(0.5)


if __name__ == '__main__':
    for d in [DATA_DIR, IMG_DIR]:
        if not os.path.exists(d):
            os.mkdir(d)

    main()
