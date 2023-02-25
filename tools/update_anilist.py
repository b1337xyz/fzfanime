#!/usr/bin/env python3
from utils import *
from time import sleep

IMG_DIR = os.path.join(HOME, '.cache/anilist_covers')
if not os.path.exists(IMG_DIR):
    os.mkdir(IMG_DIR)


def search_by_id(mal_id: int) -> dict:
    print(f'Searching by mal id "{mal_id}" ...')
    sleep(0.5)
    variables = {'idMal': mal_id, 'page': 1, 'perPage': 10}
    data = session.post(ANILIST_API, json={
        'query': api_query_by_malid, 'variables': variables
    }).json()
    return data['data']['Page']['media'][0]


def search(query: str) -> dict:
    print(f'Searching by query "{query}" ...')
    sleep(0.5)
    variables = {'search': query, 'page': 1, 'perPage': 20}
    data = session.post(ANILIST_API, json={
        'query': api_query, 'variables': variables
    }).json()
    return data['data']['Page']['media']


def filter_by_year(year: int, data: list) -> list:
    by_year = [i for i in data if i['startDate']['year'] == year]
    return by_year if by_year else data


def get_info(title: str) -> dict:
    if title in maldb:
        malid = int(maldb[title]['mal_id'])
        try:
            return search_by_id(malid)
        except Exception:
            print(f'Failed to find by mal id: {malid}')

    year = get_year(title)
    query = clean_str(title)
    print(f'{GRN}{title = }\n{query = }{END}')
    results = search(query.lower())
    if not results:
        return
    results = filter_by_year(year, results) if year else results
    return fuzzy_sort(query, {
        i: d['title']['romaji'] for i, d in enumerate(results)
    }, results)


def update_anilist(title: str, info: dict):
    anilist[title] = {
        'anilist_id': info['id'],
        'duration': info['duration'],
        'episodes': info['episodes'],
        'genres': info['genres'],
        'image': save_image(info['coverImage']['large'], IMG_DIR),
        'is_adult': info['isAdult'],
        'mal_id': info['idMal'],
        'rating': None,
        'score': info['averageScore'],
        'studios': [i['name'] for i in info['studios']['nodes']],
        'title': clean_str(info['title']['romaji']),
        'type': None,
        'year': info['startDate']['year'],
    }


def main():
    global anilist, maldb, session
    session = requests.Session()
    anilist = load_json(ANIDB)
    maldb = load_json(MALDB)
    titles = [i for i in get_titles() if i[1] not in anilist]
    if not titles:
        print('Nothing to do')
        return

    total = len(titles)
    for idx, tmp in enumerate(titles, start=1):
        fullpath, title = tmp
        print('ANILIST {} of {}: {}'.format(idx, total, title))

        info = get_info(title)
        if info:
            update_anilist(title, info)
        elif title in maldb:
            print('Falling back to maldb...')
            anilist[title] = maldb[title].copy()
            anilist[title]['score'] = int(maldb[title]['score'] * 10)

        if not anilist[title]['score'] and title in maldb:
            anilist[title]['score'] = int(maldb[title]['score'] * 10)

        if not info:
            print('Nothing found')
            continue

        anilist[title]['fullpath'] = fullpath
        print(json.dumps(anilist[title], indent=2))

    fill_the_gaps(anilist, maldb)
    save_json(anilist, ANIDB)
    fill_the_gaps(maldb, anilist)
    save_json(maldb, MALDB)


if __name__ == '__main__':
    main()
