#!/usr/bin/env python3
from thefuzz import process
from threading import Thread
from glob import glob
from shutil import copy
import requests
import os
import re
import json

HOME = os.getenv('HOME')
ROOT = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
MALDB = os.path.join(DATA_DIR, 'maldb.json')
ANIDB = os.path.join(DATA_DIR, 'anilist.json')
CONFIG = os.path.join(ROOT, 'config')
ANILIST_API = 'https://graphql.anilist.co'
JIKAN_API = 'https://api.jikan.moe/v4/anime'

RED = '\033[1;31m'
GRN = '\033[1;32m'
END = '\033[m'

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

api_query = '''
query ($id: Int, $page: Int, $perPage: Int, $search: String) {
    Page (page: $page, perPage: $perPage) {
        media (id: $id, search: $search, sort: SEARCH_MATCH, type: ANIME) {
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
'''
api_query_by_malid = '''
query ($id: Int, $idMal: Int, $page: Int, $perPage: Int) {
    Page (page: $page, perPage: $perPage) {
        media (id: $id, idMal: $idMal, sort: SEARCH_MATCH, type: ANIME) {
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
'''


def load_json(file: str) -> dict:
    try:
        with open(file, 'r') as fp:
            return json.load(fp)
    except json.decoder.JSONDecodeError:
        bak = f'{file}.bak'
        if os.path.exists(bak):
            return load_json(bak)
        else:
            return dict()
    except FileNotFoundError:
        return dict()


def save_json(obj: dict, file: str):
    copy(file, f'{file}.bak')
    with open(file, 'w') as fp:
        json.dump(obj, fp)


def download(url: str, image: str):
    r = requests.get(url)
    with open(image, 'wb') as fp:
        fp.write(r.content)


def save_image(url: str, path: str) -> str:
    image = os.path.join(path, url.split('/')[-1])
    if os.path.exists(image):
        return image

    t = Thread(target=download, args=(url, image))
    t.start()
    return image


def get_titles() -> list:
    with open(CONFIG, 'r') as fp:
        config = [os.path.expanduser(i.strip())
                  for i in fp if i and not i.startswith('#')]

    files = []
    for path in config:
        if os.path.exists(path):
            files += [(os.path.join(path, i), i) for i in os.listdir(path)]
        else:
            for i in [i for i in glob(path) if os.path.exists(i)]:
                files += [(os.path.join(i, j), j) for j in os.listdir(i)]
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
    i = [
        i[-1] for i in process.extract(query, options, limit=len(data))
    ][0]
    return data[i]


def get_year(title: str) -> int:
    try:
        return int(re.findall(r'\((\d{4})\)', title)[-1])
    except IndexError:
        return


def fill_the_gaps(a: dict, b: dict):
    for k in a:
        for v in a[k]:
            if not a[k][v] and k in b and b[k][v]:
                a[k][v] = b[k][v]
