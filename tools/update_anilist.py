#!/usr/bin/env python3
from thefuzz import process
from time import sleep
from shutil import copy
import requests
import re
import os
import json

HOME = os.getenv('HOME')
ROOT = os.path.dirname(os.path.realpath(__file__))
MALDB = os.path.join(ROOT, 'maldb.json')
DB = os.path.join(ROOT, 'anilist.json')
ANIME_DIR = '{}/Videos/Anime'.format(HOME)
IMG_DIR = '{}/.cache/anilist_covers'.format(HOME)
CACHE = '{}/.cache/anilist.json'.format(HOME)
API_URL = 'https://graphql.anilist.co'

if not os.path.exists(IMG_DIR):
    os.mkdir(IMG_DIR)

api_query = '''
query ($id: Int, $page: Int, $perPage: Int, $search: String) {
    Page (page: $page, perPage: $perPage) {
        media (id: $id, search: $search, sort: SEARCH_MATCH, type: ANIME) {
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


def search_by_id(mal_id):
    try:
        with open(CACHE, 'r') as fp:
            cache = json.load(fp)
    except FileNotFoundError:
        cache = dict()

    if mal_id in cache:
        return cache[mal_id]

    print(f'Searching by MAL ID: {mal_id}')
    variables = {
        'idMal': int(mal_id),
        'page': 1,
        'perPage': 10,
    }
    r = requests.post(API_URL, json={
        'query': api_query_by_malid, 'variables': variables
    })
    data = r.json()
    cache[mal_id] = data
    with open(CACHE, 'w') as fp:
        json.dump(cache, fp)
    copy(CACHE, f'{CACHE}.bak')

    sleep(0.5)
    return data


def search(query):
    try:
        with open(CACHE, 'r') as fp:
            cache = json.load(fp)
    except FileNotFoundError:
        cache = dict()

    if query in cache:
        return cache[query]

    print(f'Searching by query: {query}')
    variables = {
        'search': query,
        'page': 1,
        'perPage': 20,
    }
    r = requests.post(API_URL, json={
        'query': api_query, 'variables': variables
    })
    data = r.json()
    cache[query] = data
    with open(CACHE, 'w') as fp:
        json.dump(cache, fp)
    sleep(0.7)
    return data


def clean_str(s):
    s = re.sub(r'\[[^][]*\]', '', s)
    s = re.sub(r'\([^()]*\)', '', s)
    keep = [' ', '.', '!']
    s = ''.join(c for c in s if c.isalnum() or c in keep)
    return re.sub(r'\s{2,}', ' ', s).strip()


try:
    with open(DB, 'r') as fp:
        anilist = json.load(fp)
except FileNotFoundError:
    anilist = dict()
copy(DB, f'{DB}.bak')

try:
    with open(MALDB, 'r') as fp:
        maldb = json.load(fp)
except FileNotFoundError:
    maldb = dict()

blacklist = [
    'Yinhun x He Wei Dao (2017)',  # Ad
    'Fate Extra Last Encore Illustrias Tendousetsu (2018)',
    'Drifters The Outlandish Knight (2018)',
]
blacklist = list()
lst = [
    i for i in os.listdir(ANIME_DIR)
    if i not in anilist and i not in blacklist
]

for idx, inp in enumerate(lst):
    print('ANILIST {} of {}: {}'.format(idx + 1, len(lst), inp))

    results = list()
    if inp in maldb:
        malid = maldb[inp]['mal_id']
        j = search_by_id(malid)
        if 'data' in j:
            results = j['data']['Page']['media']
        if not results:
            print('\033[1;31mFailed to find by MALID: {}\033[m'.format(malid))
        else:
            media = results[0]

    if not results:
        inp_year = re.findall(r'\(\d{4}\)', inp)
        if inp_year:
            inp_year = re.sub(r'[^\d]', '', inp_year[-1])

        # if inp = [anime] >> anime
        if len(re.sub(r'\[[^][]*\]', '', inp)) == 0:
            query = clean_str(inp[1:][:-1])
        else:
            query = clean_str(inp)

        j = search(query.lower())
        if 'data' in j:
            results = j['data']['Page']['media']
            if inp_year:
                by_year = list()
                for media in results:
                    year = media['startDate']['year']
                    if str(year) == inp_year:
                        by_year.append(media)
                if by_year:
                    results = by_year

            i = [
                i[-1] for i in process.extract(
                    query,
                    {i: d['title']['romaji'] for i,d in enumerate(results)},
                    limit=len(results)
                ) if i
            ]
            try:
                media = results[i[0]]
            except IndexError:
                results = None

    if results:
        url = media['coverImage']['large']
        image = os.path.join(IMG_DIR, url.split('/')[-1])
        if not os.path.exists(image):
            r = requests.get(url)
            with open(image, 'wb') as fp:
                fp.write(r.content)


        year = media['startDate']['year']
        episodes = media['episodes']
        if not year and inp in maldb:
            year = maldb[inp]['year']
        if not episodes and inp in maldb:
            episodes = maldb[inp]['episodes']

        studios = []
        for i in media['studios']['nodes']:
            studios.append(i['name'])
        if not studios:
            studios = maldb[inp]['studios']

        anilist[inp] = {
            'idMal': media['idMal'],
            'isAdult': media['isAdult'],
            'title': clean_str(media['title']['romaji']),
            'year': year,
            'genres': media['genres'],
            'episodes': episodes,
            'duration': media['duration'],
            'score': media['averageScore'],
            'image': image,
            'type': None,
            'rated': None,
            'studios': studios
        }
        if inp in maldb:
            anilist[inp]['type'] = maldb[inp]['type']
            anilist[inp]['rated'] = maldb[inp]['rated']

        with open(DB, 'w') as fp:
            json.dump(anilist, fp)

    elif inp in maldb:
        data = maldb[inp]
        print('\033[1;33mNothing found, using maldb\033[m')
        isAdult = data["rated"] == "Rx"
        anilist[inp] = {
            'idMal': data['mal_id'],
            'isAdult': isAdult,
            'title': data['title'],
            'year': data['year'],
            'episodes': data['episodes'],
            'image': data['image'],
            'type': data['type'],
            'rated': data['rated'],
            'genres': [],
            'duration': None,
            'score': None,
            'maldb': True,
            'studios': data['studios']
        }
        with open(DB, 'w') as fp:
            json.dump(anilist, fp)
    else:
        print('\033[1;31mNothing found :(\033[m')
        continue

    print(json.dumps(anilist[inp], indent=2))
