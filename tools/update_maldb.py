#!/usr/bin/env python3
from urllib.request import urlopen, urlretrieve
from thefuzz import process
from urllib.parse import quote
from time import sleep
from shutil import copy
import json
import os
import re

HOME = os.getenv('HOME')
ROOT = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(ROOT, 'maldb.json')
ANIME_DIR = '{}/Videos/Anime'.format(HOME)
IMG_DIR = '{}/.cache/mal_covers'.format(HOME)
CACHE = '{}/.cache/jikan.json'.format(HOME)
API_URL = 'https://api.jikan.moe/v4/anime'


def clean_str(s):
    s = re.sub(r'\[[^][]*\]', '', s)
    s = re.sub(r'\([^()]*\)', '', s)
    keep = [' ', '.', '!']
    s = ''.join(c for c in s if c.isalnum() or c in keep)
    return re.sub(r'\s{2,}', ' ', s).strip()


def request(url):
    try:
        with open(CACHE, 'r') as fp:
            cache = json.load(fp)
    except FileNotFoundError:
        cache = dict()

    if url in cache:
        return cache[url]

    print(url)
    with urlopen(url, timeout=15) as data:
        data = json.load(data)['data']

    cache[url] = data
    with open(CACHE, 'w') as fp:
        json.dump(cache, fp)
    sleep(0.5)
    return data


def filter_by_year(target, data):
    by_year = list()
    for i in data:
        year = i['year']
        if not year:
            year = i["aired"]["prop"]["from"]["year"]
        if str(target) == year:
            by_year.append(i)
    return by_year if by_year else data


def fuzzy_sort(target, data):
    i = [
        i[-1] for i in process.extract(
            target,
            {i: d['title'] for i,d in enumerate(data)},
            limit=len(data)
        )
    ][0]
    return data[i]


def save_image(url):
    image = os.path.join(IMG_DIR, url.split('/')[-1])
    if not os.path.exists(image):
        urlretrieve(url, image)
    return image


def main():
    if not os.path.exists(IMG_DIR):
        os.mkdir(IMG_DIR)

    try:
        with open(DB_PATH, 'r') as fp:
            maldb = json.load(fp)
    except FileNotFoundError:
        maldb = dict()

    animes = [i for i in os.listdir(ANIME_DIR) if i not in maldb]
    length = len(animes)
    for i, v in enumerate(animes):
        print('MALDB {} of {}: {}'.format(i + 1, length, v))

        if '[malid-' in v:
            malid = re.search(r'\[malid-(\d+)\]', v).group(1)
            url = f'https://api.jikan.moe/v4/anime/{malid}'
            data = request(url)
            if not data:
                continue

            data['title'] = clean_str(data['title'])
        else:
            try:
                year = re.findall(r'\((\d{4})\)', v)[-1]
            except IndexError:
                year = None

            query = clean_str(v).lower()
            if len(query) < 3:
                continue

            url = '{}?q={}'.format(API_URL, quote(query))
            data = request(url)
            if not data:
                continue

            for i, d in enumerate(data):
                title = clean_str(d['title'])
                data[i]['title'] = title

            data = filter_by_year(year, data) if year else data
            data = fuzzy_sort(query, data)

        image_url = data['images']['jpg']['large_image_url']
        image_path = save_image(image_url)

        year = data['year']
        if not year:
            year = data["aired"]["prop"]["from"]["year"]

        try:
            rated = data['rating'].split()[0]
        except AttributeError:
            rated = None

        studios = []
        for i in data['studios']:
            studios.append(i['name'])

        maldb[v] = {
            'mal_id':   data['mal_id'],
            'title':    data['title'],
            'type':     data['type'],
            'url':      data['url'],
            'year':     year,
            'episodes': data['episodes'],
            'image':    image_path,
            'rated':    rated,
            'score':    data['score'],
            'studios':  studios
        }

        print(json.dumps(maldb[v], indent=2))
        with open(DB_PATH, 'w') as fp:
            json.dump(maldb, fp)


if __name__  == '__main__':
    main()
    copy(CACHE, f'{CACHE}.bak')
    copy(DB_PATH, f'{DB_PATH}.bak')
